"""
Алгоритмы для обработки входного TSV с SNP и определения REF и ALT.
"""
from pathlib import Path
from typing import Iterable
import pysam

from logs import get_logger

logger = get_logger()

EXPECTED_HEADER = ["#CHROM", "POS", "ID", "allele1", "allele2"]
VALID_BASES = {"A", "C", "G", "T"}
REFERENCE_DIR = Path("/ref/GRCh38.d1.vd1_mainChr/sepChrs/")


def validate_header(header: list[str]) -> None:
    """
    Проверяет заголовок входного TSV.

    Args:
        header (list[str]): Список названий колонок первой строки.

    Returns:
        None: Ничего не возвращает. При неправильном формате
        заголовка вызывает исключение.
    """
    # Проверка количества колонок
    if len(header) != len(EXPECTED_HEADER):
        logger.error(
            f"Неверный формат заголовка: ожидается {len(EXPECTED_HEADER)} колонок, "
            f"получено {len(header)}: {header}"
        )
        raise ValueError("Неверный формат заголовка входного TSV.")

    # Проверка соответствия названий колонок
    if header != EXPECTED_HEADER:
        logger.error(
            f"Неверный формат заголовка: ожидается {EXPECTED_HEADER}, "
            f"получено {header}"
        )
        raise ValueError("Неверный формат заголовка входного TSV.")


def validate_snp_row(
    row: list[str],
    line_number: int,
) -> tuple[str, int, str, str, str] | None:
    """
    Проверяет одну строку SNP и приводит значения к рабочим типам.

    Args:
        row (list[str]): Значения строки в формате
        CHROM, POS, ID, allele1, allele2.
        line_number (int): Номер строки в исходном файле.

    Returns:
        tuple[str, int, str, str, str] | None: Кортеж
        (chrom, pos, snp_id, allele1, allele2) или None
        в случае ошибки.
    """
    # Проверка количества колонок
    if len(row) != 5:
        logger.error(
            f"Строка {line_number}: Ожидается 5 колонок, "
            f"получено {len(row)}: {row}"
        )
        return None

    # Проверка на пустые значения
    for i, value in enumerate(row):
        if value == "":
            logger.error(
                f"Строка {line_number}: Пустое значение в колонке {i}: {row}"
            )
            return None

    chrom = row[0].strip()  # CHROM
    try:
        pos = int(row[1].strip())
    except ValueError:
        logger.error(
            f"Строка {line_number}: Позиция POS должна быть целым числом, "
            f"получено '{row[1]}': {row}"
        )
        return None
    snp_id = row[2].strip()  # ID
    allele1 = row[3].strip()  # allele1
    allele2 = row[4].strip()  # allele2

    # Проверка валидности аллелей
    if allele1.upper() not in VALID_BASES or allele2.upper() not in VALID_BASES:
        logger.error(
            f"Строка {line_number}: Аллели должны быть A, C, G или T, "
            f"получено '{row[3]}' и '{row[4]}': {row}"
        )
        return None

    return chrom, pos, snp_id, allele1, allele2


def get_reference_path(
    chrom: str,
) -> Path:
    """
    Формирует путь к FASTA-файлу нужной хромосомы.

    Args:
        chrom (str): Название хромосомы.

    Returns:
        Path: Путь к FASTA-файлу выбранной хромосомы.
    """
    return REFERENCE_DIR / f"{chrom}.fa"


def open_reference(
    reference_path: Path,
) -> pysam.Fastafile:
    """
    Открывает референсный FASTA-файл через pysam.Fastafile.

    Args:
        reference_path (Path): Путь к FASTA-файлу хромосомы.

    Returns:
        pysam.Fastafile: Открытый объект референсного FASTA-файла.
    """
    return pysam.FastaFile(reference_path)


def fetch_reference_base(
    fasta: pysam.Fastafile,
    pos: int,
) -> str:
    """
    Получает один нуклеотид референса для заданной позиции SNP.

    Args:
        fasta (pysam.Fastafile): Открытый референсный FASTA-файл.
        pos (int): Позиция SNP в координатах 1-based.

    Returns:
        str: Один символ референсного нуклеотида
        в верхнем регистре.
    """
    return pysam.fetch(fasta, pos-1, pos).strip()


def determine_ref_alt(
    reference_base: str,
    allele1: str,
    allele2: str,
) -> tuple[str, str] | None:
    """
    Определяет REF и ALT для SNP.

    Args:
        reference_base (str): Один символ референса в верхнем регистре.
        allele1 (str): Первый аллель из входного TSV.
        allele2 (str): Второй аллель из входного TSV.

    Returns:
        tuple[str, str] | None: Кортеж (REF, ALT) или None
        если невозможно определить SNP.
    """
    # Если референсный нуклеотид не является валидным, возвращаем None
    if reference_base.upper() not in VALID_BASES:
            return None

    # Если референс совпадает с первым аллелем, возвращаем как есть
    if reference_base.lower() == allele1.lower():
        return reference_base.upper(), allele2.upper()

    # Если референс совпадает со вторым аллелем, меняем местами
    if reference_base.lower() == allele2.lower():
        return allele2.upper(), allele1.upper()

    # Если ни один аллель не совпадает с референсом, возвращаем None
    return None


def process_snp(
    line_number: int,
    row: list[str],
    fasta_cache: dict[str, pysam.Fastafile],
) -> tuple[int, dict] | None:
    """
    Обрабатывает одну строку SNP и определяет REF и ALT.

    Args:
        line_number (int): Номер строки в исходном файле.
        row (list[str]): Значения строки входного TSV.
        fasta_cache (dict[str, pysam.Fastafile]): Словарь уже
        открытых FASTA-файлов текущего процесса.

    Returns:
        tuple[int, dict] | None: Кортеж из номера строки и словаря с информацией
        о распознанном или нераспознанном варианте,
        или None, если это заголовок.
    """
    # Если это заголовок, проверяем его и возвращаем None
    if line_number == 1:
        validate_header(row)
        return None  # Заголовок не обрабатываем дальше

    # Если это не заголовок, проверяем строку SNP
    validated_row = validate_snp_row(row, line_number)

    # Если строка не прошла валидацию, возвращаем номер строки для пропуска
    if validated_row is None:
        return line_number, {
            "status": "unrecognized",
            "row": row,
            "reference_base": None,
            "reason": "Ошибка валидации строки",
        }

    chrom = validated_row[0]

    # открывает референс хромосомы, если его ещё нет в кэше
    if chrom not in fasta_cache:
        reference_path = get_reference_path(chrom)
        fasta_cache[chrom] = open_reference(reference_path)

    # получает уже открытый референсный файл
    reference_fasta = fasta_cache[chrom]

    # Получаем референсный нуклеотид для позиции SNP
    pos = validated_row[1]
    reference_base = fetch_reference_base(
        reference_fasta,
        pos
    )

    # Определяем REF и ALT для SNP
    allele1 = validated_row[3]
    allele2 = validated_row[4]
    ref_alt = determine_ref_alt(
        reference_base,
        allele1,
        allele2
    )

    # Если невозможно определить REF и ALT,
    # логируем предупреждение и возвращаем информацию о нераспознанном варианте
    if ref_alt is None:
        logger.warning(
            f"Строка {line_number}: Невозможно определить REF и ALT для SNP, "
            f"референс: {reference_base}, аллели: {allele1}, {allele2}"
        )
        return line_number, {
            "status": "unrecognized",
            "row": row,
            "reference_base": reference_base,
            "reason": "Невозможно определить REF и ALT",
        }

    allele1 = ref_alt[0]
    allele2 = ref_alt[1]

    return line_number, {
        "status": "recognized",
        "row": [chrom, pos, validated_row[2], allele1, allele2],
        "reference_base": reference_base,
        "reason": None,
    }


def process_chunk(
    chunk: list[tuple[int, list[str]]],
    progress_queue=None,
) -> tuple[dict[int, list], dict[int, dict]]:
    """
    Обрабатывает один участок строк входного TSV.

    Args:
        chunk (list[tuple[int, list[str]]]): Список пар
        (номер строки, значения строки).
        progress_queue: Очередь для передачи прогресса
        родительскому процессу.

    Returns:
        tuple[dict[int, list[str]], dict[int, dict]]: Результаты обработки
        участка с распознанными и нераспознанными SNP.
    """
    # Создаём кэш открытых FASTA-файлов для каждой хромосомы в участке
    fasta_cache = {}
    for chrom in {row[0] for _, row in chunk if len(row) > 0}:
        reference_path = get_reference_path(chrom)
        fasta_cache[chrom] = open_reference(reference_path)

    # Обрабатываем каждую строку в участке
    recognized_results = {}
    error_results = {}
    for line_number, row in chunk:
        result = process_snp(line_number, row, fasta_cache=fasta_cache)

        # Если есть очередь прогресса,
        # отправляем сигнал о завершении одной строки
        if progress_queue is not None:
            progress_queue.put(1)

        # Если результат None, это заголовок, пропускаем его
        if result is None:
            continue

        # Если SNP распознан, добавляем его в результаты
        if result[1]["status"] == "recognized":
            recognized_results[result[0]] = result[1]["row"]

        # Возвращаем информацию о нераспознанном варианте
        else:
            error_results[result[0]] = {
                "row": result[1]["row"],
                "reference_base": result[1]["reference_base"],
                "reason": result[1]["reason"],
            }

    close_references(fasta_cache)

    return recognized_results, error_results


def close_references(
    fasta_cache: dict[str, pysam.Fastafile],
) -> None:
    """
    Закрывает все FASTA-файлы, открытые текущим процессом.

    Args:
        fasta_cache (dict[str, pysam.Fastafile]): Словарь открытых
        FASTA-файлов текущего процесса.

    Returns:
        None: Ничего не возвращает.
    """
    for fasta in fasta_cache.values():
        fasta.close()


if __name__ == "__main__":
    pass