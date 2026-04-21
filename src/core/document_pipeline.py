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



def _normalize_image_names(markdown: str, work_images_dir: Path, out_images_dir: Path, doc_num: int) -> str:
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

