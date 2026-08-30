import sys
import argparse
import multiprocessing

from tqdm import tqdm
import threading
from functools import wraps
from collections import Counter
import csv

from logs import with_logging, get_logger, get_current_log_dir
from algorithm import process_chunk

logger = get_logger()


def _define_number_of_processes() -> int:
    """
    Определяет количество доступных процессов.
    Args:

    Returns:
        int: Возвращает целочисленное число доступных процессов.
    """
    return multiprocessing.cpu_count()


def _open_tsv_file(input_tsv_path:str) -> list[list[str]]:
    """
    Открывает .tsv файл с SNP.
    Формат #CHROM<TAB>POS<TAB>ID<TAB>allele1<TAB>allele2

    Args:
        input_tsv_path (str): Путь к .tsv файлу.

    Returns:
        list[list[str]]: Набор строк, где первая строка - заголовок, а остлаьные SNP
    """
    data = []
    try:
        with open(input_tsv_path, newline='', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                data.append(row)

    except FileNotFoundError as e:
        logger.error(f"Ошибка: файл не найден: {input_tsv_path}. {e}")
        raise

    except csv.Error as e:
        logger.error(f"Ошибка парсинга TSV-файла: {e}")
        raise

    except UnicodeDecodeError as e:
        logger.error(f"Ошибка декодирования: {e}")
        raise

    return data


def _separate_chunks(lines:int, num_processes:int) -> list[tuple[int,int]]:
    """
    Разбивает набор SNP на несколько чанков.

    Args:
        lines (int): Количество SNP в наборе.
        num_processes (int): Количество доступных процессов.

    Returns:
        list[tuple[int,int]]: Список с множествами: начало чанка, конец чанка.
        1-based
    """
    # Если нет доступных процессов
    if num_processes <= 0:
        logger.error("Количество процессов должно быть > 0.")
        raise ValueError("Недостаточно доступных процессов.")

    # Если нет строк в файле
    if lines <= 0:
        logger.error("Файл пустой.")
        return []

    if num_processes == 1:
        logger.warning("Доступен только один процесс.")
        return [(1, lines)]

    # Если доступных процессов больше, чем строк то проходимся генератором
    if num_processes >= lines:
        logger.info(f"Доступно {num_processes} процессов.")
        return [(i+1, i+1) for i in range(lines)]

    base_size = lines // num_processes
    logger.info(f"Размер чанка {base_size} строк")

    # Формирует список чанков с началом и концом, кроме последнего чанка
    # 1-based
    chunks = [
        (i * base_size + 1, (i + 1) * base_size)
        for i in range(num_processes - 1)
    ]

    # 1-based
    last_start = (num_processes - 1) * base_size + 1
    last_end = lines
    chunks.append((last_start, last_end))

    return chunks


def _run_process_in_chunks(
    chunk_lines:list[list[str]],
    start_end_chunk:tuple[int, int],
    progress_queue=None
    ) -> tuple[dict[int, list], dict[int, dict]]:
    """
    Запускает алгоритм в одном чанке.

    Args:
        chunk (list[list[str]]): Список строк чанка.
        start_end_chunk (tuple[int, int]): Кортеж из номера начальной строки
        чанка и конечной строки. 1-based

    Returns:
        tuple[dict[int, list], dict[int, dict]]: Кортеж из
        успешно определённых SNP и нераспознанных SNP с информацией об ошибке.
    """
    # Определяет стартовую строку чанка
    start, _ = start_end_chunk

    # Формирует список: номер строки - содержание строки.
    numerated_rows_chunk = [
        (start + i, list(row))
        for i, row in enumerate(chunk_lines)
    ]

    # Получает распознанные и нераспознанные SNP.
    return process_chunk(
        numerated_rows_chunk,
        progress_queue=progress_queue
    )


def _merge_results(
    recognized_results_list:list[dict[int, list]],
    error_results_list:list[dict[int, dict]]
    ) -> tuple[dict[int, list], dict[int, dict]]:
    """
    Объединяет результаты нескольких процессов в один
    и сортирует их по номерам строк.

    Args:
        recognized_results_list (list): Список всех успешно определённых SNP
        и номеров их строк.
        error_results_list (list): Список всех нераспознанных SNP с информацией
        об ошибках и номеров их строк.

    Returns:
        tuple[dict[int, list], dict[int, dict]: Кортеж из объединённых
        результатов успешно определённых SNP и нераспознанных SNP с ошибками.
    """
    merged_recognized = {}
    merged_errors = {}

    # Объединяем успешные результаты
    for result_dict in recognized_results_list:
        for line_num, row in result_dict.items():
            if line_num in merged_recognized:
                merged_recognized[line_num].extend(row)
            else:
                merged_recognized[line_num] = list(row)

    # Объединяем ошибки
    for error_dict in error_results_list:
        for line_num, error_info in error_dict.items():
            # Если для строки уже есть ошибка, сохраняем последнюю
            merged_errors[line_num] = error_info

    # Сортируем по номеру строки
    sorted_recognized = dict(sorted(merged_recognized.items()))
    sorted_errors = dict(sorted(merged_errors.items()))

    return sorted_recognized, sorted_errors


def _write_results_to_file(
    output_tsv_path:str,
    recognized_results:dict[int, list],
    error_results:dict[int, dict]
    ):
    """
    Записывает результат распозннаных SNP в указанный файл,
    а нераспознанных в логи.

    Args:
        output_tsv_path (str): Путь для файла выхода.
        recognized_results (dict[int, list]): Словарь из сортированных
        распознанных SNP.
        error_results (dict[int, dict]): Словарь из сортированных
        неопределённых SNP.
    """
    header = ["#CHROM", "POS", "ID", "REF", "ALT"]

    try:
        logger.info(f"Начинаю запись TSV-файла: {output_tsv_path}")
        logger.debug(f"Количество строк для записи: {len(recognized_results)}")

        with open(output_tsv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")

            # Пишет заголовок
            writer.writerow(header)
            logger.debug("Заголовок записан.")

            # Пишет строки
            for line_number, row in recognized_results.items():
                # Валидация строки: ожидает список/кортеж, не пустой
                if not isinstance(row, (list, tuple)):
                    logger.error(
                        f"Строка {line_number} имеет неверный"
                        f"тип данных: {type(row)}"
                    )
                    raise ValueError(
                        "Неверный тип данных для строки"
                        f"{line_number}: ожидается list/tuple"
                    )
                writer.writerow(row)

        logger.info(
            f"Файл успешно записан: {output_tsv_path}"
            f"(строк: {len(recognized_results)})"
        )

    except FileNotFoundError:
        logger.error(
            f"Не удалось открыть файл для записи: {output_tsv_path}."
            "Путь не найден."
        )
        raise
    except PermissionError:
        logger.error(f"Нет прав на запись в файл: {output_tsv_path}")
        raise
    except ValueError as ve:
        logger.error(f"Ошибка валидации данных при записи TSV: {ve}")
        raise
    except Exception as e:
        logger.exception(
            "Неожиданная ошибка при записи TSV-файла"
            f"{output_tsv_path}: {e}"
        )
        raise

    # Запись ошибок
    error_header = [
        "#CHROM",
        "POS",
        "ID",
        "allele1",
        "allele2",
        "REASON",
    ]

    # запись нераспознанных SNP
    log_dir = get_current_log_dir()
    error_tsv_path = log_dir / "unrecognized_SNPs.tsv"

    with open(
        error_tsv_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.writer(
            f,
            delimiter="\t",
            lineterminator="\n"
        )

        # основная строка заголовка
        writer.writerow([
            "LINE_NUMBER",
            "ORIGINAL_ROW",
            "",
            "",
            "",
            "",
            "REASON",
        ])

        # подколонки исходной строки
        writer.writerow([
            "",
            "#CHROM",
            "POS",
            "ID",
            "allele1",
            "allele2",
            "",
        ])

        # запись нераспознанных SNP
        for line_number, error_info in error_results.items():
            original_row = list(error_info["row"])

            # приводит исходную строку к пяти колонкам
            original_row = original_row[:5]
            original_row += [""] * (5 - len(original_row))

            writer.writerow([
                line_number,
                *original_row,
                error_info["reason"],
            ])

def _calculate_statistics(
    recognized_results:dict[int, list],
    error_results:dict[int, dict]
    ) -> dict:
    """
    Расчитывает статистику работы для логов.

    Args:
        recognized_results (dict[int, list]): Словарь из распознанных SNP.
        error_results (dict[int, dict]): Словарь из неопределённых SNP.

    Returns:
        dict: Словарь со статистикой:
        total_snps - всего SNP
        recognized - распознано SNP
        recognized_percent - % распозннаных SNP относительно всех
        unrecognized - нераспознано SNP
        unrecognized_percent - % нераспозннаных SNP относительно всех
        error_reasons - словарь с перечнем всех ошибок и их количества
    """
    total_snps = len(recognized_results) + len(error_results)

    if total_snps <= 0:
        logger.error("SNP не было найдено")
        return {
                "total_snps": 0,
                "recognized": 0,
                "recognized_percent": 0,
                "unrecognized": 0,
                "unrecognized_percent": 0,
                "error_reasons": {"SNP не было найдено, проверьте логи.":1}
            }

    recognized_count = len(recognized_results)
    unrecognized_count = len(error_results)

    recognized_percent = recognized_count / total_snps * 100
    unrecognized_percent = unrecognized_count / total_snps * 100

    error_reasons = dict(Counter(
        error["reason"]
        for error in error_results.values()
    ))

    return {
        "total_snps": total_snps,
        "recognized": recognized_count,
        "recognized_percent": recognized_percent,
        "unrecognized": unrecognized_count,
        "unrecognized_percent": unrecognized_percent,
        "error_reasons": error_reasons
    }


def _create_chunk_rows(
    rows: list[list[str]],
    chunks_positions:tuple[int, int]
    ) -> list[list[str]]:
    """
    Формирует спислк строк чанков по заданным позициям.

    Args:
        rows (list[str]):
        chunks_positions (tuple[int, int]): Кортеж позиций начала и конца
        чанков. 1-based
    Returns:
        list[list[str]]: Формирует список строк чанков по заданным позициям.
    """
    start, end = chunks_positions
    return rows[start - 1:end]


def _consume_progress(
    progress_queue,
    progress_bar
) -> None:
    """
    Получает сообщения о прогрессе от дочерних процессов
    и обновляет общий прогресс бар.

    Args:
        progress_queue: Очередь сообщений от дочерних процессов.
        progress_bar: Общий прогресс бар tqdm.
    """
    while True:
        value = progress_queue.get()

        # Сигнал завершения работы потребителя
        if value is None:
            break

        progress_bar.update(value)


@with_logging
def main(
        input:str,
        output:str,
        progress_bar=None
    ) -> dict:
    """
    Принимает файл .tsv формата с вариантами SNP и возвращает определённые SNP
    в output файл .tsv формата.

    Args:
        input (str): Путь входящего .tsv файла.
        output (str): Путь для выгрузки итогового .tsv файла.

    Returns:
        dict: Статистика для логов.
    """
    # подготовка входных данных и разбиение на чанки
    rows = _open_tsv_file(input)
    num_processes = _define_number_of_processes()
    chunk_positions = _separate_chunks(len(rows), num_processes)

    total = len(rows) - 1 if len(rows) > 0 else 0

    with tqdm(
        total=total,
        desc="Обработка SNP",
        unit="SNP"
    ) as progress_bar:
        # подготовка очереди прогресса и аргументов для процессов
        with multiprocessing.Manager() as manager:
            progress_queue = manager.Queue()
            process_args = []

            for chunk_position in chunk_positions:
                chunk_lines = _create_chunk_rows(
                    rows,
                    chunk_position
                )

                process_args.append(
                    (
                        chunk_lines,
                        chunk_position,
                        progress_queue
                    )
                )

            # запуск отдельного потока для обновления прогресс бара
            progress_thread = threading.Thread(
                target=_consume_progress,
                args=(progress_queue, progress_bar)
            )
            progress_thread.start()

            # параллельная обработка чанков
            with multiprocessing.Pool(
                processes=num_processes
            ) as pool:
                results = pool.starmap(
                    _run_process_in_chunks,
                    process_args
                )

            # завершение потока прогресс бара
            progress_queue.put(None)
            progress_thread.join()

    # разделение результатов процессов
    recognized_results_list = []
    error_results_list = []

    for recognized_results, error_results in results:
        recognized_results_list.append(recognized_results)
        error_results_list.append(error_results)

    # объединение результатов
    recognized_results, error_results = _merge_results(
        recognized_results_list,
        error_results_list
    )

    # запись результатов в файлы
    _write_results_to_file(
        output,
        recognized_results,
        error_results
    )

    # расчёт итоговой статистики
    statistic = _calculate_statistics(
        recognized_results,
        error_results
    )

    return statistic

if __name__ == "__main__":
    # Принимает аргументы --input и --output
    parser = argparse.ArgumentParser(description="Process TSV file")
    parser.add_argument("--input", help="Input TSV file path")
    parser.add_argument("--output", help="Output TSV file path")
    args = parser.parse_args()

    if not args.input:
        print("Error: Input file path is required.")
        sys.exit(1)
    elif not args.output:
        print("Error: Output file path is required.")
        sys.exit(1)

    main(args.input, args.output)