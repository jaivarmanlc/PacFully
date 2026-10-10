"""
Pacfully Cost Intelligence — complete API routes.
Covers: health, costing engine (stateless), customers CRUD,
estimates CRUD + finalize, quotations + PDF generation, audit log.
"""

import json
import hashlib
import os
import tempfile
import uuid
from datetime import date, datetime, timezone
from math import ceil, isfinite
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from auth import get_formula_user, require_admin
from ai.layout_reader import extract_pdf_layout
from component_process import (
    PROCESS_TO_MODULE,
    component_label,
    components_for_process,
    processes_for_module,
)
from database import get_db
from formulas import DEFAULT_FORMULAS, FORMULA_DEFINITIONS, evaluate_formula, validate_formula_set
from models import AuditEvent, CostLine, Customer, Estimate, FormulaConfiguration, MasterConfiguration, Quotation, SystemSettings
from quotation.pdf_generator import generate_quotation_pdf, generate_proforma_pdf

router = APIRouter()

MASTER_CONFIG_PERMISSIONS = {
    "Administrator": {"MASTER_CONFIG_VIEW", "MASTER_CONFIG_EDIT", "MASTER_RATES_EDIT"},
    "Estimator": {"MASTER_CONFIG_VIEW"},
    "Viewer": {"MASTER_CONFIG_VIEW"},
    "Public": {"MASTER_CONFIG_VIEW", "MASTER_RATES_EDIT"},
}

def _configuration_version(value):
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]

def _configuration_audit_detail(current, configuration_type, module, previous_value, new_value):
    return json.dumps({
        "changed_by": current.full_name,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "previous_value": previous_value,
        "new_value": new_value,
        "configuration_type": configuration_type,
        "module": module,
        "version": _configuration_version(new_value),
    }, default=str)

def _require_config_permission(permission):
    def check_permission(current=Depends(get_formula_user)):
        if permission not in MASTER_CONFIG_PERMISSIONS.get(current.role, set()):
            raise HTTPException(403, f"{permission} permission required")
        return current
    return check_permission

# ── Rate tables (master defaults) ────────────────────────────
PRINT_RATES = {
    "15x20": {"first": 1500.0, "additional": 0.40},
    "20x28": {"first": 3500.0, "additional": 0.50},
    "28x40": {"first": 6500.0, "additional": 0.80},
}
LAMINATION_RATES = {"thermal": 1.10, "cold": 0.70, "dry": 0.80}
PUNCHING_RATES = {
    "Kappa":       {"speed": 400.0, "setup_hours": 0.5},
    "Wrapper":     {"speed": 600.0, "setup_hours": 0.5},
    "FBB":         {"speed": 600.0, "setup_hours": 0.5},
    "Duplex":      {"speed": 600.0, "setup_hours": 0.5},
    "Foam/EVA/EPE":{"speed": 500.0, "setup_hours": 0.5},
}
MASTER_RATE_DEFAULTS = {
    "kappa_rate_per_kg": 80.0,
    "wrapper_rate_per_kg": 95.0,
    "fbb_rate_per_kg": 88.0,
    "duplex_board_rate_per_kg": 72.0,
    "glue_rate_per_kg": 90.0,
    "print_15x20_first": 1500.0,
    "print_15x20_additional": 0.40,
    "print_20x28_first": 3500.0,
    "print_20x28_additional": 0.50,
    "print_28x40_first": 6500.0,
    "print_28x40_additional": 0.80,
    "lamination_thermal": 1.10,
    "lamination_cold": 0.70,
    "lamination_dry": 0.80,
    "lamination_rate_thermal_matte": 0.0,
    "lamination_rate_thermal_gloss": 0.0,
    "lamination_rate_thermal_soft_touch": 0.0,
    "lamination_rate_thermal_other": 0.0,
    "lamination_rate_cold_matte": 0.0,
    "lamination_rate_cold_gloss": 0.0,
    "lamination_rate_cold_soft_touch": 0.0,
    "lamination_rate_cold_other": 0.0,
    "lamination_rate_dry_matte": 0.0,
    "lamination_rate_dry_gloss": 0.0,
    "lamination_rate_dry_soft_touch": 0.0,
    "lamination_rate_dry_other": 0.0,
    "punching_machine_rate_per_hour": 400.0,
    "punching_speed_kappa": 400.0,
    "punching_speed_wrapper": 600.0,
    "punching_speed_fbb": 600.0,
    "punching_speed_duplex": 600.0,
    "punching_speed_foam": 500.0,
    "punching_setup_hours": 0.5,
    "wrapper_make_ready_sheets": 150.0,
    "embellishment_rate_per_sq_in": 2.5,
    "embellishment_setup": 800.0,
    "embellishment_minimum": 1000.0,
    "conversion_machine_rate": 0.0,
    "conversion_labour_rate": 0.0,
    "conversion_setup": 0.0,
    "conversion_semi_boxes_per_hour": 400.0,
    "conversion_semi_workers": 15.0,
    "conversion_monthly_salary": 15000.0,
    "conversion_working_days": 25.0,
    "conversion_hours_per_day": 8.0,
    "conversion_side_pasting_rate_per_box": 0.40,
    "conversion_automatic_boxes_per_hour": 600.0,
    "conversion_automatic_machine_rate": 875.0,
    "conversion_automatic_setup_rate": 645.0,
    "conversion_automatic_setup_hours": 4.0,
    "conversion_contract_rate_per_box": 3.0,
    "foiling_rate_per_100_sq_in": 3.0,
    "spot_uv_rate_per_100_sq_in": 1.0,
    "embossing_cost_per_box": 1.0,
    "debossing_cost_per_box": 1.0,
    "punching_die_15x20": 1500.0,
    "punching_die_20x28": 3000.0,
    "punching_die_25x36": 4000.0,
    "punching_die_28x40": 4000.0,
    "emboss_deboss_die_rate_per_sq_cm": 5.0,
    "foil_stamp_die_rate_per_sq_cm": 5.0,
}
SYSTEM_SETTING_DEFAULTS = {
    "company_name": "Pacfully Packaging Pvt Ltd",
    "gst_number": "33AABCP1234F1Z5",
    "email": "accounts@pacfully.in",
    "phone": "+91 44 1234 5678",
    "address": "120 Business Park, Chennai - 600001, Tamil Nadu, India",
    "bank_details": "Bank: HDFC Bank | A/C: 50100123456789 | IFSC: HDFC0001234 | Branch: Chennai Main",
    "gst_rate": 18.0,
    "hsn_code": "4819",
    "tax_regime": "GST (India)",
    "estimate_prefix": "EST-",
    "quotation_prefix": "QUO-",
    "proforma_prefix": "PI-",
    "next_estimate_number": 125,
}

# ── Pydantic schemas ──────────────────────────────────────────

class GlueLine(BaseModel):
    name: str = "Glue area"
    area_sq_in: float = Field(default=0, ge=0)
    gsm: float = Field(default=20, ge=0)
    rate_per_kg: float = Field(default=90, ge=0)

class AccessoryLine(BaseModel):
    name: str = "Accessory"
    quantity_per_box: float = Field(default=0, ge=0)
    unit_cost: float = Field(default=0, ge=0)

class EstimateComponent(BaseModel):
    component_name: str = Field(min_length=1, max_length=120)
    material: str = Field(min_length=1, max_length=120)
    source: str = "manual"
    processes: dict[str, bool | None] = Field(default_factory=dict)
    process_inputs: dict[str, dict[str, object]] = Field(default_factory=dict)
    extracted_fields: dict[str, dict[str, object]] = Field(default_factory=dict)

class EstimateInput(BaseModel):
    # meta
    customer_id:   int | None = None
    customer_name: str = ""
    job_name:      str = ""
    components: list[EstimateComponent] | None = None
    layout_extraction: dict[str, object] = Field(default_factory=dict)
    # costing
    quantity:             int   = Field(default=1500, gt=0)
    margin_percent:       float = Field(default=20, ge=0, lt=100)
    kappa_thickness_mm:   float = Field(default=2, gt=0)
    kappa_gsm_at_1mm:     float = Field(default=400, ge=0)
    kappa_sheet_length_mm:float = Field(default=710, gt=0)
    kappa_sheet_width_mm: float = Field(default=1010, gt=0)
    kappa_ups:            int   = Field(default=4, gt=0)
    kappa_wastage_percent:float = Field(default=8, ge=0)
    kappa_rate_per_kg:    float = Field(default=80, ge=0)
    fbb_rate_per_kg:      float = Field(default=88, ge=0)
    duplex_board_rate_per_kg: float = Field(default=72, ge=0)
    kappa_master_rate:    float | None = Field(default=None, ge=0)
    kappa_override_rate:  float | None = Field(default=None, ge=0)
    wrapper_gsm:               float = Field(default=128, ge=0)
    wrapper_ups:               int   = Field(default=1, gt=0)
    wrapper_sheet_length_mm:   float = Field(default=711, gt=0)
    wrapper_sheet_width_mm:    float = Field(default=1016, gt=0)
    wrapper_wastage_percent:   float = Field(default=10, ge=0)
    wrapper_make_ready_sheets: int   = Field(default=150, ge=0)
    wrapper_rate_per_kg:       float = Field(default=95, ge=0)
    wrapper_master_rate:       float | None = Field(default=None, ge=0)
    wrapper_override_rate:     float | None = Field(default=None, ge=0)
    print_sheet_size:          str   = "28x40"
    print_method:              str   = "Offset"
    print_colour_configuration: str = "4-Color CMYK"
    print_master_rate:         float | None = Field(default=None, ge=0)
    print_additional_rate:     float | None = Field(default=None, ge=0)
    print_override_rate:       float | None = Field(default=None, ge=0)
    lamination_type:           str   = "thermal"
    lamination_finish:          str   = "Matte"
    lamination_method_finish_rates: dict[str, float] = Field(default_factory=dict)
    lamination_sheet_length_in:float = Field(default=28, gt=0)
    lamination_sheet_width_in: float = Field(default=40, gt=0)
    lam_master_rate:           float | None = Field(default=None, ge=0)
    lam_override_rate:         float | None = Field(default=None, ge=0)
    glue_lines: list[GlueLine] = Field(default_factory=lambda: [
        GlueLine(name="Top Wrapper", area_sq_in=620),
        GlueLine(name="Bottom Wrapper", area_sq_in=480),
    ])
    punching_material:              str   = "Kappa"
    punching_machine_rate_per_hour: float = Field(default=400, ge=0)
    punching_speed:                float | None = Field(default=None, gt=0)
    punching_setup_hours:          float | None = Field(default=None, ge=0)
    embellishment_area_sq_in:       float = Field(default=24, ge=0)
    embellishment_rate_per_sq_in:   float = Field(default=2.5, ge=0)
    embellishment_setup:            float = Field(default=800, ge=0)
    embellishment_minimum:          float = Field(default=1000, ge=0)
    accessories: list[AccessoryLine] = Field(default_factory=lambda: [
        AccessoryLine(name="Magnet Snap", quantity_per_box=1, unit_cost=3.5),
        AccessoryLine(name="Ribbon",      quantity_per_box=1, unit_cost=1.2),
    ])
    conversion_machine_rate:  float = Field(default=0, ge=0)
    conversion_machine_hours: float = Field(default=0, ge=0)
    conversion_labour_rate:   float = Field(default=0, ge=0)
    conversion_labour_hours:  float = Field(default=0, ge=0)
    conversion_setup:         float = Field(default=0, ge=0)
    conversion_type: str = "Semi Automatic"
    conversion_semi_boxes_per_hour: float | None = Field(default=400, gt=0)
    conversion_semi_workers: float | None = Field(default=15, ge=0)
    conversion_monthly_salary: float | None = Field(default=15000, ge=0)
    conversion_working_days: float | None = Field(default=25, gt=0)
    conversion_hours_per_day: float | None = Field(default=8, gt=0)
    conversion_side_pasting_rate_per_box: float | None = Field(default=0.40, ge=0)
    conversion_automatic_boxes_per_hour: float | None = Field(default=600, gt=0)
    conversion_automatic_machine_rate: float | None = Field(default=875, ge=0)
    conversion_automatic_setup_rate: float | None = Field(default=645, ge=0)
    conversion_automatic_setup_hours: float | None = Field(default=4, ge=0)
    conversion_contract_rate_per_box: float | None = Field(default=3, ge=0)
    foiling_rate_per_100_sq_in: float | None = Field(default=3, ge=0)
    spot_uv_rate_per_100_sq_in: float | None = Field(default=1, ge=0)
    drip_off_rate_per_100_sq_in: float | None = Field(default=None, ge=0)
    embossing_cost_per_box: float | None = Field(default=1, ge=0)
    debossing_cost_per_box: float | None = Field(default=1, ge=0)
    punching_die_15x20: float | None = Field(default=1500, ge=0)
    punching_die_20x28: float | None = Field(default=3000, ge=0)
    punching_die_25x36: float | None = Field(default=4000, ge=0)
    punching_die_28x40: float | None = Field(default=4000, ge=0)
    emboss_deboss_die_rate_per_sq_cm: float | None = Field(default=5, ge=0)
    foil_stamp_die_rate_per_sq_cm: float | None = Field(default=5, ge=0)
    eb_method: str   = "box"
    eb_value:  float = Field(default=0, ge=0)

class KappaModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    kappa_thickness_mm: float = Field(gt=0)
    kappa_gsm_at_1mm: float = Field(ge=0)
    kappa_sheet_length_mm: float = Field(gt=0)
    kappa_sheet_width_mm: float = Field(gt=0)
    kappa_ups: int = Field(gt=0)
    kappa_wastage_percent: float = Field(ge=0)
    kappa_rate_per_kg: float = Field(default=80, ge=0)
    kappa_master_rate: float | None = Field(default=None, ge=0)
    kappa_override_rate: float | None = Field(default=None, ge=0)

class WrapperModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    wrapper_gsm: float = Field(ge=0)
    wrapper_ups: int = Field(gt=0)
    wrapper_sheet_length_mm: float = Field(gt=0)
    wrapper_sheet_width_mm: float = Field(gt=0)
    wrapper_wastage_percent: float = Field(ge=0)
    wrapper_make_ready_sheets: int = Field(ge=0)
    wrapper_rate_per_kg: float = Field(default=95, ge=0)
    wrapper_master_rate: float | None = Field(default=None, ge=0)
    wrapper_override_rate: float | None = Field(default=None, ge=0)

class PrintingModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    wrapper_final_sheets: int = Field(gt=0)
    print_sheet_size: str = "28x40"
    print_master_rate: float | None = Field(default=None, ge=0)
    print_additional_rate: float | None = Field(default=None, ge=0)
    print_override_rate: float | None = Field(default=None, ge=0)

class LaminationModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    wrapper_final_sheets: int = Field(gt=0)
    lamination_type: str = "thermal"
    lamination_sheet_length_in: float = Field(gt=0)
    lamination_sheet_width_in: float = Field(gt=0)
    lam_master_rate: float | None = Field(default=None, ge=0)
    lam_override_rate: float | None = Field(default=None, ge=0)

class GlueModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    glue_lines: list[GlueLine]

class PunchingModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    punching_material: str = "Kappa"
    punching_machine_rate_per_hour: float = Field(ge=0)
    punching_speed: float | None = Field(default=None, gt=0)
    punching_setup_hours: float | None = Field(default=None, ge=0)
    wrapper_final_sheets: int | None = Field(default=None, gt=0)

class EmbellishmentsModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    embellishment_area_sq_in: float = Field(ge=0)
    embellishment_rate_per_sq_in: float = Field(ge=0)
    embellishment_setup: float = Field(ge=0)
    embellishment_minimum: float = Field(ge=0)

class AccessoriesModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    accessories: list[AccessoryLine]

class ModuleCalculationRequest(BaseModel):
    module: str
    inputs: dict[str, object]
    components: list[EstimateComponent] | None = None
    estimate_id: int | None = Field(default=None, gt=0)
    other_module_totals: list[float] | None = None

class MasterRatesUpdate(BaseModel):
    rates: dict[str, float]

class FormulaConfigUpdate(BaseModel):
    formulas: dict[str, str]

class SystemSettingsUpdate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    gst_number: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    address: str = Field(default="", max_length=2000)
    bank_details: str = Field(default="", max_length=2000)
    gst_rate: float = Field(default=18, ge=0, le=100)
    hsn_code: str = Field(default="4819", max_length=30)
    tax_regime: str = Field(default="GST (India)", max_length=30)
    estimate_prefix: str = Field(default="EST-", max_length=20)
    quotation_prefix: str = Field(default="QUO-", max_length=20)
    proforma_prefix: str = Field(default="PI-", max_length=20)
    next_estimate_number: int = Field(default=125, gt=0)

class CustomerCreate(BaseModel):
    name:       str
    contact:    str = ""
    email:      str = ""
    phone:      str = ""
    address:    str = ""
    city:       str = ""
    state:      str = ""
    gst_number: str = ""

class QuotationCreate(BaseModel):
    estimate_id:      int | None = Field(default=None, gt=0)
    doc_type:         str   = "Quotation"   # "Quotation" | "Proforma Invoice"
    quotation_number: str | None = Field(default=None, max_length=60, pattern=r"^[A-Za-z0-9._/-]+$")
    document_date:    date | None = None
    customer_name:    str | None = Field(default=None, max_length=200)
    customer_address: str   = ""
    job_name:         str | None = Field(default=None, max_length=300)
    order_quantity:   int | None = Field(default=None, gt=0)
    unit_price:       float | None = Field(default=None, ge=0)
    gst_percent:      float = Field(default=18.0, ge=0, lt=100)
    validity_days:    int   = Field(default=15, ge=0)
    notes:            str   = "1. Prices are valid for 15 days.\n2. This is a budgetary quotation.\n3. Final pricing may vary based on final artwork and specifications."

# ── helpers ───────────────────────────────────────────────────

def _next_estimate_number(db: Session) -> str:
    count = db.query(Estimate).count()
    return f"EST-{count + 1:05d}"

def _next_quotation_number(db: Session, doc_type: str) -> str:
    prefix = "PI" if "Proforma" in doc_type else "QUO"
    count  = db.query(Quotation).filter(Quotation.doc_type == doc_type).count()
    now    = datetime.utcnow()
    return f"{prefix}-{now.year}-{now.month:02d}-{count + 1:04d}"

def _audit(db: Session, action: str, entity_type: str, entity_id: str,
           detail: str = "", estimate_id: int | None = None,
           user: str = "System", old_val: str = "", new_val: str = ""):
    ev = AuditEvent(
        estimate_id=estimate_id, user=user, action=action,
        entity_type=entity_type, entity_id=entity_id,
        detail=detail, old_value=old_val, new_value=new_val,
    )
    db.add(ev)

def _active_formulas(db: Session) -> dict[str, str]:
    config = db.query(FormulaConfiguration).filter(FormulaConfiguration.id == 1).first()
    return validate_formula_set(config.formulas if config else {})

def _costing_line(module, total, quantity, rows, unit_cost, unit_label, formula, formulas=DEFAULT_FORMULAS):
    if unit_label == "box":
        unit_cost = evaluate_formula("module_cost_per_box", {"total_cost": total, "quantity": quantity}, formulas)
    return {
        "module":      module,
        "total_cost":  round(total, 4),
        "cost_per_box":round(evaluate_formula("module_cost_per_box", {"total_cost": total, "quantity": quantity}, formulas), 4),
        "unit_cost":   round(unit_cost, 4),
        "unit_label":  unit_label,
        "formula":     formula,
        "trace":       [{"label": l, "value": str(v)} for l, v in rows],
    }

def _effective_rate(override_rate, master_rate, fallback_rate):
    return override_rate if override_rate is not None else master_rate if master_rate is not None else fallback_rate

def _calculate_kappa(p, formulas=DEFAULT_FORMULAS):
    qty = p.quantity
    eff_kappa_gsm = evaluate_formula("kappa_effective_gsm", {"gsm_at_1mm": p.kappa_gsm_at_1mm, "thickness_mm": p.kappa_thickness_mm}, formulas)
    kappa_area_m2 = evaluate_formula("kappa_sheet_area", {"sheet_length_mm": p.kappa_sheet_length_mm, "sheet_width_mm": p.kappa_sheet_width_mm}, formulas)
    kappa_kg_sheet = evaluate_formula("kappa_kg_per_sheet", {"sheet_area_m2": kappa_area_m2, "effective_gsm": eff_kappa_gsm}, formulas)
    kappa_base = int(evaluate_formula("kappa_base_sheets", {"quantity": qty, "ups": p.kappa_ups}, formulas))
    kappa_waste = int(evaluate_formula("kappa_wastage_sheets", {"base_sheets": kappa_base, "wastage_percent": p.kappa_wastage_percent}, formulas))
    kappa_final = int(evaluate_formula("kappa_final_sheets", {"base_sheets": kappa_base, "wastage_sheets": kappa_waste}, formulas))
    kappa_kg = evaluate_formula("kappa_total_kg", {"final_sheets": kappa_final, "kg_per_sheet": kappa_kg_sheet}, formulas)
    rate           = _effective_rate(p.kappa_override_rate, p.kappa_master_rate, p.kappa_rate_per_kg)
    kappa_per_sheet_cost = evaluate_formula("kappa_per_sheet", {"kg_per_sheet": kappa_kg_sheet, "rate_per_kg": rate}, formulas)
    kappa_total = evaluate_formula("kappa_total_cost", {"total_kg": kappa_kg, "rate_per_kg": rate}, formulas)
    line = _costing_line("Kappa", kappa_total, qty, [
        ("Effective GSM",    f"{p.kappa_gsm_at_1mm} × {p.kappa_thickness_mm} = {eff_kappa_gsm}"),
        ("Base sheets",      kappa_base), ("Wastage sheets", kappa_waste),
        ("Final sheets",     kappa_final), ("Total KG", f"{kappa_kg:.4f}"),
        ("Per Sheet Cost",   f"{kappa_kg_sheet:.4f} × ₹{rate:g} = ₹{kappa_per_sheet_cost:.2f} / sheet"),
    ], kappa_per_sheet_cost, "sheet", formulas["kappa_total_cost"], formulas)
    return line

def _calculate_wrapper(p, formulas=DEFAULT_FORMULAS):
    qty = p.quantity
    wrapper_base = int(evaluate_formula("wrapper_base_sheets", {"quantity": qty, "ups": p.wrapper_ups}, formulas))
    wrapper_waste = int(evaluate_formula("wrapper_wastage_sheets", {"base_sheets": wrapper_base, "wastage_percent": p.wrapper_wastage_percent}, formulas))
    wrapper_final = int(evaluate_formula("wrapper_final_sheets", {"base_sheets": wrapper_base, "wastage_sheets": wrapper_waste, "make_ready_sheets": p.wrapper_make_ready_sheets}, formulas))
    wrapper_kg_sh = evaluate_formula("wrapper_kg_per_sheet", {"sheet_length_mm": p.wrapper_sheet_length_mm, "sheet_width_mm": p.wrapper_sheet_width_mm, "gsm": p.wrapper_gsm}, formulas)
    wrapper_kg = evaluate_formula("wrapper_total_kg", {"final_sheets": wrapper_final, "kg_per_sheet": wrapper_kg_sh}, formulas)
    rate           = _effective_rate(p.wrapper_override_rate, p.wrapper_master_rate, p.wrapper_rate_per_kg)
    wrapper_total = evaluate_formula("wrapper_total_cost", {"total_kg": wrapper_kg, "rate_per_kg": rate}, formulas)
    wrapper_per_sheet = evaluate_formula("wrapper_per_sheet", {"kg_per_sheet": wrapper_kg_sh, "rate_per_kg": rate}, formulas)
    line = _costing_line("Wrapper", wrapper_total, qty, [
        ("Base sheets",      wrapper_base), ("Wastage sheets", wrapper_waste),
        ("Make-ready",       p.wrapper_make_ready_sheets),
        ("Final sheets",     wrapper_final), ("Total KG", f"{wrapper_kg:.4f}"),
        ("Per Sheet Cost",   f"{wrapper_kg_sh:.4f} × ₹{rate:g} = ₹{wrapper_per_sheet:.2f} / sheet"),
    ], wrapper_per_sheet, "sheet", formulas["wrapper_total_cost"], formulas)
    return line, wrapper_final

def _calculate_printing(p, wrapper_final, formulas=DEFAULT_FORMULAS):
    pr             = PRINT_RATES.get(p.print_sheet_size, PRINT_RATES["28x40"])
    master_first   = getattr(p, "print_master_rate", None)
    first_rate     = p.print_override_rate if p.print_override_rate is not None else (master_first if master_first is not None else pr["first"])
    additional_rate = getattr(p, "print_additional_rate", None)
    if additional_rate is None:
        additional_rate = pr["additional"]
    printing_total = evaluate_formula("printing_total_cost", {"first_rate": first_rate, "input_sheets": wrapper_final, "additional_rate": additional_rate}, formulas)
    printing_per_sheet = evaluate_formula("printing_per_sheet", {"total_cost": printing_total, "input_sheets": wrapper_final}, formulas)
    return _costing_line("Printing", printing_total, p.quantity, [
        ("Input",            f"{wrapper_final} final wrapper sheets"),
        ("Sheet tier",       p.print_sheet_size),
        ("First-tier rate",  first_rate), ("Additional rate", additional_rate),
        ("Per Sheet Cost",   f"₹{printing_total:.2f} ÷ {wrapper_final} = ₹{printing_per_sheet:.2f} / sheet"),
    ], printing_per_sheet, "sheet", formulas["printing_total_cost"], formulas)

def _calculate_lamination(p, wrapper_final, formulas=DEFAULT_FORMULAS):
    configured_rate = getattr(p, "lam_master_rate", None)
    master_rate    = configured_rate if configured_rate is not None else LAMINATION_RATES.get(p.lamination_type, 1.10)
    lam_rate       = p.lam_override_rate if p.lam_override_rate is not None else master_rate
    lam_per_sheet = evaluate_formula("lamination_per_sheet", {"sheet_length_in": p.lamination_sheet_length_in, "sheet_width_in": p.lamination_sheet_width_in, "rate_per_100_sq_in": lam_rate}, formulas)
    lamination_total = evaluate_formula("lamination_total_cost", {"cost_per_sheet": lam_per_sheet, "wrapper_final_sheets": wrapper_final}, formulas)
    return _costing_line("Lamination", lamination_total, p.quantity, [
        ("Rate/100 sq.in",   lam_rate),
        ("Cost/sheet",       f"{p.lamination_sheet_length_in} × {p.lamination_sheet_width_in} × ₹{lam_rate:g} / 100 = ₹{lam_per_sheet:.2f}"),
        ("Input",            f"{wrapper_final} wrapper sheets"),
    ], lam_per_sheet, "sheet", formulas["lamination_total_cost"], formulas)

def _calculate_glue(p, formulas=DEFAULT_FORMULAS):
    # Glue: weight per box × rate × quantity = total order glue cost
    component_costs = []
    for glue_line in p.glue_lines:
        kg_per_box = evaluate_formula("glue_kg_per_box", {"area_sq_in": glue_line.area_sq_in, "gsm": glue_line.gsm}, formulas)
        component_costs.append(evaluate_formula("glue_component_cost", {"kg_per_box": kg_per_box, "rate_per_kg": glue_line.rate_per_kg, "quantity": p.quantity}, formulas))
    glue_total = evaluate_formula("glue_total_cost", {"component_costs": component_costs}, formulas)
    return _costing_line("Glue", glue_total, p.quantity, [
        ("Formula",          "Area × 0.00064516 × GSM / 1000 × rate"),
        ("Components",       len(p.glue_lines)),
        ("Cost / Box",       f"₹{glue_total / p.quantity:.2f}"),
    ], glue_total / p.quantity, "box", formulas["glue_total_cost"], formulas)

def _calculate_punching(p, wrapper_final, formulas=DEFAULT_FORMULAS):
    punch          = dict(PUNCHING_RATES.get(p.punching_material, PUNCHING_RATES["Kappa"]))
    configured_speed = getattr(p, "punching_speed", None)
    configured_setup = getattr(p, "punching_setup_hours", None)
    if configured_speed is not None:
        punch["speed"] = configured_speed
    if configured_setup is not None:
        punch["setup_hours"] = configured_setup
    is_wrapper = p.punching_material == "Wrapper"
    punch_quantity = int(evaluate_formula("punching_input_quantity", {"wrapper_final_sheets": wrapper_final or 0, "is_wrapper": is_wrapper, "quantity": p.quantity}, formulas))
    prod_hrs = evaluate_formula("punching_production_hours", {"input_quantity": punch_quantity, "speed": punch["speed"]}, formulas)
    punching_total = evaluate_formula("punching_total_cost", {"production_hours": prod_hrs, "setup_hours": punch["setup_hours"], "machine_rate": p.punching_machine_rate_per_hour}, formulas)
    punch_unit = "sheet" if p.punching_material == "Wrapper" else "box"
    punch_unit_count = punch_quantity if punch_unit == "sheet" else p.quantity
    return _costing_line("Punching", punching_total, p.quantity, [
        ("Speed",            punch["speed"]),
        ("Production hrs",   f"{prod_hrs:.4f}"),
        ("Setup hrs",        punch["setup_hours"]),
        ("Machine rate",     f"₹{p.punching_machine_rate_per_hour:.2f} / hr"),
        ("Cost / Box",       f"₹{punching_total / p.quantity:.2f}"),
    ], evaluate_formula("punching_unit_cost", {"total_cost": punching_total, "unit_quantity": punch_unit_count}, formulas), punch_unit, formulas["punching_total_cost"], formulas)

def _calculate_embellishments(p, formulas=DEFAULT_FORMULAS):
    emb_raw = evaluate_formula("embellishments_raw_cost", {"area_sq_in": p.embellishment_area_sq_in, "rate_per_sq_in": p.embellishment_rate_per_sq_in, "setup_cost": p.embellishment_setup}, formulas)
    emb_total = evaluate_formula("embellishments_total_cost", {"raw_cost": emb_raw, "tool_cost": p.embellishment_minimum}, formulas)
    return _costing_line("Embellishments", emb_total, p.quantity, [
        ("Raw cost",         f"₹{emb_raw:.2f}"),
        ("Tool Cost",        f"₹{p.embellishment_minimum:.2f}"),
        ("Applied cost",     f"₹{emb_total:.2f}"),
        ("Cost / Box",       f"₹{emb_total / p.quantity:.2f}"),
    ], emb_total / p.quantity, "box", formulas["embellishments_total_cost"], formulas)

def _calculate_accessories(p, formulas=DEFAULT_FORMULAS):
    accessory_costs = [evaluate_formula("accessory_component_cost", {"quantity_per_box": item.quantity_per_box, "unit_cost": item.unit_cost, "quantity": p.quantity}, formulas) for item in p.accessories]
    acc_total = evaluate_formula("accessories_total_cost", {"accessory_costs": accessory_costs}, formulas)
    return _costing_line("Accessories", acc_total, p.quantity, [
        ("Formula",          "Qty/box × unit cost × order qty"),
        ("Items",            len(p.accessories)),
        ("Cost / Box",       f"₹{acc_total / p.quantity:.2f}"),
    ], acc_total / p.quantity, "box", formulas["accessories_total_cost"], formulas)

def _calculate_conversion(p, formulas=DEFAULT_FORMULAS):
    conv_total = evaluate_formula("conversion_total_cost", {"machine_rate": p.conversion_machine_rate, "machine_hours": p.conversion_machine_hours, "labour_rate": p.conversion_labour_rate, "labour_hours": p.conversion_labour_hours, "setup_cost": p.conversion_setup}, formulas)
    return _costing_line("Conversion", conv_total, p.quantity, [
        ("Status",           "CONFIGURATION REQUIRED"),
        ("Machine+Labour+Setup", conv_total),
    ], conv_total / p.quantity, "box", formulas["conversion_total_cost"], formulas)

def _calculate_eb(p):
    return _costing_line("EB", 0, p.quantity, [
        ("Status",           "CONFIGURATION REQUIRED"),
        ("Formula",          "Not defined"),
    ], 0, "box", "Not defined", DEFAULT_FORMULAS)

def _run_calculation(p: EstimateInput, formulas=DEFAULT_FORMULAS) -> dict:
    """Calculate the complete estimate in dependency order."""
    if p.components is not None:
        return _run_component_calculation(p, formulas)

    qty = p.quantity

    kappa_line = _calculate_kappa(p, formulas)
    wrapper_line, wrapper_final = _calculate_wrapper(p, formulas)
    printing_line = _calculate_printing(p, wrapper_final, formulas)
    lamination_line = _calculate_lamination(p, wrapper_final, formulas)
    glue_line = _calculate_glue(p, formulas)
    punching_line = _calculate_punching(p, wrapper_final, formulas)
    embellishments_line = _calculate_embellishments(p, formulas)
    accessories_line = _calculate_accessories(p, formulas)
    conversion_line = _calculate_conversion(p, formulas)
    eb_line = _calculate_eb(p)

    lines = [
        kappa_line, wrapper_line, printing_line, lamination_line, glue_line,
        punching_line, embellishments_line, accessories_line, conversion_line, eb_line,
    ]

    total = evaluate_formula("estimate_total_cost", {"module_totals": [line["total_cost"] for line in lines]}, formulas)
    cpb = evaluate_formula("estimate_cost_per_box", {"total_cost": total, "quantity": qty}, formulas)
    selling_p = evaluate_formula("selling_price_per_box", {"cost_per_box": cpb, "margin_percent": p.margin_percent}, formulas)
    order_val = evaluate_formula("order_value", {"selling_price_per_box": selling_p, "quantity": qty}, formulas)

    for l in lines:
        l["weightage_percent"] = round(evaluate_formula("module_weightage", {"module_total": l["total_cost"], "total_cost": total}, formulas), 4)

    return {
        "order_quantity":           qty,
        "total_manufacturing_cost": round(total, 4),
        "cost_per_box":             round(cpb, 4),
        "margin_percent":           p.margin_percent,
        "selling_price_per_box":    round(selling_p, 4),
        "order_value":              round(order_val, 4),
        "wrapper_final_sheets":     wrapper_final,
        "lines":                    lines,
        "configuration_required":   ["Conversion", "EB"],
    }

def _component_estimate_input(p, component, process, module):
    values = p.model_dump(exclude={"components"})
    values.update(component.process_inputs.get(module, {}))
    values.update(component.process_inputs.get(process, {}))
    values["quantity"] = p.quantity
    row_values = {
        **component.process_inputs.get(module, {}),
        **component.process_inputs.get(process, {}),
    }
    if module == "Glue" and any(key in row_values for key in ("glue_area_sq_in", "glue_gsm", "glue_rate_per_kg")):
        values["glue_lines"] = [{
            "name": f"{component.component_name} glue",
            "area_sq_in": row_values.get("glue_area_sq_in", 0),
            "gsm": row_values.get("glue_gsm", 20),
            "rate_per_kg": row_values.get("glue_rate_per_kg", 90),
        }]
    if module == "Accessories" and any(key in row_values for key in ("accessory_quantity_per_box", "accessory_unit_cost")):
        values["accessories"] = [{
            "name": component.component_name,
            "quantity_per_box": row_values.get("accessory_quantity_per_box", 0),
            "unit_cost": row_values.get("accessory_unit_cost", 0),
        }]
    return EstimateInput.model_validate(values)

def _nearest_punching_die(sheet_size):
    try:
        length, width = (float(value) for value in sheet_size.lower().replace(" ", "").split("x", 1))
    except (AttributeError, TypeError, ValueError):
        return None
    configured = {
        "15x20": (15, 20, "punching_die_15x20"),
        "20x28": (20, 28, "punching_die_20x28"),
        "25x36": (25, 36, "punching_die_25x36"),
        "28x40": (28, 40, "punching_die_28x40"),
    }
    return min(
        configured.items(),
        key=lambda item: min(
            (length - item[1][0]) ** 2 + (width - item[1][1]) ** 2,
            (length - item[1][1]) ** 2 + (width - item[1][0]) ** 2,
        ),
    )

def _calculate_component_line(module, process, component, p, formulas, wrapper_final):
    row_input = _component_estimate_input(p, component, process, module)
    if module in {"Kappa", "Insert"}:
        if module == "Insert":
            sheet_size = component.extracted_fields.get("sheet_size", {}).get("normalized_value")
            if component.source == "pdf_text" and (not sheet_size or sheet_size.get("unit") not in {"mm", "in"}):
                return None, "Confirm the insert sheet-size unit before costing."
            material = component.material.strip().upper()
            material_rates = {
                "KAPPA": row_input.kappa_master_rate,
                "KAPPA BOARD": row_input.kappa_master_rate,
                "FBB": row_input.fbb_rate_per_kg,
                "DUPLEX": row_input.duplex_board_rate_per_kg,
                "DUPLEX BOARD": row_input.duplex_board_rate_per_kg,
            }
            if material in {"EVA", "EPE", "PU"}:
                return None, "Insert costing for EVA/EPE/PU requires a confirmed thickness-based rate."
            if material not in material_rates:
                return None, f"Insert costing for {component.material} is not configured."
            row_input.kappa_master_rate = material_rates[material]
            row_input.kappa_rate_per_kg = row_input.kappa_override_rate if row_input.kappa_override_rate is not None else material_rates[material]
        line = _calculate_kappa(row_input, formulas)
    elif module == "Wrapper":
        line, _ = _calculate_wrapper(row_input, formulas)
    elif module == "Printing":
        if wrapper_final is None:
            return None, "Wrapper final sheets are unavailable. Calculate an applicable Wrapper row first."
        if row_input.print_method.strip().lower() != "offset":
            return None, "Digital printing rates are not configured."
        line = _calculate_printing(row_input, wrapper_final, formulas)
    elif module == "Lamination":
        if wrapper_final is None:
            return None, "Wrapper final sheets are unavailable. Calculate an applicable Wrapper row first."
        finish_field = component.extracted_fields.get("lamination_finish", {})
        if process == "Lamination" and component.source == "pdf_text" and not finish_field.get("normalized_value"):
            return None, "Confirm the extracted lamination finish before costing."
        finish_key = row_input.lamination_finish.strip().lower().replace(" ", "_")
        rate_key = f"{row_input.lamination_type.strip().lower()}_{finish_key}"
        finish_rate = row_input.lamination_method_finish_rates.get(rate_key)
        if finish_rate is None or finish_rate <= 0:
            finish_rate = LAMINATION_RATES.get(row_input.lamination_type.strip().lower(), LAMINATION_RATES["thermal"])
        row_input.lam_master_rate = finish_rate
        line = _calculate_lamination(row_input, wrapper_final, formulas)
    elif module == "Glue":
        line = _calculate_glue(row_input, formulas)
    elif module == "Punching":
        material_map = {
            "KAPPA BOARD": "Kappa", "KAPPA": "Kappa", "ART PAPER": "Wrapper",
            "WRAPPER": "Wrapper", "FBB": "FBB", "DUPLEX": "Duplex",
            "DUPLEX BOARD": "Duplex", "EVA": "Foam/EVA/EPE", "EPE": "Foam/EVA/EPE",
            "PU": "Foam/EVA/EPE",
        }
        material = material_map.get(component.material.upper())
        if material is None and "KAPPA" in component.material.upper():
            material = "Kappa"
        if material is None:
            return None, f"Punching parameters for {component.material} are not configured."
        row_input.punching_material = material
        if material == "Wrapper" and wrapper_final is None:
            return None, "Wrapper final sheets are unavailable. Calculate an applicable Wrapper row first."
        line = _calculate_punching(row_input, wrapper_final, formulas)
    elif module == "Embellishments":
        if process == "Foiling":
            rate = row_input.foiling_rate_per_100_sq_in
            if rate is None:
                return None, "Foiling rate per 100 sq.in is CONFIGURATION REQUIRED."
            raw_cost_per_box = evaluate_formula("embellishment_area_raw_cost", {"area_sq_in": row_input.embellishment_area_sq_in, "rate_per_100_sq_in": rate}, formulas)
            total = evaluate_formula("embellishment_area_total_cost", {"raw_cost_per_box": raw_cost_per_box, "minimum_cost_per_box": row_input.embellishment_minimum, "quantity": row_input.quantity}, formulas)
            line = _costing_line("Embellishments", total, row_input.quantity, [
                ("Process", process), ("Component area (sq.in)", row_input.embellishment_area_sq_in),
                ("Rate / 100 sq.in", rate), ("Raw cost / box", raw_cost_per_box),
                ("Minimum cost / box", row_input.embellishment_minimum),
            ], total / row_input.quantity, "box", formulas["embellishment_area_total_cost"], formulas)
        elif process in {"Spot UV", "Drip-Off"}:
            if wrapper_final is None:
                return None, "Wrapper final sheets are unavailable for surface finishing."
            rate_key = "spot_uv_rate_per_100_sq_in" if process == "Spot UV" else "drip_off_rate_per_100_sq_in"
            rate = getattr(row_input, rate_key)
            if rate is None:
                return None, f"{process} rate per 100 sq.in is CONFIGURATION REQUIRED."
            cost_per_sheet = evaluate_formula("lamination_per_sheet", {"sheet_length_in": row_input.lamination_sheet_length_in, "sheet_width_in": row_input.lamination_sheet_width_in, "rate_per_100_sq_in": rate}, formulas)
            total = evaluate_formula("lamination_total_cost", {"cost_per_sheet": cost_per_sheet, "wrapper_final_sheets": wrapper_final}, formulas)
            line = _costing_line("Embellishments", total, row_input.quantity, [
                ("Process", process), ("Rate / 100 sq.in", rate),
                ("Cost / sheet", cost_per_sheet), ("Wrapper final sheets", wrapper_final),
            ], cost_per_sheet, "sheet", formulas["lamination_total_cost"], formulas)
        elif process in {"Embossing", "Debossing"}:
            rate_key = "embossing_cost_per_box" if process == "Embossing" else "debossing_cost_per_box"
            rate = getattr(row_input, rate_key)
            if rate is None:
                return None, f"{process} direct cost per box is CONFIGURATION REQUIRED."
            total = evaluate_formula("embellishment_direct_cost_total", {"rate_per_box": rate, "quantity": row_input.quantity}, formulas)
            line = _costing_line("Embellishments", total, row_input.quantity, [("Process", process), ("Direct cost / box", rate)], total / row_input.quantity, "box", formulas["embellishment_direct_cost_total"], formulas)
        else:
            return None, f"{process} is CONFIGURATION REQUIRED."
    elif module == "Accessories":
        line = _calculate_accessories(row_input, formulas)
    elif module == "Conversion":
        material = component.material.strip().upper()
        conversion_type = row_input.conversion_type.strip().lower()
        is_kappa = material in {"KAPPA", "KAPPA BOARD", "BASE MATERIAL"}
        if conversion_type == "contract":
            rate = row_input.conversion_contract_rate_per_box
            if rate is None:
                return None, "Contract conversion rate per box is not configured."
            total = evaluate_formula("conversion_contract_total_cost", {"rate_per_box": rate, "quantity": row_input.quantity}, formulas)
            conversion_formula = formulas["conversion_contract_total_cost"]
            trace = [("Method", "Contract"), ("Rate / box", rate), ("Order quantity", row_input.quantity)]
        elif conversion_type == "automatic" and is_kappa:
            boxes_per_hour = row_input.conversion_automatic_boxes_per_hour
            machine_rate = row_input.conversion_automatic_machine_rate
            setup_rate = row_input.conversion_automatic_setup_rate
            setup_hours = row_input.conversion_automatic_setup_hours
            if any(value is None for value in (boxes_per_hour, machine_rate, setup_rate, setup_hours)):
                return None, "Automatic Kappa conversion parameters are not configured."
            machine_hours = evaluate_formula("conversion_automatic_machine_hours", {"quantity": row_input.quantity, "boxes_per_hour": boxes_per_hour}, formulas)
            total = evaluate_formula("conversion_automatic_total_cost", {"machine_hours": machine_hours, "machine_rate": machine_rate, "setup_hours": setup_hours, "setup_rate": setup_rate}, formulas)
            conversion_formula = formulas["conversion_automatic_total_cost"]
            trace = [("Method", "Automatic"), ("Machine hours", machine_hours), ("Machine rate / hr", machine_rate), ("Setup hours", setup_hours), ("Setup rate / hr", setup_rate)]
        elif conversion_type == "semi automatic" and is_kappa:
            boxes_per_hour = row_input.conversion_semi_boxes_per_hour
            workers = row_input.conversion_semi_workers
            salary = row_input.conversion_monthly_salary
            workdays = row_input.conversion_working_days
            hours_per_day = row_input.conversion_hours_per_day
            if any(value is None for value in (boxes_per_hour, workers, salary, workdays, hours_per_day)):
                return None, "Semi-automatic Kappa conversion parameters are not configured."
            machine_hours = evaluate_formula("conversion_semi_machine_hours", {"quantity": row_input.quantity, "boxes_per_hour": boxes_per_hour}, formulas)
            total = evaluate_formula("conversion_semi_total_cost", {"workers": workers, "monthly_salary": salary, "working_days": workdays, "hours_per_day": hours_per_day, "machine_hours": machine_hours}, formulas)
            conversion_formula = formulas["conversion_semi_total_cost"]
            trace = [("Method", "Semi Automatic"), ("Machine hours", machine_hours), ("Workers", workers), ("Monthly salary", salary), ("Working days", workdays), ("Hours per day", hours_per_day)]
        elif material in {"FBB", "DUPLEX", "DUPLEX BOARD", "KRAFT"} and conversion_type == "semi automatic":
            rate = row_input.conversion_side_pasting_rate_per_box
            if rate is None:
                return None, "Side-pasting rate per box is not configured."
            total = evaluate_formula("conversion_side_pasting_total_cost", {"rate_per_box": rate, "quantity": row_input.quantity}, formulas)
            conversion_formula = formulas["conversion_side_pasting_total_cost"]
            trace = [("Method", "Side Pasting"), ("Rate / box", rate), ("Order quantity", row_input.quantity)]
        else:
            return None, f"{conversion_type.title()} conversion is not configured for {component.material}."
        line = _costing_line("Conversion", total, row_input.quantity, trace, total / row_input.quantity, "box", conversion_formula, formulas)
    elif module == "One Time Cost":
        tooling = component.process_inputs.get(process, {})
        tooling_type = str(tooling.get("tooling_type", "")).strip()
        if tooling_type == "Punching Die":
            nearest = _nearest_punching_die(str(tooling.get("sheet_size", "")))
            if nearest is None:
                return None, "Enter a valid sheet size for nearest-size Punching Die costing."
            size_key, (_, _, rate_key) = nearest
            rate = getattr(row_input, rate_key)
            if rate is None:
                return None, f"Punching Die rate for {size_key} is CONFIGURATION REQUIRED."
            total = rate
            formula = f"Nearest configured Punching Die rate ({size_key})"
            trace = [("Tooling type", tooling_type), ("Entered sheet size", tooling.get("sheet_size")), ("Nearest configured size", size_key), ("Die rate", rate)]
        elif tooling_type in {"Emboss/Deboss Die", "Foil Stamp Die"}:
            area = tooling.get("area_sq_cm")
            rate_key = "foil_stamp_die_rate_per_sq_cm" if tooling_type == "Foil Stamp Die" else "emboss_deboss_die_rate_per_sq_cm"
            rate = getattr(row_input, rate_key)
            if area is None or rate is None:
                return None, f"Area and configured rate are required for {tooling_type}."
            total = evaluate_formula("tooling_area_die_cost", {"area_sq_cm": float(area), "rate_per_sq_cm": rate}, formulas)
            formula = formulas["tooling_area_die_cost"]
            trace = [("Tooling type", tooling_type), ("Area (sq.cm)", area), ("Rate / sq.cm", rate)]
        else:
            return None, "Select a configured tooling or die type."
        line = _costing_line("One Time Cost", total, row_input.quantity, trace, total, "lot", formula, formulas)
    else:
        return None, f"{module} is CONFIGURATION REQUIRED."

    line.update({
        "component_name": component.component_name,
        "material": component.material,
        "component_label": component_label(component.model_dump()),
        "process": process,
    })
    return line, None

def _run_component_calculation(p, formulas=DEFAULT_FORMULAS, only_module=None):
    """Calculate routed rows from the submitted matrix without creating NO rows."""
    unknown_processes = {
        process
        for component in p.components or []
        for process in component.processes
        if process not in PROCESS_TO_MODULE
    }
    if unknown_processes:
        raise ValueError(f"Unknown component processes: {', '.join(sorted(unknown_processes))}")

    quantity = p.quantity
    module_order = ["Kappa", "Wrapper", "Insert", "Printing", "Lamination", "Punching", "Glue", "Embellishments", "Accessories", "Conversion", "EB", "One Time Cost"]
    wrapper_rows = []
    wrapper_sheets = []
    for component in components_for_process(p.components or [], "Wrapper"):
        try:
            row_input = _component_estimate_input(p, component, "Wrapper", "Wrapper")
            line, final_sheets = _calculate_wrapper(row_input, formulas)
            line.update({
                "component_name": component.component_name,
                "material": component.material,
                "component_label": component_label(component.model_dump()),
                "process": "Wrapper",
            })
            wrapper_rows.append(line)
            wrapper_sheets.append(final_sheets)
        except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
            wrapper_rows.append({"status": "CONFIGURATION REQUIRED", "component_label": component_label(component.model_dump()), "detail": str(exc)})

    wrapper_final = wrapper_sheets[0] if wrapper_sheets and len(set(wrapper_sheets)) == 1 else None
    lines = []
    configuration_required = []
    for module in module_order:
        if only_module and module != only_module:
            continue
        if module == "Wrapper":
            rows = wrapper_rows
            failures = [row for row in rows if row.get("status") == "CONFIGURATION REQUIRED"]
        else:
            processes = processes_for_module(module)
            if not processes:
                continue
            rows = []
            failures = []
            if module == "Punching":
                routed_rows = []
                for component in p.components or []:
                    punching_yes = component.processes.get("Punching") is True
                    die_cutting_yes = component.processes.get("Die Cutting") is True
                    if punching_yes or die_cutting_yes:
                        foam_material = component.material.strip().upper() in {"EVA", "EPE", "PU", "FOAM/EVA/EPE"}
                        process = "Die Cutting" if foam_material or die_cutting_yes else "Punching"
                        routed_rows.append((process, component))
            else:
                routed_rows = [
                    (process, component)
                    for process in processes
                    for component in components_for_process(p.components or [], process)
                ]
            for process, component in routed_rows:
                if only_module and module != only_module:
                    continue
                try:
                    line, failure = _calculate_component_line(module, process, component, p, formulas, wrapper_final)
                except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
                    line, failure = None, str(exc)
                if line:
                    rows.append(line)
                elif failure:
                    failures.append({
                        "status": "CONFIGURATION REQUIRED",
                        "component_label": component_label(component.model_dump()),
                        "process": process,
                        "detail": failure,
                    })

        if failures:
            configuration_required.append(module)
        if not rows:
            continue
        total = sum(row["total_cost"] for row in rows)
        line = {
            "module": module,
            "total_cost": round(total, 4),
            "cost_per_box": round(evaluate_formula("module_cost_per_box", {"total_cost": total, "quantity": quantity}, formulas), 4),
            "unit_cost": round(evaluate_formula("module_cost_per_box", {"total_cost": total, "quantity": quantity}, formulas), 4),
            "unit_label": "box",
            "formula": "Component costs summed using the configured module formula",
            "trace": [{"label": "Applicable component rows", "value": str(len(rows))}],
            "component_lines": rows,
            "configuration_required": failures,
        }
        if module == "Wrapper" and wrapper_final is not None:
            line["wrapper_final_sheets"] = wrapper_final
        lines.append(line)

    total = evaluate_formula(
        "estimate_total_cost",
        {"module_totals": [line["total_cost"] for line in lines]},
        formulas,
    )
    cost_per_box = evaluate_formula("estimate_cost_per_box", {"total_cost": total, "quantity": quantity}, formulas)
    selling_price = evaluate_formula("selling_price_per_box", {"cost_per_box": cost_per_box, "margin_percent": p.margin_percent}, formulas)
    order_value = evaluate_formula("order_value", {"selling_price_per_box": selling_price, "quantity": quantity}, formulas)
    for line in lines:
        line["weightage_percent"] = round(evaluate_formula("module_weightage", {"module_total": line["total_cost"], "total_cost": total}, formulas), 4)
        for component_line in line["component_lines"]:
            component_line["weightage_percent"] = round(evaluate_formula("module_weightage", {"module_total": component_line["total_cost"], "total_cost": total}, formulas), 4)

    return {
        "order_quantity": quantity,
        "total_manufacturing_cost": round(total, 4),
        "cost_per_box": round(cost_per_box, 4),
        "margin_percent": p.margin_percent,
        "selling_price_per_box": round(selling_price, 4),
        "order_value": round(order_value, 4),
        "wrapper_final_sheets": wrapper_final,
        "component_process_matrix": [component.model_dump() for component in p.components or []],
        "lines": lines,
        "configuration_required": sorted(set(configuration_required)),
    }

# ═══════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
def health():
    return {"status": "ok", "service": "pacfully-cost-intelligence"}

@router.post("/layout/extract")
def extract_layout(file: UploadFile, current=Depends(get_formula_user)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF layouts are supported for automatic component extraction.")
    content = file.file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Layout file exceeds the 20 MB limit.")
    try:
        extraction = extract_pdf_layout(content)
    except Exception as exc:
        raise HTTPException(422, f"Unable to read layout PDF: {exc}") from exc
    return extraction

@router.get("/formulas")
def get_formula_config(db: Session = Depends(get_db), current=Depends(_require_config_permission("MASTER_CONFIG_VIEW"))):
    formulas = _active_formulas(db)
    return {
        "version": _configuration_version(formulas),
        "formulas": {
            key: {**definition, "expression": formulas[key]}
            for key, definition in FORMULA_DEFINITIONS.items()
        }
    }

@router.put("/formulas")
def update_formula_config(body: FormulaConfigUpdate, db: Session = Depends(get_db), current=Depends(_require_config_permission("MASTER_CONFIG_EDIT"))):
    config = db.query(FormulaConfiguration).filter(FormulaConfiguration.id == 1).first()
    previous = _active_formulas(db)
    try:
        formulas = validate_formula_set({**previous, **body.formulas})
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise HTTPException(422, str(exc)) from exc

    if config is None:
        config = FormulaConfiguration(id=1, formulas=formulas)
        db.add(config)
    else:
        config.formulas = formulas
    _audit(
        db, "Costing Formulas Updated", "config", "formulas",
        detail=_configuration_audit_detail(current, "formula_definitions", "all", previous, formulas),
        old_val=json.dumps(previous), new_val=json.dumps(formulas),
        user=current.full_name,
    )
    db.commit()
    return {"formulas": formulas, "version": _configuration_version(formulas), "message": "Formulas saved and applied to future calculations"}

@router.get("/settings")
def get_system_settings(db: Session = Depends(get_db), current=Depends(require_admin)):
    record = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    return {"settings": {**SYSTEM_SETTING_DEFAULTS, **(record.settings if record else {})}}

@router.put("/settings")
def update_system_settings(body: SystemSettingsUpdate, db: Session = Depends(get_db), current=Depends(require_admin)):
    record = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    previous = {**SYSTEM_SETTING_DEFAULTS, **(record.settings if record else {})}
    settings = body.model_dump()
    if record is None:
        record = SystemSettings(id=1, settings=settings)
        db.add(record)
    else:
        record.settings = settings
    _audit(
        db, "System Settings Updated", "config", "system-settings",
        detail="Company, tax, and document numbering settings updated",
        old_val=json.dumps(previous), new_val=json.dumps(settings), user=current.full_name,
    )
    db.commit()
    return {"settings": settings, "message": "Settings saved"}

@router.get("/master-config")
def get_master_config(db: Session = Depends(get_db), current=Depends(_require_config_permission("MASTER_CONFIG_VIEW"))):
    config = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
    rates = {**MASTER_RATE_DEFAULTS, **(config.rates if config else {})}
    return {"rates": rates, "version": _configuration_version(rates)}

@router.put("/master-config")
def update_master_config(body: MasterRatesUpdate, db: Session = Depends(get_db), current=Depends(_require_config_permission("MASTER_RATES_EDIT"))):
    unknown = set(body.rates) - set(MASTER_RATE_DEFAULTS)
    if unknown:
        raise HTTPException(422, f"Unknown master rates: {', '.join(sorted(unknown))}")
    if any(not isfinite(value) or value < 0 for value in body.rates.values()):
        raise HTTPException(422, "Master rates must be finite non-negative numbers")

    config = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
    if config is None:
        config = MasterConfiguration(id=1, rates=dict(MASTER_RATE_DEFAULTS))
        db.add(config)
    previous = {**MASTER_RATE_DEFAULTS, **(config.rates or {})}
    rates = {**previous, **body.rates}
    config.rates = rates
    _audit(db, "Master Configuration Updated", "config", "master-rates",
            detail=_configuration_audit_detail(current, "rate_and_process_parameters", "all", previous, rates),
            old_val=json.dumps(previous), new_val=json.dumps(rates), user=current.full_name)
    db.commit()
    return {"rates": rates, "version": _configuration_version(rates), "message": "Master rates saved"}

# ═══════════════════════════════════════════════════════════════
# Costing engine — stateless calculate (no DB)
# ═══════════════════════════════════════════════════════════════

@router.post("/estimates/calculate")
def calculate_estimate(payload: EstimateInput, db: Session = Depends(get_db)):
    try:
        return _run_calculation(payload, _active_formulas(db))
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise HTTPException(422, f"Configured formula could not be evaluated: {exc}") from exc

@router.post("/estimates/calculate/module")
def calculate_estimate_module(body: ModuleCalculationRequest, db: Session = Depends(get_db)):
    module_models = {
        "Kappa": KappaModuleInput,
        "Wrapper": WrapperModuleInput,
        "Printing": PrintingModuleInput,
        "Lamination": LaminationModuleInput,
        "Glue": GlueModuleInput,
        "Punching": PunchingModuleInput,
        "Embellishments": EmbellishmentsModuleInput,
        "Accessories": AccessoriesModuleInput,
    }
    if body.module == "EB" or (body.module == "Conversion" and body.components is None):
        raise HTTPException(409, f"{body.module} is CONFIGURATION REQUIRED")
    formulas = _active_formulas(db)
    matrix_mode = body.components is not None
    if matrix_mode:
        try:
            inputs = EstimateInput.model_validate({**body.inputs, "components": body.components})
            result = _run_component_calculation(inputs, formulas, only_module=body.module)
        except (ValidationError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
            raise HTTPException(422, str(exc)) from exc
        line = next((item for item in result["lines"] if item["module"] == body.module), None)
        if line is None:
            return {"line": None, "stored": False, "configuration_required": result["configuration_required"]}
        wrapper_final = result["wrapper_final_sheets"] if body.module == "Wrapper" else None
    else:
        model = module_models.get(body.module)
        if model is None:
            raise HTTPException(404, "Unknown costing module")
        try:
            inputs = model.model_validate(body.inputs)
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc

    try:
        if not matrix_mode:
            if body.module == "Kappa":
                line = _calculate_kappa(inputs, formulas)
                wrapper_final = None
            elif body.module == "Wrapper":
                line, wrapper_final = _calculate_wrapper(inputs, formulas)
            elif body.module == "Printing":
                line = _calculate_printing(inputs, inputs.wrapper_final_sheets, formulas)
                wrapper_final = None
            elif body.module == "Lamination":
                line = _calculate_lamination(inputs, inputs.wrapper_final_sheets, formulas)
                wrapper_final = None
            elif body.module == "Glue":
                line = _calculate_glue(inputs, formulas)
                wrapper_final = None
            elif body.module == "Punching":
                if inputs.punching_material == "Wrapper" and inputs.wrapper_final_sheets is None:
                    raise HTTPException(422, "Calculate Wrapper first to determine Final Wrapper Sheets.")
                line = _calculate_punching(inputs, inputs.wrapper_final_sheets, formulas)
                wrapper_final = None
            elif body.module == "Embellishments":
                line = _calculate_embellishments(inputs, formulas)
                wrapper_final = None
            else:
                line = _calculate_accessories(inputs, formulas)
                wrapper_final = None
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise HTTPException(422, f"Configured formula could not be evaluated: {exc}") from exc

    line["weightage_percent"] = None
    if body.other_module_totals is not None:
        estimate_total = evaluate_formula(
            "estimate_total_cost",
            {"module_totals": [*body.other_module_totals, line["total_cost"]]},
            formulas,
        )
        line["weightage_percent"] = round(evaluate_formula(
            "module_weightage",
            {"module_total": line["total_cost"], "total_cost": estimate_total},
            formulas,
        ), 4)
    stored = False
    if body.estimate_id is not None:
        estimate = db.query(Estimate).filter(Estimate.id == body.estimate_id).first()
        if not estimate:
            raise HTTPException(404, "Estimate not found")
        if estimate.status != "Draft":
            raise HTTPException(409, "Finalized estimates cannot be changed")

        cost_line = db.query(CostLine).filter(
            CostLine.estimate_id == estimate.id,
            CostLine.module == body.module,
        ).first()
        old_cost = cost_line.total_cost if cost_line else 0
        if cost_line is None:
            cost_line = CostLine(estimate_id=estimate.id, module=body.module)
            db.add(cost_line)
        cost_line.total_cost = line["total_cost"]
        cost_line.cost_per_box = line["cost_per_box"]
        cost_line.trace = line["trace"]
        cost_line.status = "OK"

        input_snapshot = dict(estimate.input_snapshot or {})
        input_snapshot.update(body.inputs)
        if body.components is not None:
            input_snapshot["components"] = [component.model_dump() for component in body.components]
        estimate.input_snapshot = input_snapshot
        db.flush()

        stored_lines = db.query(CostLine).filter(CostLine.estimate_id == estimate.id).all()
        required_modules = {
            "Kappa", "Wrapper", "Printing", "Lamination", "Glue",
            "Punching", "Embellishments", "Accessories",
        }
        stored_by_module = {item.module: item for item in stored_lines}
        if all(
            name in stored_by_module and stored_by_module[name].status == "OK"
            for name in required_modules
        ):
            total = evaluate_formula("estimate_total_cost", {"module_totals": [item.total_cost for item in stored_lines]}, formulas)
            line["weightage_percent"] = round(evaluate_formula("module_weightage", {"module_total": line["total_cost"], "total_cost": total}, formulas), 4)
            cost_line.weightage_pct = line["weightage_percent"]
            estimate.total_manufacturing_cost = round(total, 4)
            estimate.cost_per_box = round(evaluate_formula("estimate_cost_per_box", {"total_cost": total, "quantity": estimate.order_quantity}, formulas), 4)
            estimate.selling_price_per_box = round(evaluate_formula("selling_price_per_box", {"cost_per_box": estimate.cost_per_box, "margin_percent": estimate.margin_percent}, formulas), 4)
            estimate.order_value = round(evaluate_formula("order_value", {"selling_price_per_box": estimate.selling_price_per_box, "quantity": estimate.order_quantity}, formulas), 4)
        else:
            cost_line.weightage_pct = None

        _audit(
            db, "Module Cost Recalculated", "estimate", estimate.estimate_number,
            detail=f"{body.module} cost recalculated",
            estimate_id=estimate.id, user="Admin",
            old_val=str(old_cost), new_val=str(line["total_cost"]),
        )
        db.commit()
        stored = True

    response = {"line": line, "stored": stored}
    if wrapper_final is not None:
        response["wrapper_final_sheets"] = wrapper_final
    return response

# ═══════════════════════════════════════════════════════════════
# Customers
# ═══════════════════════════════════════════════════════════════

@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    rows = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.name).all()
    return [
        {
            "id": c.id, "name": c.name, "contact": c.contact,
            "email": c.email, "phone": c.phone, "city": c.city,
            "state": c.state, "gst_number": c.gst_number,
            "address": c.address, "created_at": c.created_at,
            "estimate_count": c.estimates.count(),
        }
        for c in rows
    ]

@router.post("/customers", status_code=201)
def create_customer(body: CustomerCreate, db: Session = Depends(get_db)):
    c = Customer(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    _audit(db, "Customer Created", "customer", str(c.id),
           detail=f"New customer: {c.name}", user="Admin")
    db.commit()
    return {"id": c.id, "name": c.name, "message": "Customer created"}

@router.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    ests = db.query(Estimate).filter(Estimate.customer_id == customer_id).order_by(Estimate.created_at.desc()).limit(20).all()
    return {
        "id": c.id, "name": c.name, "contact": c.contact, "email": c.email,
        "phone": c.phone, "address": c.address, "city": c.city, "state": c.state,
        "gst_number": c.gst_number, "created_at": c.created_at,
        "estimates": [
            {
                "id": e.id, "estimate_number": e.estimate_number,
                "job_name": e.job_name, "status": e.status,
                "cost_per_box": e.cost_per_box, "order_value": e.order_value,
                "created_at": e.created_at,
            }
            for e in ests
        ],
    }

@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    c.is_active = False
    _audit(db, "Customer Deactivated", "customer", str(customer_id),
           detail=f"Deactivated: {c.name}", user="Admin")
    db.commit()
    return {"message": "Customer deactivated"}

# ═══════════════════════════════════════════════════════════════
# Estimates — CRUD
# ═══════════════════════════════════════════════════════════════

@router.get("/estimates")
def list_estimates(db: Session = Depends(get_db)):
    rows = db.query(Estimate).order_by(Estimate.created_at.desc()).limit(200).all()
    return [
        {
            "id": e.id,
            "estimate_number": e.estimate_number,
            "customer_name":   e.customer_name,
            "job_name":        e.job_name,
            "status":          e.status,
            "order_quantity":  e.order_quantity,
            "cost_per_box":    round(e.cost_per_box, 2),
            "order_value":     round(e.order_value, 2),
            "created_at":      e.created_at.strftime("%d %b %Y") if e.created_at else "",
        }
        for e in rows
    ]

@router.get("/estimates/{estimate_id}")
def get_estimate(estimate_id: int, db: Session = Depends(get_db)):
    e = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not e:
        raise HTTPException(404, "Estimate not found")
    lines = [
        {
            "module":        cl.module, "total_cost":   cl.total_cost,
            "cost_per_box":  cl.cost_per_box, "weightage_percent": cl.weightage_pct,
            "trace":         cl.trace, "status": cl.status,
            "component_lines": (e.input_snapshot or {}).get("component_cost_lines", {}).get(cl.module, []),
        }
        for cl in e.cost_lines
    ]
    quotes = [
        {
            "id": q.id, "quotation_number": q.quotation_number,
            "doc_type": q.doc_type, "grand_total": q.grand_total,
            "status": q.status, "created_at": q.created_at,
        }
        for q in e.quotations
    ]
    return {
        "id": e.id, "estimate_number": e.estimate_number,
        "customer_id": e.customer_id, "customer_name": e.customer_name,
        "job_name": e.job_name, "status": e.status,
        "order_quantity": e.order_quantity,
        "total_manufacturing_cost": e.total_manufacturing_cost,
        "cost_per_box": e.cost_per_box, "margin_percent": e.margin_percent,
        "selling_price_per_box": e.selling_price_per_box,
        "order_value": e.order_value,
        "input_snapshot": e.input_snapshot,
        "cost_lines": lines, "quotations": quotes,
        "created_at": e.created_at, "finalized_at": e.finalized_at,
    }

@router.post("/estimates", status_code=201)
def save_estimate(payload: EstimateInput, db: Session = Depends(get_db)):
    """
    Calculate + persist an estimate as Draft.
    Called by the frontend Save Draft button.
    """
    formulas = _active_formulas(db)
    master_record = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
    master_rates = {**MASTER_RATE_DEFAULTS, **(master_record.rates if master_record else {})}
    result = _run_calculation(payload, formulas)
    num    = _next_estimate_number(db)

    est = Estimate(
        estimate_number          = num,
        customer_id              = payload.customer_id,
        customer_name            = payload.customer_name,
        job_name                 = payload.job_name,
        status                   = "Draft",
        input_snapshot           = {
            **payload.model_dump(),
            "formula_snapshot": {"version": _configuration_version(formulas), "formulas": formulas},
            "master_configuration_snapshot": {"version": _configuration_version(master_rates), "rates": master_rates},
            "component_cost_lines": {
                line["module"]: line.get("component_lines", [])
                for line in result["lines"]
                if line.get("component_lines")
            },
        },
        order_quantity           = result["order_quantity"],
        total_manufacturing_cost = result["total_manufacturing_cost"],
        cost_per_box             = result["cost_per_box"],
        margin_percent           = result["margin_percent"],
        selling_price_per_box    = result["selling_price_per_box"],
        order_value              = result["order_value"],
    )
    db.add(est)
    db.flush()   # get est.id before adding children

    for l in result["lines"]:
        cl = CostLine(
            estimate_id   = est.id,
            module        = l["module"],
            total_cost    = l["total_cost"],
            cost_per_box  = l["cost_per_box"],
            weightage_pct = l.get("weightage_percent", 0),
            trace         = l["trace"],
            status        = "CONFIGURATION REQUIRED" if l["module"] in result["configuration_required"] else "OK",
        )
        db.add(cl)

    _audit(db, "Estimate Created", "estimate", num,
           detail=f"{payload.customer_name} — {payload.job_name} — Qty {payload.quantity}",
           estimate_id=est.id, user="Admin")
    db.commit()
    db.refresh(est)

    return {**result, "estimate_id": est.id, "estimate_number": num, "status": "Draft"}

@router.post("/estimates/{estimate_id}/finalize")
def finalize_estimate(estimate_id: int, db: Session = Depends(get_db)):
    """Mark an estimate as Finalized — immutable snapshot."""
    e = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not e:
        raise HTTPException(404, "Estimate not found")
    if e.status == "Finalized":
        return {"message": "Already finalized", "estimate_number": e.estimate_number}
    e.status        = "Finalized"
    e.finalized_at  = datetime.utcnow()
    _audit(db, "Estimate Finalized", "estimate", e.estimate_number,
           detail=f"Finalized by Admin — cost/box ₹{e.cost_per_box:.2f}",
           estimate_id=e.id, user="Admin",
           old_val="Draft", new_val="Finalized")
    db.commit()
    return {"message": "Estimate finalized", "estimate_number": e.estimate_number}

@router.delete("/estimates/{estimate_id}")
def delete_estimate(estimate_id: int, db: Session = Depends(get_db)):
    e = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not e:
        raise HTTPException(404, "Estimate not found")
    if e.status == "Finalized":
        raise HTTPException(400, "Finalized estimates cannot be deleted")
    _audit(db, "Estimate Deleted", "estimate", e.estimate_number,
           detail=f"Deleted by Admin", estimate_id=e.id, user="Admin")
    db.delete(e)
    db.commit()
    return {"message": "Estimate deleted"}

# ═══════════════════════════════════════════════════════════════
# Quotations
# ═══════════════════════════════════════════════════════════════

@router.get("/quotations")
def list_quotations(db: Session = Depends(get_db)):
    rows = db.query(Quotation).order_by(Quotation.created_at.desc()).limit(200).all()
    return [
        {
            "id":               q.id,
            "quotation_number": q.quotation_number,
            "doc_type":         q.doc_type,
            "estimate_id":      q.estimate_id,
            "customer_name":    q.customer_name,
            "job_name":         q.job_name,
            "order_quantity":   q.order_quantity,
            "unit_price":       round(q.unit_price, 2),
            "subtotal":         round(q.subtotal, 2),
            "gst_amount":       round(q.gst_amount, 2),
            "grand_total":      round(q.grand_total, 2),
            "status":           q.status,
            "created_at":       q.created_at.strftime("%d %b %Y") if q.created_at else "",
            "has_pdf":          bool(q.pdf_path and Path(q.pdf_path).exists()),
        }
        for q in rows
    ]

@router.get("/quotations/next-number")
def get_next_quotation_number(doc_type: str = "Quotation", db: Session = Depends(get_db)):
    return {"quotation_number": _next_quotation_number(db, doc_type)}

@router.get("/quotations/{quotation_id}")
def get_quotation(quotation_id: int, db: Session = Depends(get_db)):
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(404, "Quotation not found")
    return {
        "id": q.id, "quotation_number": q.quotation_number, "doc_type": q.doc_type,
        "estimate_id": q.estimate_id, "customer_name": q.customer_name,
        "customer_address": q.customer_address, "job_name": q.job_name,
        "order_quantity": q.order_quantity, "unit_price": q.unit_price,
        "subtotal": q.subtotal, "gst_percent": q.gst_percent,
        "gst_amount": q.gst_amount, "grand_total": q.grand_total,
        "validity_days": q.validity_days, "notes": q.notes,
        "status": q.status, "created_at": q.created_at,
        "has_pdf": bool(q.pdf_path and Path(q.pdf_path).exists()),
    }

@router.post("/quotations", status_code=201)
def create_quotation(body: QuotationCreate, db: Session = Depends(get_db)):
    """Generate a quotation/proforma from a saved estimate and produce a PDF."""
    if body.estimate_id is None:
        raise HTTPException(422, "Estimate ID is required to save a document")
    est = db.query(Estimate).filter(Estimate.id == body.estimate_id).first()
    if not est:
        raise HTTPException(404, "Estimate not found")

    q_num = (body.quotation_number or "").strip() or _next_quotation_number(db, body.doc_type)
    if db.query(Quotation).filter(Quotation.quotation_number == q_num).first():
        raise HTTPException(409, "Document number already exists")

    customer_name = body.customer_name if body.customer_name is not None else est.customer_name
    job_name = body.job_name if body.job_name is not None else est.job_name
    quantity = body.order_quantity if body.order_quantity is not None else est.order_quantity
    unit_price = body.unit_price if body.unit_price is not None else est.selling_price_per_box
    document_date = datetime.combine(body.document_date, datetime.min.time()) if body.document_date else datetime.utcnow()
    formulas = _active_formulas(db)
    subtotal = round(evaluate_formula("quotation_subtotal", {"unit_price": unit_price, "quantity": quantity}, formulas), 2)
    gst_amt = round(evaluate_formula("quotation_gst_amount", {"subtotal": subtotal, "gst_percent": body.gst_percent}, formulas), 2)
    grand = round(evaluate_formula("quotation_grand_total", {"subtotal": subtotal, "gst_amount": gst_amt}, formulas), 2)

    q = Quotation(
        quotation_number = q_num,
        estimate_id      = est.id,
        doc_type         = body.doc_type,
        customer_name    = customer_name,
        customer_address = body.customer_address,
        job_name         = job_name,
        order_quantity   = quantity,
        unit_price       = unit_price,
        subtotal         = subtotal,
        gst_percent      = body.gst_percent,
        gst_amount       = gst_amt,
        grand_total      = grand,
        validity_days    = body.validity_days,
        notes            = body.notes,
        created_at       = document_date,
        status           = "Draft",
    )
    db.add(q)
    db.flush()

    # Generate PDF
    pdf_data = {
        "quotation_number": q_num, "doc_type": body.doc_type,
        "customer_name": customer_name, "customer_address": body.customer_address,
        "job_name": job_name, "order_quantity": quantity,
        "unit_price": unit_price, "subtotal": subtotal,
        "gst_percent": body.gst_percent, "gst_amount": gst_amt, "grand_total": grand,
        "validity_days": body.validity_days, "notes": body.notes,
        "document_date": body.document_date.isoformat() if body.document_date else None,
    }
    try:
        if "Proforma" in body.doc_type:
            pdf_path = generate_proforma_pdf(pdf_data)
        else:
            pdf_path = generate_quotation_pdf(pdf_data)
        q.pdf_path = pdf_path
    except Exception as exc:
        q.pdf_path = None  # PDF failed but DB record is OK

    # Mark estimate as Quoted
    if est.status == "Draft":
        est.status = "Quoted"

    _audit(db, f"{body.doc_type} Generated", "quotation", q_num,
           detail=f"{customer_name} — Grand Total ₹{grand:,.2f}",
           estimate_id=est.id, user="Admin")
    db.commit()
    db.refresh(q)

    return {
        "id":               q.id,
        "quotation_number": q.quotation_number,
        "grand_total":      q.grand_total,
        "has_pdf":          bool(q.pdf_path and Path(q.pdf_path).exists()),
        "message":          f"{body.doc_type} created successfully",
    }

@router.post("/quotations/preview")
def preview_quotation(body: QuotationCreate, db: Session = Depends(get_db)):
    """Generate a temporary PDF from the current editable document values."""
    q_num = (body.quotation_number or "").strip() or f"PREVIEW-{uuid.uuid4().hex[:8].upper()}"
    quantity = body.order_quantity or 0
    unit_price = body.unit_price or 0
    formulas = _active_formulas(db)
    subtotal = round(evaluate_formula("quotation_subtotal", {"unit_price": unit_price, "quantity": quantity}, formulas), 2)
    gst_amount = round(evaluate_formula("quotation_gst_amount", {"subtotal": subtotal, "gst_percent": body.gst_percent}, formulas), 2)
    data = {
        "quotation_number": q_num,
        "doc_type": body.doc_type,
        "document_date": body.document_date.isoformat() if body.document_date else None,
        "customer_name": body.customer_name or "",
        "customer_address": body.customer_address,
        "job_name": body.job_name or "Packaging",
        "order_quantity": quantity,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "gst_percent": body.gst_percent,
        "gst_amount": gst_amount,
        "grand_total": round(evaluate_formula("quotation_grand_total", {"subtotal": subtotal, "gst_amount": gst_amount}, formulas), 2),
        "validity_days": body.validity_days,
        "notes": body.notes,
    }
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporary_pdf:
        path = Path(temporary_pdf.name)
    try:
        if "Proforma" in body.doc_type:
            generate_proforma_pdf(data, output_path=path)
        else:
            generate_quotation_pdf(data, output_path=path)
        content = path.read_bytes()
    finally:
        path.unlink(missing_ok=True)
    filename = f"{q_num.replace('/', '-')}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

@router.put("/quotations/{quotation_id}")
def update_quotation(quotation_id: int, body: QuotationCreate, db: Session = Depends(get_db)):
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(404, "Quotation not found")

    q_num = (body.quotation_number or q.quotation_number).strip()
    duplicate = db.query(Quotation).filter(
        Quotation.quotation_number == q_num,
        Quotation.id != q.id,
    ).first()
    if duplicate:
        raise HTTPException(409, "Document number already exists")

    customer_name = body.customer_name if body.customer_name is not None else q.customer_name
    customer_address = body.customer_address
    job_name = body.job_name if body.job_name is not None else q.job_name
    quantity = body.order_quantity if body.order_quantity is not None else q.order_quantity
    unit_price = body.unit_price if body.unit_price is not None else q.unit_price
    document_date = body.document_date or (q.created_at.date() if q.created_at else date.today())
    formulas = _active_formulas(db)
    subtotal = round(evaluate_formula("quotation_subtotal", {"unit_price": unit_price, "quantity": quantity}, formulas), 2)
    gst_amount = round(evaluate_formula("quotation_gst_amount", {"subtotal": subtotal, "gst_percent": body.gst_percent}, formulas), 2)
    grand_total = round(evaluate_formula("quotation_grand_total", {"subtotal": subtotal, "gst_amount": gst_amount}, formulas), 2)
    doc_type = body.doc_type or q.doc_type
    pdf_data = {
        "quotation_number": q_num, "doc_type": doc_type,
        "customer_name": customer_name, "customer_address": customer_address,
        "job_name": job_name, "order_quantity": quantity,
        "unit_price": unit_price, "subtotal": subtotal,
        "gst_percent": body.gst_percent, "gst_amount": gst_amount,
        "grand_total": grand_total, "validity_days": body.validity_days,
        "notes": body.notes, "document_date": document_date.isoformat(),
    }
    try:
        if "Proforma" in doc_type:
            pdf_path = generate_proforma_pdf(pdf_data)
        else:
            pdf_path = generate_quotation_pdf(pdf_data)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}") from exc

    old_pdf_path = q.pdf_path
    q.quotation_number = q_num
    q.doc_type = doc_type
    q.customer_name = customer_name
    q.customer_address = customer_address
    q.job_name = job_name
    q.order_quantity = quantity
    q.unit_price = unit_price
    q.subtotal = subtotal
    q.gst_percent = body.gst_percent
    q.gst_amount = gst_amount
    q.grand_total = grand_total
    q.validity_days = body.validity_days
    q.notes = body.notes
    q.created_at = datetime.combine(document_date, datetime.min.time())
    q.pdf_path = pdf_path

    _audit(db, f"{doc_type} Updated", "quotation", q_num,
           detail=f"{customer_name} — Grand Total ₹{grand_total:,.2f}",
           estimate_id=q.estimate_id, user="Admin")
    db.commit()
    db.refresh(q)
    if old_pdf_path and old_pdf_path != pdf_path:
        Path(old_pdf_path).unlink(missing_ok=True)

    return {
        "id": q.id,
        "quotation_number": q.quotation_number,
        "grand_total": q.grand_total,
        "has_pdf": bool(q.pdf_path and Path(q.pdf_path).exists()),
        "message": f"{doc_type} updated successfully",
    }

@router.get("/quotations/{quotation_id}/pdf")
def download_pdf(quotation_id: int, db: Session = Depends(get_db)):
    """Return the PDF file for download / inline preview."""
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(404, "Quotation not found")
    if not q.pdf_path or not Path(q.pdf_path).exists():
        # Regenerate on demand
        pdf_data = {
            "quotation_number": q.quotation_number, "doc_type": q.doc_type,
            "customer_name": q.customer_name, "customer_address": q.customer_address or "",
            "job_name": q.job_name, "order_quantity": q.order_quantity,
            "unit_price": q.unit_price, "subtotal": q.subtotal,
            "gst_percent": q.gst_percent, "gst_amount": q.gst_amount,
            "grand_total": q.grand_total, "validity_days": q.validity_days,
            "notes": q.notes or "", "document_date": q.created_at.date().isoformat() if q.created_at else None,
        }
        try:
            if "Proforma" in q.doc_type:
                path = generate_proforma_pdf(pdf_data)
            else:
                path = generate_quotation_pdf(pdf_data)
            q.pdf_path = path
            db.commit()
        except Exception as exc:
            raise HTTPException(500, f"PDF generation failed: {exc}")

    filename = Path(q.pdf_path).name
    return FileResponse(
        path        = q.pdf_path,
        media_type  = "application/pdf",
        filename    = filename,
        headers     = {"Content-Disposition": f'inline; filename="{filename}"'},
    )

@router.delete("/quotations/{quotation_id}")
def delete_quotation(quotation_id: int, db: Session = Depends(get_db)):
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(404, "Quotation not found")
    db.delete(q)
    db.commit()
    return {"message": "Quotation deleted"}

# ═══════════════════════════════════════════════════════════════
# Audit Log
# ═══════════════════════════════════════════════════════════════

@router.get("/audit-log")
def get_audit_log(db: Session = Depends(get_db), current=Depends(require_admin)):
    rows = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(500).all()
    return [
        {
            "id":          e.id,
            "user":        e.user,
            "action":      e.action,
            "entity_type": e.entity_type,
            "entity_id":   e.entity_id,
            "detail":      e.detail,
            "old_value":   e.old_value,
            "new_value":   e.new_value,
            "timestamp":   e.timestamp.strftime("%d %b %Y, %H:%M") if e.timestamp else "",
        }
        for e in rows
    ]
