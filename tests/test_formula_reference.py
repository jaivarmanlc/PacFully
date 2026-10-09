import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.formulas import DEFAULT_FORMULAS, evaluate_formula
from backend.routes import EstimateInput, _configuration_audit_detail, _configuration_version, _nearest_punching_die, _require_config_permission, _run_calculation


def test_kappa_sheet_area_uses_formula_reference_inch_conversion():
    area = evaluate_formula(
        "kappa_sheet_area",
        {"sheet_length_mm": 1000, "sheet_width_mm": 700},
        DEFAULT_FORMULAS,
    )

    assert area == pytest.approx(0.7)


def test_component_estimate_uses_saved_estimate_total_formula():
    estimate = EstimateInput(quantity=1000, components=[
        {"component_name": "Base Material", "material": "Kappa", "processes": {"Base Material": True}},
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
    result = _run_calculation(EstimateInput(components=[
        {
            "component_name": "Wrapper",
            "material": "Art Paper",
            "processes": {"Wrapper": True, "Drip-Off": True},
        },
    ]))

    assert "Embellishments" in result["configuration_required"]
    assert all(line["module"] != "Embellishments" for line in result["lines"])


def test_lamination_uses_method_defaults_when_finish_rate_is_not_configured():
    component = {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True, "Lamination": True}}
    default_rate = _run_calculation(EstimateInput(components=[component]))
    configured_rate = _run_calculation(EstimateInput(
        lamination_method_finish_rates={"thermal_matte": 0.5},
        components=[component],
    ))
    unknown_method = _run_calculation(EstimateInput(lamination_type="unknown", components=[component]))

    default_lamination = next(line for line in default_rate["lines"] if line["module"] == "Lamination")
    lamination = next(line for line in configured_rate["lines"] if line["module"] == "Lamination")
    unknown_lamination = next(line for line in unknown_method["lines"] if line["module"] == "Lamination")
    assert default_lamination["component_lines"][0]["trace"][0]["value"] == "1.1"
    assert lamination["component_lines"][0]["trace"][0]["value"] == "0.5"
    assert unknown_lamination["component_lines"][0]["trace"][0]["value"] == "1.1"


def test_lamination_estimate_override_precedes_missing_master_combination():
    result = _run_calculation(EstimateInput(lam_override_rate=0.75, components=[
        {"component_name": "Wrapper", "material": "Art Paper", "processes": {"Wrapper": True, "Lamination": True}},
    ]))

    lamination = next(line for line in result["lines"] if line["module"] == "Lamination")
    assert lamination["component_lines"][0]["trace"][0]["value"] == "0.75"


def test_digital_printing_does_not_use_offset_rate_table():
    result = _run_calculation(EstimateInput(print_method="Digital", components=[
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
    with pytest.raises(HTTPException) as error:
        edit_guard(SimpleNamespace(role="Estimator"))
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        edit_guard(SimpleNamespace(role="Public"))
    assert error.value.status_code == 403


def test_public_access_keeps_administrator_routes_protected(monkeypatch):
    import auth
    from app import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(auth, "PUBLIC_APP_ACCESS", True)
    client = TestClient(app)

    assert client.get("/api/master-config").status_code == 200
    assert client.get("/api/formulas").status_code == 200
    assert client.put("/api/master-config", json={"rates": {}}).status_code == 403
    assert client.put("/api/formulas", json={"formulas": {}}).status_code == 403
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
    fbb = _run_calculation(EstimateInput(quantity=1000, fbb_rate_per_kg=88, components=[
        {"component_name": "Insert1", "material": "FBB", "processes": {"Insert": True}},
    ]))
    duplex = _run_calculation(EstimateInput(quantity=1000, duplex_board_rate_per_kg=72, components=[
        {"component_name": "Insert2", "material": "Duplex", "processes": {"Insert": True}},
    ]))

    fbb_trace = next(line for line in fbb["lines"] if line["module"] == "Insert")["component_lines"][0]["trace"]
    duplex_trace = next(line for line in duplex["lines"] if line["module"] == "Insert")["component_lines"][0]["trace"]
    assert any("₹88" in item["value"] for item in fbb_trace)
    assert any("₹72" in item["value"] for item in duplex_trace)


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