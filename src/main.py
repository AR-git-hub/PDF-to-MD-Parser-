"""Точка входа CLI для пакетной конвертации PDF в Markdown."""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Инициализация переменных окружения и патчей до импорта тяжелых библиотек
from config.settings import setup_environment
setup_environment()

from docling.datamodel.base_models import InputFormat
from core.document_pipeline import build_converter, convert_pdf
from utils.system_helpers import clear_cuda_cache, create_submission_zip

def main() -> None:
    """Разбирает аргументы CLI и запускает параллельную обработку PDF."""
    parser = argparse.ArgumentParser(description="Baseline (Docling ACCURATE + HTML Tables + VLM Fallback)")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--no-table-structure", action="store_true")
    parser.add_argument("--full-quality", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(args.input_dir.glob("*.pdf"))
    if args.max_files is not None:
        pdf_files = pdf_files[: args.max_files]

    import os
    dev = os.environ.get("DOCLING_DEVICE", "auto")
    print(f"Устройство: {dev} | Потоков: {args.workers}")
    
    converter = build_converter(
        no_ocr=args.no_ocr,
        no_table_structure=args.no_table_structure,
        full_quality=args.full_quality, 
    )
    converter.initialize_pipeline(InputFormat.PDF)

    print(f"Начало обработки {len(pdf_files)} файлов...")
    
    processed_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_pdf = {executor.submit(convert_pdf, pdf_path, args.output_dir, converter): pdf_path for pdf_path in pdf_files}
        
        for future in as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            processed_count += 1
            try:
                filename = future.result()
                print(f"[{processed_count}/{len(pdf_files)}] {filename} ... УСПЕХ", flush=True)
            except Exception as exc:
                print(f"[{processed_count}/{len(pdf_files)}] {pdf_path.name} ... ОШИБКА: {exc}", flush=True)
            finally:
                clear_cuda_cache()

    create_submission_zip(args.output_dir)

if __name__ == "__main__":
    main()