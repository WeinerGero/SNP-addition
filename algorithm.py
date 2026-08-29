"""

"""
from pathlib import Path
from typing import Iterable
import pysam

from logs import with_logging, get_logger

logger = get_logger()

EXPECTED_HEADER = ["#CHROM", "POS", "ID", "allele1", "allele2"]
VALID_BASES = {"A", "C", "G", "T"}


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

    row[0] = row[0].strip()  # CHROM
    try:
        row[1] = int(row[1].strip())  # POS
    except ValueError:
        logger.error(
            f"Строка {line_number}: Позиция POS должна быть целым числом, "
            f"получено '{row[1]}': {row}"
        )
        return None
    row[2] = row[2].strip()  # ID
    row[3] = row[3].strip()  # allele1
    row[4] = row[4].strip()  # allele2

    # Проверка валидности аллелей
    if row[3].upper() not in VALID_BASES or row[4].upper() not in VALID_BASES:
        logger.error(
            f"Строка {line_number}: Аллели должны быть A, C, G или T, "
            f"получено '{row[3]}' и '{row[4]}': {row}"
        )
        return None

    return row[0], row[1], row[2], row[3], row[4]


def get_reference_path(
    reference_dir: Path,
    chrom: str,
) -> Path:
    """
    Формирует путь к FASTA-файлу нужной хромосомы.

    Args:
        reference_dir (Path): Каталог с референсными FASTA-файлами.
        chrom (str): Название хромосомы.

    Returns:
        Path: Путь к FASTA-файлу выбранной хромосомы.
    """
    return reference_dir / f"{chrom}.fa"


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
    reference_dir: Path,
    fasta_cache: dict[str, pysam.Fastafile],
):
    """
    Обрабатывает одну строку SNP и определяет REF и ALT.

    Args:
        line_number (int): Номер строки в исходном файле.
        row (list[str]): Значения строки входного TSV.
        reference_dir (Path): Каталог с референсными FASTA-файлами.
        fasta_cache (dict[str, pysam.Fastafile]): Словарь уже
        открытых FASTA-файлов текущего процесса.

    Returns:
        object: Результат обработки SNP с номером исходной строки
        и информацией о распознанном или нераспознанном варианте.
    """
    #
    chr = row[0].strip()
    pos = int(row[1].strip())
    allele1 = row[-2].strip()
    allele2 = row[-1].strip()



    reference_base = pysam.fetch

    pass


def process_chunk(
    chunk: list[tuple[int, list[str]]],
    reference_dir: Path,
    progress_queue=None,
):
    """
    Обрабатывает один участок строк входного TSV.

    Args:
        chunk (list[tuple[int, list[str]]]): Список пар
        (номер строки, значения строки).
        reference_dir (Path): Каталог с референсными FASTA-файлами.
        progress_queue: Очередь для передачи прогресса
        родительскому процессу.

    Returns:
        object: Результаты обработки участка с распознанными
        и нераспознанными SNP.
    """
    pass


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