import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.formulas import DEFAULT_FORMULAS, FORMULA_DEFINITIONS, evaluate_formula
from backend.routes import (
    EstimateInput,
    MASTER_RATE_DEFAULTS,
    _calculate_conversion_for_material,
    _configuration_audit_detail,
    _configuration_version,
    _effective_master_rates,
    _nearest_punching_die,
    _require_config_permission,
    _run_calculation,
)


def test_kappa_sheet_area_uses_formula_reference_inch_conversion():
    area = evaluate_formula(
        "kappa_sheet_area",
        {"sheet_length_mm": 1000, "sheet_width_mm": 700},
        DEFAULT_FORMULAS,
    )

    assert area == pytest.approx(0.7)


def test_each_cost_module_exposes_one_complete_formula():
    module_groups = {
        "Base Material", "Insert", "Wrapper", "Printing", "Lamination",
        "Glue", "Punching", "Embellishments", "Tooling / Dies",
        "Accessories", "Conversion", "Estimate Totals", "Quotation / Proforma",
    }
    visible_formulas = {
        group: [
            key for key, definition in FORMULA_DEFINITIONS.items()
            if definition["group"] == group and definition.get("visible", True)
        ]
        for group in module_groups
    }

    assert all(len(keys) == 1 for keys in visible_formulas.values())
    assert visible_formulas["Estimate Totals"] == ["estimate_total_cost"]
    assert visible_formulas["Accessories"] == ["accessories_total_cost"]
    assert visible_formulas["Quotation / Proforma"] == ["quotation_complete_grand_total"]


def test_complete_quotation_formula_calculates_subtotal_plus_gst():
    total = evaluate_formula("quotation_complete_grand_total", {
        "unit_price": 100,
        "quantity": 25,
        "gst_percent": 18,
    }, DEFAULT_FORMULAS)

    assert total == pytest.approx(2950)


def test_component_estimate_uses_saved_estimate_total_formula():
    estimate = EstimateInput(quantity=1000, components=[
        {"component_name": "Base Material", "material": "Kappa", "processes": {"Base Material": True}},
        {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True}, "process_inputs": {"Wrapper": {"wrapper_wastage_percent": 0}}},
    ])
    configured_formulas = {
        **DEFAULT_FORMULAS,
        "estimate_total_cost": "sum(module_totals) * 2",
    }

    default_result = _run_calculation(estimate)
    configured_result = _run_calculation(estimate, configured_formulas)

    assert configured_result["total_manufacturing_cost"] == pytest.approx(
        default_result["total_manufacturing_cost"] * 2
    )


def test_component_wrapper_requires_explicit_wastage():
    result = _run_calculation(EstimateInput(components=[{
        "component_name": "Wrapper",
        "material": "Art Paper",
        "processes": {"Wrapper": True},
    }]))

    assert result["wrapper_final_sheets"] is None
    assert "Wrapper" in result["configuration_required"]
    assert all(line["module"] != "Wrapper" for line in result["lines"])

def test_unset_master_wastage_uses_editable_ten_percent_default():
    class SavedConfig:
        rates = {"kappa_wastage_percent": None, "wrapper_wastage_percent": None}

    rates = _effective_master_rates(SavedConfig())

    assert rates["kappa_wastage_percent"] == 10
    assert rates["wrapper_wastage_percent"] == 10
    assert MASTER_RATE_DEFAULTS["kappa_wastage_percent"] == 10


def test_kappa_client_formula_example_matches_expected_cost():
    result = _run_calculation(EstimateInput(
        quantity=1000,
        components=None,
        kappa_thickness_mm=1.8,
        kappa_gsm_at_1mm=1200,
        kappa_sheet_length_mm=1000,
        kappa_sheet_width_mm=700,
        kappa_ups=2,
        kappa_wastage_percent=10,
        kappa_rate_per_kg=80,
    ))

    kappa = next(line for line in result["lines"] if line["module"] == "Kappa")
    assert kappa["total_cost"] == pytest.approx(66528)
    assert kappa["cost_per_box"] == pytest.approx(66.528)


def test_kappa_complete_formula_controls_total_cost_and_preserves_trace():
    estimate = EstimateInput(
        quantity=1000,
        components=None,
        kappa_thickness_mm=1.8,
        kappa_gsm_at_1mm=1200,
        kappa_sheet_length_mm=1000,
        kappa_sheet_width_mm=700,
        kappa_ups=2,
        kappa_wastage_percent=10,
        kappa_rate_per_kg=80,
    )
    result = _run_calculation(estimate, {
        **DEFAULT_FORMULAS,
        "kappa_complete_total_cost": "quantity * rate_per_kg",
    })

    kappa = next(line for line in result["lines"] if line["module"] == "Kappa")
    assert kappa["total_cost"] == pytest.approx(80000)
    assert kappa["trace"][0]["label"] == "Effective GSM"
    assert kappa["trace"][-2]["label"] == "Total Cost"


def test_conversion_reference_formulas_are_registered():
    assert "conversion_semi_total_cost" in DEFAULT_FORMULAS
    assert "conversion_automatic_total_cost" in DEFAULT_FORMULAS
    assert "conversion_contract_total_cost" in DEFAULT_FORMULAS


def test_conversion_semi_automatic_kappa_uses_configured_labour_formula():
    result = _run_calculation(EstimateInput(quantity=1000, components=[
        {"component_name": "Base Material", "material": "Kappa", "processes": {"Conversion": True}},
    ]))

    line = next(item for item in result["lines"] if item["module"] == "Conversion")
    assert line["total_cost"] == pytest.approx(5625)


def test_conversion_automatic_kappa_uses_machine_and_two_setup_cycles():
    result = _run_calculation(EstimateInput(quantity=1000, conversion_type="Automatic", components=[
        {"component_name": "Base Material", "material": "Kappa", "processes": {"Conversion": True}},
    ]))

    line = next(item for item in result["lines"] if item["module"] == "Conversion")
    assert line["total_cost"] == pytest.approx(8076.6667)


def test_conversion_contract_and_default_board_side_pasting():
    contract = _run_calculation(EstimateInput(quantity=1000, conversion_type="Contract", components=[
        {"component_name": "Base Material", "material": "Kappa", "processes": {"Conversion": True}},
    ]))
    side_pasting = _run_calculation(EstimateInput(quantity=1000, components=[
        {"component_name": "Insert1", "material": "FBB", "processes": {"Conversion": True}},
    ]))

    assert next(item for item in contract["lines"] if item["module"] == "Conversion")["total_cost"] == pytest.approx(3000)
    assert next(item for item in side_pasting["lines"] if item["module"] == "Conversion")["total_cost"] == pytest.approx(400)


def test_conversion_module_only_formula_uses_selected_material():
    inputs = EstimateInput(quantity=1000, conversion_type="Semi Automatic", conversion_base_material="FBB")
    line, failure = _calculate_conversion_for_material(inputs, inputs.conversion_base_material)

    assert failure is None
    assert line["total_cost"] == pytest.approx(400)


def test_module_only_conversion_endpoint_calculates_without_component_matrix(monkeypatch):
    import auth
    from app import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(auth, "PUBLIC_APP_ACCESS", True)
    response = TestClient(app).post("/api/estimates/calculate/module", json={
        "module": "Conversion",
        "inputs": {
            "quantity": 1000,
            "conversion_type": "Semi Automatic",
            "conversion_base_material": "FBB",
        },
    })

    assert response.status_code == 200
    assert response.json()["line"]["total_cost"] == pytest.approx(400)


def test_module_only_glue_endpoint_calculates_legacy_glue_rows(monkeypatch):
    import auth
    from app import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(auth, "PUBLIC_APP_ACCESS", True)
    response = TestClient(app).post("/api/estimates/calculate/module", json={
        "module": "Glue",
        "inputs": {
            "quantity": 100,
            "glue_rate_per_kg": 125,
            "glue_lines": [{"name": "Liner", "area_sq_in": 10, "gsm": 20, "rate_per_kg": 125}],
        },
    })

    assert response.status_code == 200
    assert response.json()["line"]["total_cost"] == pytest.approx(1.6129)


@pytest.mark.parametrize(
    ("method", "inputs", "expected"),
    [
        ("Thickness-based", {"insert_thickness_mm": 10, "insert_quantity_per_box": 2}, 150000),
        ("Fixed per insert", {"insert_quantity_per_box": 2, "foam_insert_fixed_rate_per_piece": 3}, 600),
        ("Per kg", {"insert_quantity_per_box": 2, "insert_weight_g_per_piece": 100, "foam_insert_rate_per_kg": 50}, 1000),
    ],
)
def test_foam_insert_pricing_methods(method, inputs, expected):
    result = _run_calculation(EstimateInput(quantity=100, components=[{
        "component_name": "Insert1",
        "material": "EVA",
        "processes": {"Insert": True},
        "process_inputs": {"Insert": {"insert_pricing_method": method, **inputs}},
    }]))

    line = next(item for item in result["lines"] if item["module"] == "Insert")
    assert line["total_cost"] == pytest.approx(expected)


def test_punching_die_uses_nearest_configured_sheet_size():
    nearest = _nearest_punching_die("20x14")

    assert nearest[0] == "15x20"


def test_matrix_tooling_uses_configured_die_rate_and_area_formula():
    punching_die = _run_calculation(EstimateInput(quantity=1000, components=[
        {
            "component_name": "Base Material",
            "material": "Kappa",
            "processes": {"One Time Cost": True},
            "process_inputs": {"One Time Cost": {"tooling_type": "Punching Die", "sheet_size": "20x14"}},
        },
    ]))
    emboss_die = _run_calculation(EstimateInput(quantity=1000, components=[
        {
            "component_name": "Insert1",
            "material": "EVA",
            "processes": {"One Time Cost": True},
            "process_inputs": {"One Time Cost": {"tooling_type": "Emboss/Deboss Die", "area_sq_cm": 10}},
        },
    ]))

    assert next(item for item in punching_die["lines"] if item["module"] == "One Time Cost")["total_cost"] == pytest.approx(1500)
    assert next(item for item in emboss_die["lines"] if item["module"] == "One Time Cost")["total_cost"] == pytest.approx(50)


def test_drip_off_without_confirmed_rate_is_configuration_required():
    result = _run_calculation(EstimateInput(wrapper_wastage_percent=0, components=[
        {
            "component_name": "Wrapper",
            "material": "Art Paper",
            "processes": {"Wrapper": True, "Drip-Off": True},
        },
    ]))

    assert "Embellishments" in result["configuration_required"]
    assert all(line["module"] != "Embellishments" for line in result["lines"])


@pytest.mark.parametrize("rate", ["0.9", "0.95"])
def test_drip_off_accepts_selected_formula_sheet_rate(rate):
    result = _run_calculation(EstimateInput(
        quantity=1,
        wrapper_wastage_percent=0,
        components=[{
            "component_name": "Wrapper",
            "material": "Art Paper",
            "processes": {"Wrapper": True, "Drip-Off": True},
            "process_inputs": {"Drip-Off": {"drip_off_rate_per_100_sq_in": rate}},
        }],
    ))

    line = next(item for item in result["lines"] if item["module"] == "Embellishments")
    assert any(item["label"] == "Rate / 100 sq.in" and item["value"] == rate for item in line["component_lines"][0]["trace"])


def test_lamination_uses_method_defaults_when_finish_rate_is_not_configured():
    component = {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True, "Lamination": True}}
    default_rate = _run_calculation(EstimateInput(wrapper_wastage_percent=10, components=[component]))
    configured_rate = _run_calculation(EstimateInput(
        wrapper_wastage_percent=10,
        lamination_method_finish_rates={"thermal_matte": 0.5},
        components=[component],
    ))
    unknown_method = _run_calculation(EstimateInput(wrapper_wastage_percent=10, lamination_type="unknown", components=[component]))

    default_lamination = next(line for line in default_rate["lines"] if line["module"] == "Lamination")
    lamination = next(line for line in configured_rate["lines"] if line["module"] == "Lamination")
    unknown_lamination = next(line for line in unknown_method["lines"] if line["module"] == "Lamination")
    assert default_lamination["component_lines"][0]["trace"][0]["value"] == "1.1"
    assert lamination["component_lines"][0]["trace"][0]["value"] == "0.5"
    assert unknown_lamination["component_lines"][0]["trace"][0]["value"] == "1.1"


def test_pdf_lamination_uses_selected_master_default_method_and_rate():
    component = {
        "component_name": "Wrapper",
        "material": "Art Paper",
        "source": "pdf_text",
        "processes": {"Wrapper": True, "Lamination": True},
        "extracted_fields": {
            "lamination_finish": {"value": "Matte", "normalized_value": "Matte"},
        },
    }
    result = _run_calculation(EstimateInput(
        quantity=1000,
        wrapper_gsm=100,
        wrapper_ups=2,
        wrapper_sheet_length_mm=711.2,
        wrapper_sheet_width_mm=508,
        lamination_type="thermal",
        lamination_finish="Matte",
        lamination_sheet_length_in=28,
        lamination_sheet_width_in=20,
        components=[component],
    ), master_rates={
        "wrapper_wastage_percent": 10,
        "wrapper_make_ready_sheets": 150,
        "wrapper_rate_per_kg": 95,
        "lamination_thermal": 1.6,
    })

    lamination = next(line for line in result["lines"] if line["module"] == "Lamination")
    assert lamination["component_lines"][0]["trace"][0]["value"] == "1.6"


def test_insert_lamination_uses_insert_sheet_dimensions_instead_of_wrapper_size():
    result = _run_calculation(EstimateInput(
        quantity=1000,
        wrapper_gsm=128,
        wrapper_ups=2,
        wrapper_sheet_length_mm=508,
        wrapper_sheet_width_mm=711.2,
        lamination_type="thermal",
        lamination_finish="Gloss",
        lamination_sheet_length_in=20,
        lamination_sheet_width_in=28,
        components=[
            {
                "component_name": "WR-01",
                "material": "Art Paper",
                "processes": {"Wrapper": True},
                "process_inputs": {"Wrapper": {
                    "wrapper_gsm": 128,
                    "wrapper_ups": 2,
                    "wrapper_sheet_length_mm": 508,
                    "wrapper_sheet_width_mm": 711.2,
                    "wrapper_wastage_percent": 10,
                    "wrapper_make_ready_sheets": 150,
                }},
            },
            {
                "component_name": "INS-DUPLEX-01",
                "material": "Duplex",
                "processes": {"Insert": True, "Lamination": True},
                "process_inputs": {
                    "Insert": {
                        "insert_gsm": 230,
                        "insert_ups": 2,
                        "insert_sheet_length_mm": 762,
                        "insert_sheet_width_mm": 508,
                    },
                    "Lamination": {"lamination_finish": "Gloss"},
                },
            },
        ],
    ), master_rates={
        "wrapper_wastage_percent": 10,
        "wrapper_make_ready_sheets": 150,
        "wrapper_rate_per_kg": 95,
        "lamination_thermal": 1.1,
    })

    lamination = next(line for line in result["lines"] if line["module"] == "Lamination")
    insert_line = next(line for line in lamination["component_lines"] if line["component_name"] == "INS-DUPLEX-01")
    assert insert_line["trace"][1]["value"] == "30.0 × 20.0 × ₹1.1 / 100 = ₹6.60"


def test_lamination_estimate_override_precedes_missing_master_combination():
    result = _run_calculation(EstimateInput(wrapper_wastage_percent=10, lam_override_rate=0.75, components=[
        {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True, "Lamination": True}},
    ]))

    lamination = next(line for line in result["lines"] if line["module"] == "Lamination")
    assert lamination["component_lines"][0]["trace"][0]["value"] == "0.75"


def test_digital_printing_does_not_use_offset_rate_table():
    result = _run_calculation(EstimateInput(wrapper_wastage_percent=10, print_method="Digital", components=[
        {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True, "Printing": True}},
    ]))

    assert "Printing" in result["configuration_required"]
    assert all(line["module"] != "Printing" for line in result["lines"])


def test_master_configuration_permissions_are_role_scoped():
    from types import SimpleNamespace

    view_guard = _require_config_permission("MASTER_CONFIG_VIEW")
    edit_guard = _require_config_permission("MASTER_CONFIG_EDIT")

    assert view_guard(SimpleNamespace(role="Estimator")).role == "Estimator"
    assert view_guard(SimpleNamespace(role="Public")).role == "Public"
    assert edit_guard(SimpleNamespace(role="Administrator")).role == "Administrator"
    rates_guard = _require_config_permission("MASTER_RATES_EDIT")
    assert rates_guard(SimpleNamespace(role="Administrator")).role == "Administrator"
    assert rates_guard(SimpleNamespace(role="Public")).role == "Public"
    with pytest.raises(HTTPException) as error:
        edit_guard(SimpleNamespace(role="Estimator"))
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        rates_guard(SimpleNamespace(role="Estimator"))
    assert error.value.status_code == 403


def test_public_access_keeps_administrator_routes_protected(monkeypatch):
    import auth
    from app import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(auth, "PUBLIC_APP_ACCESS", True)
    client = TestClient(app)

    assert client.get("/api/master-config").status_code == 200
    assert client.get("/api/formulas").status_code == 200
    baseline_calculation = client.post("/api/estimates/calculate", json={"quantity": 1000})
    assert baseline_calculation.status_code == 200
    updated = client.put("/api/master-config", json={"rates": {"kappa_rate_per_kg": 82}})
    assert updated.status_code == 200
    assert updated.json()["rates"]["kappa_rate_per_kg"] == 82
    cleared_wastage = client.put("/api/master-config", json={
        "rates": {"kappa_wastage_percent": None, "wrapper_wastage_percent": None},
    })
    assert cleared_wastage.status_code == 200
    assert cleared_wastage.json()["rates"]["kappa_wastage_percent"] is None
    assert cleared_wastage.json()["rates"]["wrapper_wastage_percent"] is None
    original_formulas = {
        key: definition["expression"]
        for key, definition in client.get("/api/formulas").json()["formulas"].items()
    }
    updated_formulas = client.put(
        "/api/formulas",
        json={"formulas": {
            "selling_price_per_box": "cost_per_box",
            "estimate_total_cost": "sum(module_totals) * 2",
        }},
    )
    assert updated_formulas.status_code == 200
    assert updated_formulas.json()["formulas"]["selling_price_per_box"] == "cost_per_box"
    live_calculation = client.post("/api/estimates/calculate", json={"quantity": 1000})
    assert live_calculation.status_code == 200
    assert live_calculation.json()["total_manufacturing_cost"] == pytest.approx(
        baseline_calculation.json()["total_manufacturing_cost"] * 2
    )
    assert client.put("/api/formulas", json={"formulas": original_formulas}).status_code == 200
    assert client.get("/api/settings").status_code == 401
    assert client.put("/api/settings", json={}).status_code == 401
    assert client.get("/api/audit-log").status_code == 401
    assert client.get("/api/auth/users").status_code == 401


def test_configuration_versions_are_stable_and_content_sensitive():
    config = {"rate": 10, "formula": "quantity * rate"}

    assert _configuration_version(config) == _configuration_version({"formula": "quantity * rate", "rate": 10})
    assert _configuration_version(config) != _configuration_version({**config, "rate": 11})


def test_configuration_audit_detail_contains_required_named_fields():
    from types import SimpleNamespace

    previous = {"rate": 10}
    updated = {"rate": 11}
    detail = json.loads(_configuration_audit_detail(
        SimpleNamespace(full_name="Administrator"),
        "master_rates",
        "Punching",
        previous,
        updated,
    ))

    assert detail["changed_by"] == "Administrator"
    assert detail["changed_at"]
    assert detail["previous_value"] == previous
    assert detail["new_value"] == updated
    assert detail["configuration_type"] == "master_rates"
    assert detail["module"] == "Punching"
    assert detail["version"] == _configuration_version(updated)


def test_board_insert_uses_material_specific_master_rate():
    insert_inputs = {
        "insert_gsm": 230,
        "insert_ups": 2,
        "insert_sheet_length_mm": 762,
        "insert_sheet_width_mm": 508,
    }
    fbb = _run_calculation(EstimateInput(quantity=1000, kappa_wastage_percent=0, fbb_rate_per_kg=88, components=[
        {"component_name": "Insert1", "material": "FBB", "processes": {"Insert": True}, "process_inputs": {"Insert": insert_inputs}},
    ]))
    duplex = _run_calculation(EstimateInput(quantity=1000, kappa_wastage_percent=0, duplex_board_rate_per_kg=72, components=[
        {"component_name": "Insert2", "material": "Duplex", "processes": {"Insert": True}, "process_inputs": {"Insert": insert_inputs}},
    ]))

    fbb_line = next(line for line in fbb["lines"] if line["module"] == "Insert")
    duplex_line = next(line for line in duplex["lines"] if line["module"] == "Insert")
    fbb_trace = fbb_line["component_lines"][0]["trace"]
    duplex_trace = duplex_line["component_lines"][0]["trace"]
    assert any("₹88" in item["value"] for item in fbb_trace)
    assert any("₹72" in item["value"] for item in duplex_trace)
    assert fbb_line["total_cost"] == pytest.approx(1000 / 2 * 0.387096 * 230 / 1000 * 88)
    assert duplex_line["total_cost"] == pytest.approx(1000 / 2 * 0.387096 * 230 / 1000 * 72)


def test_component_specific_glue_and_accessory_inputs_are_used():
    glue = _run_calculation(EstimateInput(quantity=100, components=[
        {"component_name": "Liner", "material": "Art Paper", "processes": {"Glue": True}, "process_inputs": {"Glue": {"glue_area_sq_in": 10, "glue_gsm": 20, "glue_rate_per_kg": 90}}},
        {"component_name": "Insert", "material": "FBB", "processes": {"Glue": True}, "process_inputs": {"Glue": {"glue_area_sq_in": 20, "glue_gsm": 20, "glue_rate_per_kg": 90}}},
    ]))
    accessories = _run_calculation(EstimateInput(quantity=100, components=[
        {"component_name": "Insert1", "material": "EVA", "processes": {"Accessories": True}, "process_inputs": {"Accessories": {"accessory_quantity_per_box": 1, "accessory_unit_cost": 2}}},
        {"component_name": "Insert2", "material": "EPE", "processes": {"Accessories": True}, "process_inputs": {"Accessories": {"accessory_quantity_per_box": 2, "accessory_unit_cost": 3}}},
    ]))

    glue_rows = next(line for line in glue["lines"] if line["module"] == "Glue")["component_lines"]
    accessory_rows = next(line for line in accessories["lines"] if line["module"] == "Accessories")["component_lines"]
    assert glue_rows[1]["total_cost"] == pytest.approx(glue_rows[0]["total_cost"] * 2)
    assert [row["total_cost"] for row in accessory_rows] == [200, 600]


def test_component_glue_uses_master_rate_when_rate_is_inherited():
    estimate = EstimateInput(
        quantity=100,
        glue_rate_per_kg=90,
        components=[{
            "component_name": "Liner",
            "material": "Art Paper",
            "processes": {"Glue": True},
            "process_inputs": {"Glue": {"glue_area_sq_in": 10, "glue_gsm": 20}},
        }],
    )
    result = _run_calculation(estimate, master_rates={"glue_rate_per_kg": 125})

    glue = next(line for line in result["lines"] if line["module"] == "Glue")
    component_line = glue["component_lines"][0]
    assert component_line["total_cost"] == pytest.approx(1.6129)
    assert any(item["label"] == "Liner glue · Rate / kg" and item["value"] == "₹125" for item in component_line["trace"])


def test_component_glue_requires_area_and_gsm_instead_of_costing_zero():
    result = _run_calculation(EstimateInput(components=[{
        "component_name": "Liner",
        "material": "Art Paper",
        "processes": {"Glue": True},
        "process_inputs": {"Glue": {"glue_gsm": 20}},
    }]))

    assert all(line["module"] != "Glue" for line in result["lines"])
    failure = next(detail for detail in result["configuration_details"] if detail["module"] == "Glue")
    assert failure["detail"] == "Enter the glue area (sq.in) for this component."


def test_foiling_uses_component_area_and_configured_per_box_minimum():
    result = _run_calculation(EstimateInput(quantity=1000, embellishment_minimum=1, components=[
        {
            "component_name": "Wrapper",
            "material": "Art Paper",
            "processes": {"Foiling": True},
            "process_inputs": {"Foiling": {"embellishment_area_sq_in": 50, "foiling_rate_per_100_sq_in": 3}},
        },
    ]))

    foil = next(line for line in result["lines"] if line["module"] == "Embellishments")["component_lines"][0]
    assert foil["total_cost"] == pytest.approx(1500)
    assert any("Raw cost / box" in item["label"] and item["value"] == "1.5" for item in foil["trace"])