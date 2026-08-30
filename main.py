import os
import sys
import argparse
import multiprocessing

import datetime
from tqdm import tqdm
from functools import wraps
from collections import Counter
import csv

from logs import with_logging, get_logger
from algorithm import process_chunk

logger = get_logger()


def with_progress(func):
    """
    Декоратор для прогресс-бара со средней скоростью выполнения процесса
    и оставшимся временем.

    Args:
        func (_type_): Принимает на вход функцию, которую нужно обернуть
        в декоратор.

    Returns:
        _type_: Возвращает прогресс-бар.
    """
    @wraps(func)
    def wrapper(*args, total: int, **kwargs):
        with tqdm(
            total=total,
            desc="Обработка SNP",
            unit="SNP",
        ) as progress_bar:
            return func(
                *args,
                progress_bar=progress_bar,
                **kwargs
            )

    return wrapper


def define_number_of_processes() -> int:
    """
    Определяет количество доступных процессов.
    Args:

    Returns:
        int: Возвращает целочисленное число доступных процессов.
    """
    return multiprocessing.cpu_count()


def open_tsv_file(input_tsv_path:str) -> list[str]:
    """
    Открывает .tsv файл с SNP.
    Формат #CHROM<TAB>POS<TAB>ID<TAB>allele1<TAB>allele2

    Args:
        input_tsv_path (str): Путь к .tsv файлу.

    Returns:
        list[str]: Набор строк, где первая строка - заголовок, а остлаьные SNP
    """
    data = []
    try:
        with open(input_tsv_path, newline='', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                data.append(row)

    except FileNotFoundError:
        print("Ошибка: файл не найден.")
    except csv.Error as e:
        print(f"Ошибка парсинга TSV-файла: {e}")
    except UnicodeDecodeError:
        print("Ошибка декодирования: проверьте кодировку файла.")

    return data


def separate_chunks(lines:int) -> list[tuple[int,int]]:
    """
    Разбивает набор SNP на несколько чанков.

    Args:
        lines (int): Количество SNP в наборе.

    Returns:
        list[tuple[int,int]]: Список с множествами: начало чанка, конец чанка.
    """
    num_processes = define_number_of_processes()

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
        return [(i, i) for i in range(lines)]

    base_size = lines // num_processes
    logger.info(f"Размер чанка {base_size} строк")

    # Формирует список чанков с началом и концом, кроме последнего чанка
    chunks = [
        (i * base_size, (i + 1) * base_size - 1)
        for i in range(num_processes - 1)
    ]

    # Отдельно формирует последний чанк и добавяляет остатки
    last_start = (num_processes - 1) * base_size
    last_end = lines - 1
    chunks.append((last_start, last_end))

    return chunks


def run_process_in_chunks(
    chunk_lines:list[str],
    start_end_chunk:tuple[int, int]
    ) -> tuple[dict[int, list], dict[int, dict]]:
    """
    Запускает алгоритм в одном чанке.

    Args:
        chunk (list[str]): Список строк чанка.
        start_end_chunk (tuple[int, int]): Кортеж из номера начальной строки
        чанка и конечной строки.

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
    return process_chunk(numerated_rows_chunk)


def merge_results(
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
    for line_num, error_info in error_results_list:
        # Если для строки уже есть ошибка, сохраняем последнюю
        merged_errors[line_num] = error_info

    # Сортируем по номеру строки
    sorted_recognized = dict(sorted(merged_recognized.items()))
    sorted_errors = dict(sorted(merged_errors.items()))

    return sorted_recognized, sorted_errors


def write_results_to_file(
    output_tsv_path:str,
    recognized_results:dict[int, list],
    error_results:dict[int, dict]
    ):
    """
    Записывает результат распозннаных SNP в указанный файл,
    а нераспознанных в логи.

    Args:
        output_tsv_path (str): Путь для файла выхода.
        recognized_results (dict[int, list]): Словарь из распознанных SNP.
        error_results (dict[int, dict]): Словарь из неопределённых SNP.
    """
    pass


def calculate_statistics(
    recognized_results:dict[int, list],
    error_results:dict[int, dict]
    ):
    """
    Расчитывает статистику работы для логов и записывает их в файл report.txt

    Args:
        recognized_results (dict[int, list]): Словарь из распознанных SNP.
        error_results (dict[int, dict]): Словарь из неопределённых SNP.
    """
    pass

@with_logging
@with_progress
def main(input:str, output:str):
    """
    Принимает файл .tsv формата с вариантами SNP и возвращает определённые SNP
    в output файл .tsv формата.

    Args:
        input (str): Путь входящего .tsv файла.
        output (str): Путь для выгрузки итогового .tsv файла.
    """
    pass


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