from __future__ import annotations

import re
from pathlib import Path

import fitz


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "paper" / "ijgis_submission_20260605"
MANUSCRIPT = PACKAGE / "01_manuscript" / "01_manuscript_ijgis.tex"


def _referenced_pdf_figures() -> set[str]:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    return {
        Path(match).name
        for match in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+\.pdf)\}", text)
    }


def test_submission_package_has_standalone_figures_folder_for_referenced_pdfs():
    referenced = _referenced_pdf_figures()
    assert referenced

    standalone = PACKAGE / "figures"
    assert standalone.is_dir()
    for figure_name in referenced:
        assert (standalone / figure_name).is_file()

def _figure_text_blocks(pdf_path: Path) -> list[str]:
    page = fitz.open(pdf_path)[0]
    blocks = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        text = " ".join(
            span["text"]
            for line in block["lines"]
            for span in line["spans"]
        ).strip()
        if text:
            blocks.append(text)
    return blocks


def test_loveplot_rule_label_is_separate_from_title():
    blocks = _figure_text_blocks(PACKAGE / "figures" / "fig_chongqing_loveplot.pdf")

    assert not any(
        ("0.10" in block or "threshold" in block) and "covariate balance" in block
        for block in blocks
    )

def _figure_text_block_rects(pdf_path: Path):
    page = fitz.open(pdf_path)[0]
    blocks = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        text = " ".join(
            span["text"]
            for line in block["lines"]
            for span in line["spans"]
        ).strip()
        if text:
            blocks.append((text, fitz.Rect(block["bbox"])))
    return blocks


def test_standalone_figure_text_blocks_do_not_overlap():
    figure_dir = PACKAGE / "figures"
    for figure_pdf in sorted(figure_dir.glob("*.pdf")):
        blocks = _figure_text_block_rects(figure_pdf)
        overlaps = []
        for i, (left_text, left_rect) in enumerate(blocks):
            for right_text, right_rect in blocks[i + 1:]:
                intersection = left_rect & right_rect
                if not intersection.is_empty and intersection.get_area() > 1.0:
                    overlaps.append((left_text, right_text))

        assert not overlaps, f"{figure_pdf.name} has overlapping text blocks: {overlaps}"
