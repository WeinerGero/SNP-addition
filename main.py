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


def open_tsv_file(input_tsv_path) -> list[str]:
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


def separate_chunks(lines:int, num_process:int) -> list[tuple[int,int]]:
    """
    Разбивает набор SNP на несколько

    Args:
        lines (int): Количество SNP в наборе.
        num_process (int): Количество доступных процессов в системе.

    Returns:
        list[tuple[int,int]]: Список с множествами: начало чанка, конец чанка.
    """
    pass


def run_process_in_chunks(
    input_tsv_path,
    output_tsv_path=None
    ) -> tuple[dict[int, list], dict[int, dict]]:
    """
    Запускает алгоритм в одном чанке.

    Args:
        input_tsv_path (_type_): _description_
        output_tsv_path (_type_, optional): _description_. Defaults to None.

    Returns:
        tuple[dict[int, list], dict[int, dict]]: Кортеж из
        успешно определённых SNP и нераспознанных SNP с информацией об ошибке.
    """
    pass


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
    pass


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