from __future__ import annotations

import re
from pathlib import Path


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
