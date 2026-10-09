import pytest
import sys
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.component_process import (
    component_label,
    components_for_module,
    components_for_process,
)
from backend.ai import layout_reader
from backend.ai.layout_reader import extract_pdf_layout, parse_component_process_table

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from backend.routes import EstimateInput, _run_calculation
from backend.app import app


@pytest.fixture
def components():
    return [
        {
            "component_name": "Base Material",
            "material": "Kappa",
            "processes": {"Base Material": True, "Punching": True, "Printing": True},
        },
        {
            "component_name": "Wrapper",
            "material": "Art Paper",
            "processes": {"Punching": True},
        },
        {
            "component_name": "Insert1",
            "material": "EVA",
            "processes": {"Punching": True, "Embossing": True},
        },
        {
            "component_name": "Insert2",
            "material": "EVA",
            "processes": {"Punching": False, "Printing": True},
        },
    ]


def test_process_routing_excludes_no_rows_and_keeps_distinct_components(components):
    routed = components_for_process(components, "Punching")

    assert [component_label(row) for row in routed] == [
        "Base Material_Kappa",
        "Wrapper_Art Paper",
        "Insert1_EVA",
    ]


def test_module_routing_combines_processes_without_duplicate_components(components):
    routed = components_for_module(components, "Embellishments")

    assert [component_label(row) for row in routed] == ["Insert1_EVA"]


def test_one_component_can_route_to_multiple_modules(components):
    assert components_for_module(components, "Kappa") == components[:1]
    assert components_for_module(components, "Printing") == [components[0], components[3]]


def test_unknown_process_is_rejected(components):
    with pytest.raises(ValueError, match="Unknown component process"):
        components_for_process(components, "Unconfigured Process")


def test_full_calculation_creates_only_yes_process_lines():
    estimate = EstimateInput(components=[
        {"component_name": "Base Material", "material": "Kappa", "processes": {"Base Material": True}},
        {"component_name": "Insert2", "material": "EPE", "processes": {"Punching": False}},
    ])

    result = _run_calculation(estimate)

    assert [line["module"] for line in result["lines"]] == ["Kappa"]
    assert result["lines"][0]["component_lines"][0]["component_label"] == "Base Material_Kappa"
    assert result["total_manufacturing_cost"] == result["lines"][0]["total_cost"]


def test_no_process_rows_do_not_create_zero_cost_module_lines():
    estimate = EstimateInput(components=[
        {"component_name": "Insert2", "material": "EPE", "processes": {"Punching": False}},
        {"component_name": "Unconfirmed", "material": "Kappa", "processes": {"Punching": None}},
    ])

    result = _run_calculation(estimate)

    assert result["lines"] == []
    assert result["total_manufacturing_cost"] == 0


def test_multiple_components_with_same_material_keep_separate_cost_rows():
    estimate = EstimateInput(components=[
        {"component_name": "Insert1", "material": "Kappa", "processes": {"Base Material": True}},
        {"component_name": "Insert2", "material": "Kappa", "processes": {"Base Material": True}},
    ])

    result = _run_calculation(estimate)

    assert [row["component_label"] for row in result["lines"][0]["component_lines"]] == [
        "Insert1_Kappa",
        "Insert2_Kappa",
    ]
    assert result["lines"][0]["total_cost"] == pytest.approx(
        2 * result["lines"][0]["component_lines"][0]["total_cost"]
    )


def test_wrapper_final_sheets_feed_printing_component_rows():
    estimate = EstimateInput(components=[
        {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True}},
        {"component_name": "Printed Wrapper", "material": "Art Paper", "processes": {"Printing": True}},
    ])

    result = _run_calculation(estimate)
    wrapper = next(line for line in result["lines"] if line["module"] == "Wrapper")
    printing = next(line for line in result["lines"] if line["module"] == "Printing")

    assert result["wrapper_final_sheets"] == wrapper["wrapper_final_sheets"]
    assert any("final wrapper sheets" in trace["value"] for trace in printing["component_lines"][0]["trace"])


def test_punching_and_die_cutting_aliases_create_one_foam_cost_row():
    estimate = EstimateInput(components=[
        {"component_name": "Insert1", "material": "EVA", "processes": {"Punching": True, "Die Cutting": True}},
    ])

    result = _run_calculation(estimate)
    punching = next(line for line in result["lines"] if line["module"] == "Punching")

    assert len(punching["component_lines"]) == 1
    assert punching["component_lines"][0]["process"] == "Die Cutting"


def test_foam_punching_yes_is_labeled_die_cutting():
    result = _run_calculation(EstimateInput(components=[
        {"component_name": "Insert1", "material": "EVA", "processes": {"Punching": True}},
    ]))

    punching = next(line for line in result["lines"] if line["module"] == "Punching")
    assert punching["component_lines"][0]["process"] == "Die Cutting"


def test_layout_parser_uses_only_explicit_yes_no_values_and_material_label():
    rows = parse_component_process_table(
        "Component Name | Material | Printing | Punching / Die Cutting\n"
        "Insert1 | EVA | NO | YES\n"
        "Insert2 | EPE | YES | NO\n"
        "Unconfirmed | Kappa | maybe | ?"
    )

    assert [row["component_name"] for row in rows] == ["Insert1", "Insert2"]
    assert rows[0]["processes"]["Printing"] is False
    assert rows[0]["processes"]["Die Cutting"] is True
    assert rows[0]["processes"]["Punching"] is False
    assert rows[1]["processes"]["Printing"] is True
    assert rows[1]["processes"]["Die Cutting"] is False


def test_layout_extract_api_reads_explicit_pdf_matrix_rows():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((40, 50), "Component Name | Material | Printing | Punching / Die Cutting")
    page.insert_text((40, 70), "Insert1 | EVA | NO | YES")
    pdf_content = document.tobytes()
    document.close()

    response = TestClient(app).post(
        "/api/layout/extract",
        headers={"Authorization": "Bearer testing-session"},
        files={"file": ("layout.pdf", pdf_content, "application/pdf")},
    )

    assert response.status_code == 200
    component = response.json()["components"][0]
    assert component["component_name"] == "Insert1"
    assert component["material"] == "EVA"
    assert component["processes"]["Die Cutting"] is True


def _structured_layout_pdf():
    document = fitz.open()
    component_page = document.new_page()
    component_page.insert_textbox(
        fitz.Rect(40, 40, 520, 300),
        "Component ID: Top-KAPPA-01\n"
        "Material: White Back Kappa Board\n"
        "Sheet Size: 31 x 20.5 in\n"
        "Thickness: 1.5 mm\n"
        "GSM per 1 mm: 750\n"
        "UPS: 6\n"
        "Punching: Yes\n"
        "Lamination: No\n"
        "Printing: No",
    )
    project_page = document.new_page()
    project_page.insert_textbox(
        fitz.Rect(40, 40, 520, 180),
        "Project Name: Kakada premium sweet box\n"
        "Customer / Brand: Kakada\n"
        "Finished Box Size (L x W x H): 208x148x36mm\n"
        "Quantity: 5000 qty",
    )
    content = document.tobytes()
    document.close()
    return content


def test_structured_pdf_extraction_normalizes_values_and_keeps_provenance():
    result = extract_pdf_layout(_structured_layout_pdf())

    component = result["components"][0]
    assert component["component_name"] == "Top-KAPPA-01"
    assert component["material"] == "White Back Kappa Board"
    assert component["processes"]["Punching"] is True
    assert component["processes"]["Lamination"] is False
    assert component["processes"]["Printing"] is False
    assert component["processes"]["Foiling"] is None
    assert component["process_inputs"]["Kappa"] == {
        "kappa_sheet_length_mm": 787.4,
        "kappa_sheet_width_mm": 520.7,
        "kappa_thickness_mm": 1.5,
        "kappa_gsm_at_1mm": 750.0,
        "kappa_ups": 6,
    }
    assert component["extracted_fields"]["sheet_size"]["value"] == "31 x 20.5 in"
    assert component["extracted_fields"]["sheet_size"]["source"] == "pymupdf_text"
    assert component["extracted_fields"]["sheet_size"]["page"] == 1
    assert component["extracted_fields"]["sheet_size"]["confidence"] > 0.9
    assert result["document_fields"]["quantity"]["normalized_value"] == 5000
    assert result["document_fields"]["finished_box_size"]["normalized_value"] == {
        "length": 208.0, "width": 148.0, "height": 36.0, "unit": "mm",
    }


def test_pymupdf_table_cells_are_used_when_native_page_text_is_empty(monkeypatch):
    import pymupdf

    class Table:
        def extract(self):
            return [
                ["Component Name", "Material", "Printing", "Punching"],
                ["Insert1", "EVA", "NO", "YES"],
            ]

    class Page:
        def get_text(self, mode):
            return ""

        def find_tables(self):
            return type("TableResult", (), {"tables": [Table()]})()

        def get_images(self, full=True):
            return []

    class Document:
        def __init__(self):
            self.pages = [Page()]

        def __iter__(self):
            return iter(self.pages)

        def __len__(self):
            return len(self.pages)

        def close(self):
            pass

    monkeypatch.setattr(pymupdf, "open", lambda **kwargs: Document())
    monkeypatch.setattr(layout_reader, "_ocr_page", lambda page: ("", 0.0))
    monkeypatch.setattr(layout_reader, "_page_bbox", lambda page, value: None)
    monkeypatch.setattr(layout_reader, "_page_geometry", lambda page: {})

    result = extract_pdf_layout(b"table fixture")

    assert result["pages"][0]["table_count"] == 1
    assert result["components"][0]["component_name"] == "Insert1"
    assert result["components"][0]["processes"]["Printing"] is False
    assert result["components"][0]["processes"]["Punching"] is True


def test_missing_sheet_unit_requires_confirmation_and_does_not_create_cost_override():
    text = (
        "Component ID: INS-DUPLEX-01\nMaterial: Duplex\nSheet Size: 30x20\n"
        "GSM: 230gsm\nUPS: 2 set ups\nPunching: Yes\nLamination: Yes / glass"
    )
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 520, 300), text)
    result = extract_pdf_layout(document.tobytes())
    document.close()

    component = result["components"][0]
    assert component["extracted_fields"]["sheet_size"]["review_status"] == "Confirmation Required"
    assert component["extracted_fields"]["lamination_finish"]["value"] == "glass"
    assert component["extracted_fields"]["lamination_finish"]["normalized_value"] is None
    assert component["extracted_fields"]["lamination_finish"]["review_status"] == "Confirmation Required"
    assert component["processes"]["Lamination"] is True
    assert "Insert" not in component["process_inputs"]


def test_ocr_is_used_only_when_native_page_text_is_missing(monkeypatch):
    document = fitz.open()
    document.new_page()
    content = document.tobytes()
    document.close()
    monkeypatch.setattr(layout_reader, "_ocr_page", lambda page: (
        "Component ID: OCR-01\nMaterial: Art Paper\nPrinting: Yes", 0.87,
    ))
    monkeypatch.setattr(layout_reader, "_vision_fallback", lambda page, page_number: pytest.fail("Vision must follow OCR"))

    result = extract_pdf_layout(content)

    assert result["components"][0]["source"] == "tesseract_ocr"
    assert result["components"][0]["confidence"] == 0.87
    assert result["pages"][0]["text_source"] == "tesseract_ocr"


def test_ocr_runs_for_raster_page_with_partial_native_text(monkeypatch):
    from PIL import Image
    from io import BytesIO

    image = Image.new("RGB", (80, 80), "white")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((40, 50), "Drawing and production specifications appear on this page")
    page.insert_image(fitz.Rect(100, 100, 180, 180), stream=image_bytes.getvalue())
    content = document.tobytes()
    document.close()
    calls = []
    monkeypatch.setattr(layout_reader, "_ocr_page", lambda page: (
        calls.append(page) or "Component ID: SCAN-01\nMaterial: Art Paper\nPrinting: Yes", 0.91,
    ))
    monkeypatch.setattr(layout_reader, "_vision_fallback", lambda page, page_number: pytest.fail("Vision must follow OCR"))

    result = extract_pdf_layout(content)

    assert len(calls) == 1
    assert result["components"][0]["component_name"] == "SCAN-01"
    assert result["components"][0]["processes"]["Printing"] is True


def test_vision_fallback_runs_after_native_text_and_ocr_fail(monkeypatch):
    document = fitz.open()
    document.new_page()
    content = document.tobytes()
    document.close()
    monkeypatch.setattr(layout_reader, "_ocr_page", lambda page: ("", 0.0))
    monkeypatch.setattr(layout_reader, "_vision_fallback", lambda page, page_number: (
        "Component ID: VISION-01\nMaterial: Art Paper\nPrinting: Yes", 0.65,
    ))

    result = extract_pdf_layout(content)

    assert result["vision_used"] is True
    assert result["components"][0]["source"] == "vision"
    assert result["components"][0]["extracted_fields"]["component_name"]["confidence"] == 0.65


def test_pdf_page_geometry_reports_vector_and_raster_content():
    from PIL import Image, ImageDraw
    from io import BytesIO
    from backend.ai.layout_reader import _page_geometry

    image = Image.new("RGB", (80, 80), "white")
    ImageDraw.Draw(image).rectangle((10, 10, 70, 70), outline="black", width=3)
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    document = fitz.open()
    page = document.new_page()
    page.draw_rect(fitz.Rect(20, 20, 100, 100))
    page.insert_image(fitz.Rect(120, 20, 200, 100), stream=image_bytes.getvalue())

    geometry = _page_geometry(page)
    document.close()

    assert geometry["vector_path_count"] > 0
    assert geometry["raster_image_count"] > 0
    assert geometry["opencv_edge_pixels"] > 0
    assert geometry["opencv_contour_count"] > 0


def test_structured_pdf_extract_api_returns_fields_and_process_matrix():
    response = TestClient(app).post(
        "/api/layout/extract",
        headers={"Authorization": "Bearer testing-session"},
        files={"file": ("structured.pdf", _structured_layout_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["components"]) == 1
    assert result["document_fields"]["quantity"]["normalized_value"] == 5000
    assert result["components"][0]["processes"]["Punching"] is True
    assert result["components"][0]["processes"]["Foiling"] is None


@pytest.mark.parametrize("kakada_pdf", [
    Path(__file__).resolve().parents[1] / "Kakada_Ramprasad_Premium Sweets_kappa_Ups Plan.pdf",
    Path(__file__).resolve().parents[1] / "Kakada_Ramprasad_Premium Sweets_kappa_Ups Plan2.pdf",
], ids=lambda path: path.stem)
def test_kakada_reference_pdf_extracts_and_routes_components_end_to_end(kakada_pdf):
    if not kakada_pdf.exists():
        pytest.skip("Local Kakada reference PDF is not included")
    response = TestClient(app).post(
        "/api/layout/extract",
        headers={"Authorization": "Bearer testing-session"},
        files={"file": (kakada_pdf.name, kakada_pdf.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 200
    result = response.json()

    assert [component["component_name"] for component in result["components"]] == [
        "Top-KAPPA-01", "Bottom-KAPPA-02", "WR-01", "INS-DUPLEX-01",
    ]
    assert result["document_fields"]["quantity"]["normalized_value"] == 5000
    assert result["document_fields"]["finished_box_size"]["normalized_value"] == {
        "length": 208.0, "width": 148.0, "height": 36.0, "unit": "mm",
    }
    assert result["document_fields"]["project_name"]["value"] == "Kakada premium sweet box"
    assert result["document_fields"]["customer_name"]["value"] == "Kakada"
    assert result["document_fields"]["product_name"]["value"] == "sweet box"
    assert result["document_fields"]["box_type"]["value"] == "Top and bottom"
    assert result["document_fields"]["drawing_version"]["value"] == "v1"
    assert result["document_fields"]["prepared_date"]["value"] == "06.10.2026"
    assert len(result["layout_dimensions"]) == 18
    assert result["components"][0]["processes"]["Punching"] is True
    assert result["components"][0]["processes"]["Printing"] is False
    assert result["components"][2]["processes"]["Lamination"] is True
    assert result["components"][0]["process_inputs"]["Kappa"] == {
        "kappa_sheet_length_mm": 787.4,
        "kappa_sheet_width_mm": 520.7,
        "kappa_thickness_mm": 1.5,
        "kappa_gsm_at_1mm": 750.0,
        "kappa_ups": 6,
    }
    assert result["components"][2]["process_inputs"]["Wrapper"] == {
        "wrapper_sheet_length_mm": 508.0,
        "wrapper_sheet_width_mm": 711.2,
        "wrapper_gsm": 128.0,
        "wrapper_ups": 2,
    }
    assert result["components"][3]["extracted_fields"]["sheet_size"]["review_status"] == "Confirmation Required"

    calculation = _run_calculation(EstimateInput(
        quantity=result["document_fields"]["quantity"]["normalized_value"],
        components=result["components"],
    ))
    modules = {line["module"] for line in calculation["lines"]}
    assert {"Kappa", "Wrapper", "Printing", "Lamination", "Punching"} <= modules
    assert "Insert" not in modules
    assert {"Insert", "Lamination"} <= set(calculation["configuration_required"])
    assert result["components"][0]["processes"]["Base Material"] is True
    assert result["components"][1]["processes"]["Base Material"] is True
    assert result["components"][2]["processes"]["Wrapper"] is True
    assert result["components"][3]["processes"]["Insert"] is True
    assert next(line for line in calculation["lines"] if line["module"] == "Wrapper")["wrapper_final_sheets"] == 2900
    punching_line = next(line for line in calculation["lines"] if line["module"] == "Punching")
    assert {row["component_name"] for row in punching_line["component_lines"]} == {
        "Top-KAPPA-01", "Bottom-KAPPA-02", "WR-01", "INS-DUPLEX-01",
    }
    assert calculation["total_manufacturing_cost"] > 0