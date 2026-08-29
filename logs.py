"""
    Логирование для приложения.
"""
import os
import datetime
import logging
from pathlib import Path
from typing import Optional

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


def cleanup_old_folders():
    """Оставляет только последние MAX_FOLDERS папок в BASE_LOG_DIR."""
    pass


def run_with_logging(func, *args, **kwargs):
    """
    Запускает функцию func(*args, **kwargs) в контексте логирования:
      - создаёт папку запуска
      - настраивает логгер
      - после завершения пишет отчёт
      - в конце чистит старые папки
    Возвращает результат func.
    """
    pass


if __name__ == "__main__":
    # пример использования
    pass