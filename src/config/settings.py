"""Помощники для настройки окружения и стартовых патчей совместимости."""

import os
import sys
import warnings
from dotenv import load_dotenv

def _apply_device_from_argv() -> None:
    """Читает --device из аргументов CLI и сохраняет значение в переменную окружения."""
    for i, arg in enumerate(sys.argv):
        if arg == "--device" and i + 1 < len(sys.argv):
            val = sys.argv[i + 1]
            if val != "auto":
                os.environ["DOCLING_DEVICE"] = val
            return
        if arg.startswith("--device="):
            val = arg.split("=", 1)[1]
            if val != "auto":
                os.environ["DOCLING_DEVICE"] = val
            return

def _patch_cv2_set_num_threads() -> None:
    """Подставляет no-op метод, если в OpenCV отсутствует setNumThreads."""
    try:
        import cv2
    except ImportError:
        return
    if not hasattr(cv2, "setNumThreads"):
        cv2.setNumThreads = lambda _nthreads: None

def setup_environment():
    """Загружает .env и применяет стартовые настройки для пайплайна."""
    load_dotenv()
    
    warnings.filterwarnings("ignore", category=UserWarning, message=".*pin_memory.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    _apply_device_from_argv()
    _patch_cv2_set_num_threads()