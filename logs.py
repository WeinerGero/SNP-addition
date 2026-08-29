"""
    Логирование для приложения.
"""
import os
import datetime
import logging
from pathlib import Path
from typing import Optional
from functools import wraps

BASE_LOG_DIR = "logs"
MAX_FOLDERS = 10


def setup_logging(log_dir: Path) -> logging.Logger:
    """Настраивает логгер с FileHandler в указанной папке."""
    os.makedirs(log_dir, exist_ok=True)

    log_file = log_dir / "app.log"

    logger = logging.getLogger("my_app")
    logger.setLevel(logging.DEBUG)

    # очищает существующие хендлеры, чтобы не дублировать при повторном вызове
    if logger.handlers:
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def create_run_folder() -> Path:
    """Создаёт папку для текущего запуска и возвращает её путь."""
    base_path = Path(BASE_LOG_DIR)
    os.makedirs(base_path, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base_path / timestamp
    os.makedirs(run_dir, exist_ok=True)

    return run_dir


def write_report(report_path: Path, content: str) -> None:
    """Записывает отчёт в файл с кодировкой UTF‑8."""
    with report_path.open("w", encoding="utf-8") as f:
        f.write(content)


def cleanup_old_folders() -> None:
    """Оставляет только последние MAX_FOLDERS папок в BASE_LOG_DIR."""
    base_path = Path(BASE_LOG_DIR)
    if not base_path.is_dir():
        return

    # сортирует папки по имени
    folders = sorted(
        [f for f in base_path.iterdir() if f.is_dir()],
        key=lambda x: x.name,
        reverse=True,  # самые свежие первыми
    )

    to_remove = folders[MAX_FOLDERS:]
    for folder in to_remove:
        # удаляет всё внутри и саму папку
        for item in folder.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
        folder.rmdir()


def run_with_logging(func, *args, **kwargs):
    """
    Запускает функцию func(*args, **kwargs) в контексте логирования:
      - создаёт папку запуска
      - настраивает логгер
      - после завершения пишет отчёт
      - в конце чистит старые папки
    Возвращает результат func.
    """
    run_dir = create_run_folder()
    logger = setup_logging(run_dir)

    report_content_lines = []
    report_content_lines.append("Отчёт о выполнении запуска")
    report_content_lines.append(f"Папка: {run_dir.resolve()}")
    report_content_lines.append(f"Дата/время запуска: {datetime.datetime.now().isoformat()}")
    report_content_lines.append("")

    try:
        result = func(*args, **kwargs)
        report_content_lines.append("Статус: Успешно")
        report_content_lines.append(f"Результат (repr): {repr(result)}")
    except Exception as e:
        report_content_lines.append("Статус: Ошибка")
        report_content_lines.append(f"Исключение: {type(e).__name__}: {e}")
        logger.exception("Необработанное исключение в основной функции")
        raise
    finally:
        # формирует и пишет отчёт
        report_path = run_dir / "report.txt"
        write_report(report_path, "\n".join(report_content_lines))

        # чистит старые папки
        cleanup_old_folders()

        logger.info("Логирование завершено, отчёт сохранён")

    return result


def with_logging(func):
    """
    Декоратор для функций, которые должны выполняться с логированием.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return run_with_logging(func, *args, **kwargs)
    return wrapper


def get_logger() -> logging.Logger:
    """Возвращает активный логгер 'my_app'."""
    return logging.getLogger("my_app")


if __name__ == "__main__":
    # пример использования
    from logs import with_logging, get_logger

    @with_logging
    def simple_task() -> int:
        logger = get_logger()
        logger.info("Старт задачи")
        result = 42 * 2
        logger.info(f"Промежуточный результат: {result}")
        return result

    output = simple_task()
    print(f"Готово. Результат: {output}")