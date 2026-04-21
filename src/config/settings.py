import os
import sys
import warnings
from dotenv import load_dotenv

def _apply_device_from_argv() -> None:
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
    try:
        import cv2
    except ImportError:
        return
    if not hasattr(cv2, "setNumThreads"):
        cv2.setNumThreads = lambda _nthreads: None

def setup_environment():
    """Загрузка .env и применение системных настроек."""
    load_dotenv()
    
    warnings.filterwarnings("ignore", category=UserWarning, message=".*pin_memory.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    _apply_device_from_argv()
    _patch_cv2_set_num_threads()