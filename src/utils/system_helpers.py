"""Системные утилиты для очистки памяти, работы с файлами и архивирования результатов."""

import gc
import shutil
from pathlib import Path
from PIL import Image

def clear_cuda_cache() -> None:
    """Очищает кэш CUDA, если доступен PyTorch с поддержкой GPU."""
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        gc.collect()
        torch.cuda.empty_cache()

def doc_num_from_stem(stem: str) -> int:
    """Извлекает числовой идентификатор документа из имени файла."""
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        return 1
    try:
        return int(parts[1])
    except ValueError:
        return 1

def move_or_convert_to_png(src: Path, dst: Path) -> None:
    """Копирует изображение или конвертирует JPEG в PNG по пути назначения."""
    ext = src.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        with Image.open(src) as im:
            im.save(dst, format="PNG")
        src.unlink()
    else:
        shutil.copy(str(src), str(dst))

def create_submission_zip(output_dir: Path, zip_name: str = "submission"):
    """Создает zip-архив с итоговыми файлами из выходной директории."""
    print(f"\nСоздание архива {zip_name}.zip...")
    shutil.make_archive(zip_name, 'zip', output_dir)
    print(f"Архив {zip_name}.zip успешно создан!")  