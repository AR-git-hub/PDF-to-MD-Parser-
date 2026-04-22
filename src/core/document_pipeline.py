"""Основной пайплайн конвертации PDF в Markdown с постобработкой таблиц и изображений."""

import re
import tempfile
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    TableFormerMode,
    TableStructureOptions,
    ThreadedPdfPipelineOptions,
    EasyOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.labels import DocItemLabel

from ai.vlm import get_openai_client, call_vlm_for_image
from utils.html_parser import parse_html_table_to_md
from utils.text_helpers import (
    process_extracted_elements, 
    is_text_in_local_context_fuzzy, 
    remove_text_watermarks
)
from utils.system_helpers import doc_num_from_stem, move_or_convert_to_png

IMG_LINK_RE = re.compile(
    r"!\[.*?\]\((images/([^\)]+\.(?:png|jpe?g)))\)",
    flags=re.IGNORECASE,
)

def build_converter(no_ocr: bool, no_table_structure: bool, full_quality: bool) -> DocumentConverter:
    """Собирает и возвращает настроенный экземпляр конвертера Docling."""
    images_scale = 1.2 if full_quality else 1.0
    ocr_opts = EasyOcrOptions(force_full_page_ocr=True, lang=["ru", "en"])
    
    table_opts = TableStructureOptions(
        mode=TableFormerMode.ACCURATE,
        do_cell_matching=True 
    )
    
    pipeline_options = ThreadedPdfPipelineOptions(
        do_ocr=not no_ocr,
        ocr_options=ocr_opts,
        do_table_structure=True, 
        table_structure_options=table_opts,
        generate_picture_images=True,
        images_scale=images_scale,
        accelerator_options=AcceleratorOptions(),
    )
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)},
    )

def _filter_document_noise(doc) -> None:
    """Удаляет элементы колонтитулов из структуры документа."""
    labels_to_remove = {DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER}
    if hasattr(doc, 'body') and hasattr(doc.body, 'children'):
        doc.body.children = [
            item for item in doc.body.children 
            if getattr(item, "label", None) not in labels_to_remove
        ]

def _replace_native_tables_with_html(doc, md_text: str) -> str:
    """Заменяет таблицы Docling на Markdown, полученный из HTML-представления."""
    out_text = md_text
    for item, level in doc.iterate_items():
        if getattr(item, "label", None) == DocItemLabel.TABLE:
            try:
                native_md = item.export_to_markdown(doc).strip()
                native_html = item.export_to_html(doc)

                if not native_md or not native_html:
                    continue

                custom_md = parse_html_table_to_md(native_html).strip()
                if native_md in out_text:
                    out_text = out_text.replace(native_md, custom_md)
            except Exception:
                pass
    return out_text

def _normalize_image_names(markdown: str, work_images_dir: Path, out_images_dir: Path, doc_num: int) -> str:
    """Классифицирует изображения, переименовывает их и обновляет ссылки в Markdown."""
    out_images_dir.mkdir(parents=True, exist_ok=True)
    old_to_new: dict[str, str] = {}
    order = 1
    client = get_openai_client()
    
    matches = list(IMG_LINK_RE.finditer(markdown))
    out = markdown
    
    for m in reversed(matches):
        full_match = m.group(0)
        link_path = m.group(1)
        old_name = m.group(2)
        match_pos = m.start()
        
        src = work_images_dir / old_name
        if not src.is_file():
            continue

        img_class = "figures"
        elements = []
        if client:
            vlm_res = call_vlm_for_image(client, src)
            img_class = vlm_res.get("class", "figures")
            elements = vlm_res.get("elements", [])

        extracted_text = process_extracted_elements(elements)
        
        if img_class in ("text", "garbage", "figures_with_text", "table", "many_tables"):
            if extracted_text and is_text_in_local_context_fuzzy(extracted_text, out, match_pos):
                extracted_text = "" 

        if img_class == "watermark":
            replacement = ""
        elif img_class in ("text", "garbage", "table", "many_tables"):
            replacement = f"\n{extracted_text}\n" if extracted_text else ""
        elif img_class == "figures_with_text":
            if old_name not in old_to_new:
                new_name = f"doc_{doc_num}_image_{order}.png"
                old_to_new[old_name] = new_name
                move_or_convert_to_png(src, out_images_dir / new_name)
                order += 1
            else:
                new_name = old_to_new[old_name]
            
            new_link = f"![image](images/{new_name})"
            replacement = f"{new_link}\n\n{extracted_text}\n" if extracted_text else f"{new_link}\n"
        else:
            if old_name not in old_to_new:
                new_name = f"doc_{doc_num}_image_{order}.png"
                old_to_new[old_name] = new_name
                move_or_convert_to_png(src, out_images_dir / new_name)
                order += 1
            else:
                new_name = old_to_new[old_name]

            replacement = f"![image](images/{new_name})"

        out = out[:m.start()] + replacement + out[m.end():]

    out = re.sub(r'\n{3,}', '\n\n', out)
    return out

def convert_pdf(pdf_path: Path, output_dir: Path, converter: DocumentConverter) -> str:
    """Конвертирует один PDF в Markdown и сохраняет результат в выходную папку."""
    stem = pdf_path.stem
    doc_num = doc_num_from_stem(stem)

    result = converter.convert(str(pdf_path))
    doc = result.document

    _filter_document_noise(doc)

    with tempfile.TemporaryDirectory(prefix=f"docling_{stem}_") as tmp:
        work = Path(tmp)
        md_work = work / f"{stem}.md"
        
        doc.save_as_markdown(
            md_work,
            artifacts_dir=Path("images"),
            image_mode=ImageRefMode.REFERENCED,
        )
        text = md_work.read_text(encoding="utf-8")
        
        text = _replace_native_tables_with_html(doc, text)

        text = _normalize_image_names(
            text,
            work_images_dir=work / "images",
            out_images_dir=output_dir / "images",
            doc_num=doc_num,
        )
        
        text = remove_text_watermarks(text)
        
        out_md = output_dir / f"{stem}.md"
        out_md.write_text(text, encoding="utf-8")
    
    return pdf_path.name