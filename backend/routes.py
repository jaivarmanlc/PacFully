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
    "Public": {"MASTER_CONFIG_VIEW", "MASTER_RATES_EDIT", "MASTER_CONFIG_EDIT"},
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
    "default_margin_percent": 20.0,
    "kappa_wastage_percent": 10.0,
    "wrapper_wastage_percent": 10.0,
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
    "foam_insert_rate_per_10mm": 750.0,
    "foam_insert_fixed_rate_per_piece": 0.0,
    "foam_insert_rate_per_kg": 0.0,
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
    kappa_wastage_percent:float = Field(default=10, ge=0)
    kappa_rate_per_kg:    float = Field(default=80, ge=0)
    fbb_rate_per_kg:      float = Field(default=88, ge=0)
    duplex_board_rate_per_kg: float = Field(default=72, ge=0)
    insert_gsm: float | None = Field(default=None, ge=0)
    insert_ups: int | None = Field(default=None, gt=0)
    insert_sheet_length_mm: float | None = Field(default=None, gt=0)
    insert_sheet_width_mm: float | None = Field(default=None, gt=0)
    insert_pricing_method: str | None = None
    insert_thickness_mm: float | None = Field(default=None, gt=0)
    insert_quantity_per_box: float | None = Field(default=None, gt=0)
    insert_weight_g_per_piece: float | None = Field(default=None, gt=0)
    foam_insert_rate_per_10mm: float = Field(default=750, ge=0)
    foam_insert_fixed_rate_per_piece: float = Field(default=0, ge=0)
    foam_insert_rate_per_kg: float = Field(default=0, ge=0)
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
    glue_rate_per_kg:          float = Field(default=90, ge=0)
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
    conversion_base_material: str = "Kappa"
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
    rates: dict[str, float | None]

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
    eff_kappa_gsm = p.kappa_gsm_at_1mm * p.kappa_thickness_mm
    kappa_area_m2 = (p.kappa_sheet_length_mm / 25.4) * (p.kappa_sheet_width_mm / 25.4) * 0.00064516
    kappa_kg_sheet = kappa_area_m2 * eff_kappa_gsm / 1000
    kappa_base = ceil(qty / p.kappa_ups)
    kappa_waste = ceil(kappa_base * p.kappa_wastage_percent / 100)
    kappa_final = kappa_base + kappa_waste
    kappa_kg = kappa_final * kappa_kg_sheet
    rate           = _effective_rate(p.kappa_override_rate, p.kappa_master_rate, p.kappa_rate_per_kg)
    kappa_per_sheet_cost = kappa_kg_sheet * rate
    kappa_total = evaluate_formula("kappa_complete_total_cost", {
        "quantity": qty,
        "ups": p.kappa_ups,
        "wastage_percent": p.kappa_wastage_percent,
        "sheet_length_mm": p.kappa_sheet_length_mm,
        "sheet_width_mm": p.kappa_sheet_width_mm,
        "gsm_at_1mm": p.kappa_gsm_at_1mm,
        "thickness_mm": p.kappa_thickness_mm,
        "rate_per_kg": rate,
    }, formulas)
    line = _costing_line("Kappa", kappa_total, qty, [
        ("Effective GSM",    f"{p.kappa_gsm_at_1mm} × {p.kappa_thickness_mm} = {eff_kappa_gsm}"),
        ("Sheet area",       f"{p.kappa_sheet_length_mm / 25.4:g} × {p.kappa_sheet_width_mm / 25.4:g} in = {kappa_area_m2:.6f} m²"),
        ("KG / sheet",       f"{kappa_area_m2:.6f} × {eff_kappa_gsm} / 1,000 = {kappa_kg_sheet:.6f} kg"),
        ("Base sheets",      f"CEILING({qty} / {p.kappa_ups}) = {kappa_base}"),
        ("Wastage sheets",   f"CEILING({kappa_base} × {p.kappa_wastage_percent}% / 100) = {kappa_waste}"),
        ("Final sheets",     f"{kappa_base} + {kappa_waste} = {kappa_final}"),
        ("Total KG",         f"{kappa_final} × {kappa_kg_sheet:.6f} = {kappa_kg:.4f} kg"),
        ("Effective rate",   f"₹{rate:g} / kg"),
        ("Per Sheet Cost",   f"{kappa_kg_sheet:.6f} × ₹{rate:g} = ₹{kappa_per_sheet_cost:.2f} / sheet"),
        ("Total Cost",       f"{kappa_kg:.4f} × ₹{rate:g} = ₹{kappa_total:.4f}"),
        ("Cost / Box",       f"₹{kappa_total:.4f} / {qty} = ₹{kappa_total / qty:.4f}"),
    ], kappa_per_sheet_cost, "sheet", formulas["kappa_complete_total_cost"], formulas)
    return line

def _calculate_insert(p, formulas=DEFAULT_FORMULAS):
    qty = p.quantity
    sheet_area_m2 = (p.insert_sheet_length_mm / 25.4) * (p.insert_sheet_width_mm / 25.4) * 0.00064516
    kg_per_sheet = sheet_area_m2 * p.insert_gsm / 1000
    base_sheets = ceil(qty / p.insert_ups)
    wastage_sheets = ceil(base_sheets * p.kappa_wastage_percent / 100)
    final_sheets = base_sheets + wastage_sheets
    total_kg = final_sheets * kg_per_sheet
    rate = _effective_rate(p.kappa_override_rate, p.kappa_master_rate, p.duplex_board_rate_per_kg)
    per_sheet_cost = kg_per_sheet * rate
    total_cost = evaluate_formula("insert_complete_total_cost", {
        "pricing_method": 0, "quantity": qty, "ups": p.insert_ups,
        "wastage_percent": p.kappa_wastage_percent,
        "sheet_length_mm": p.insert_sheet_length_mm, "sheet_width_mm": p.insert_sheet_width_mm,
        "gsm": p.insert_gsm, "rate_per_kg": rate,
        "rate_per_10mm": 0, "thickness_mm": 0, "pieces_per_box": 0,
        "rate_per_piece": 0, "weight_g_per_piece": 0,
    }, formulas)
    return _costing_line("Insert", total_cost, qty, [
        ("Sheet size (in)", f"{p.insert_sheet_length_mm / 25.4:g} × {p.insert_sheet_width_mm / 25.4:g}"),
        ("GSM", p.insert_gsm), ("UPS", p.insert_ups),
        ("Base sheets", base_sheets), ("Wastage sheets", wastage_sheets),
        ("Final sheets", final_sheets), ("Total KG", f"{total_kg:.4f}"),
        ("Per Sheet Cost", f"{kg_per_sheet:.4f} × ₹{rate:g} = ₹{per_sheet_cost:.2f} / sheet"),
    ], per_sheet_cost, "sheet", formulas["insert_complete_total_cost"], formulas)

def _calculate_wrapper(p, formulas=DEFAULT_FORMULAS):
    qty = p.quantity
    wrapper_base = ceil(qty / p.wrapper_ups)
    wrapper_waste = ceil(wrapper_base * p.wrapper_wastage_percent / 100)
    wrapper_final = wrapper_base + wrapper_waste + p.wrapper_make_ready_sheets
    wrapper_kg_sh = p.wrapper_sheet_length_mm * p.wrapper_sheet_width_mm * p.wrapper_gsm / 1000000000
    wrapper_kg = wrapper_final * wrapper_kg_sh
    rate           = _effective_rate(p.wrapper_override_rate, p.wrapper_master_rate, p.wrapper_rate_per_kg)
    wrapper_total = evaluate_formula("wrapper_complete_total_cost", {
        "quantity": qty, "ups": p.wrapper_ups, "wastage_percent": p.wrapper_wastage_percent,
        "make_ready_sheets": p.wrapper_make_ready_sheets, "sheet_length_mm": p.wrapper_sheet_length_mm,
        "sheet_width_mm": p.wrapper_sheet_width_mm, "gsm": p.wrapper_gsm, "rate_per_kg": rate,
    }, formulas)
    wrapper_per_sheet = wrapper_kg_sh * rate
    line = _costing_line("Wrapper", wrapper_total, qty, [
        ("Base sheets",      wrapper_base), ("Wastage sheets", wrapper_waste),
        ("Make-ready",       p.wrapper_make_ready_sheets),
        ("Final sheets",     wrapper_final), ("Total KG", f"{wrapper_kg:.4f}"),
        ("Per Sheet Cost",   f"{wrapper_kg_sh:.4f} × ₹{rate:g} = ₹{wrapper_per_sheet:.2f} / sheet"),
    ], wrapper_per_sheet, "sheet", formulas["wrapper_complete_total_cost"], formulas)
    return line, wrapper_final

def _calculate_printing(p, wrapper_final, formulas=DEFAULT_FORMULAS):
    pr             = PRINT_RATES.get(p.print_sheet_size, PRINT_RATES["28x40"])
    master_first   = getattr(p, "print_master_rate", None)
    first_rate     = p.print_override_rate if p.print_override_rate is not None else (master_first if master_first is not None else pr["first"])
    additional_rate = getattr(p, "print_additional_rate", None)
    if additional_rate is None:
        additional_rate = pr["additional"]
    printing_total = evaluate_formula("printing_complete_total_cost", {"first_rate": first_rate, "input_sheets": wrapper_final, "additional_rate": additional_rate}, formulas)
    printing_per_sheet = printing_total / wrapper_final if wrapper_final else 0
    return _costing_line("Printing", printing_total, p.quantity, [
        ("Input",            f"{wrapper_final} final wrapper sheets"),
        ("Sheet tier",       p.print_sheet_size),
        ("First-tier rate",  first_rate), ("Additional rate", additional_rate),
        ("Per Sheet Cost",   f"₹{printing_total:.2f} ÷ {wrapper_final} = ₹{printing_per_sheet:.2f} / sheet"),
    ], printing_per_sheet, "sheet", formulas["printing_complete_total_cost"], formulas)

def _calculate_lamination(p, wrapper_final, formulas=DEFAULT_FORMULAS):
    configured_rate = getattr(p, "lam_master_rate", None)
    master_rate    = configured_rate if configured_rate is not None else LAMINATION_RATES.get(p.lamination_type, 1.10)
    lam_rate       = p.lam_override_rate if p.lam_override_rate is not None else master_rate
    lam_per_sheet = p.lamination_sheet_length_in * p.lamination_sheet_width_in * lam_rate / 100
    lamination_total = evaluate_formula("lamination_complete_total_cost", {
        "sheet_length_in": p.lamination_sheet_length_in, "sheet_width_in": p.lamination_sheet_width_in,
        "rate_per_100_sq_in": lam_rate, "input_sheets": wrapper_final,
    }, formulas)
    return _costing_line("Lamination", lamination_total, p.quantity, [
        ("Rate/100 sq.in",   lam_rate),
        ("Cost/sheet",       f"{p.lamination_sheet_length_in} × {p.lamination_sheet_width_in} × ₹{lam_rate:g} / 100 = ₹{lam_per_sheet:.2f}"),
        ("Input",            f"{wrapper_final} wrapper sheets"),
    ], lam_per_sheet, "sheet", formulas["lamination_complete_total_cost"], formulas)

def _calculate_glue(p, formulas=DEFAULT_FORMULAS):
    component_costs = []
    trace = [("Formula", "Area × 0.00064516 × GSM / 1000 × rate/kg × quantity")]
    for glue_line in p.glue_lines:
        kg_per_box = glue_line.area_sq_in * 0.00064516 * glue_line.gsm / 1000
        component_cost = kg_per_box * glue_line.rate_per_kg * p.quantity
        component_costs.append(component_cost)
        trace.extend([
            (f"{glue_line.name} · Area (sq.in)", glue_line.area_sq_in),
            (f"{glue_line.name} · GSM", glue_line.gsm),
            (f"{glue_line.name} · Rate / kg", f"₹{glue_line.rate_per_kg:g}"),
            (f"{glue_line.name} · KG / box", f"{kg_per_box:.6f}"),
            (f"{glue_line.name} · Total cost", f"₹{component_cost:.4f}"),
        ])
    glue_total = evaluate_formula("glue_total_cost", {"component_costs": component_costs}, formulas)
    trace.extend([
        ("Components", len(p.glue_lines)),
        ("Cost / Box", f"₹{glue_total / p.quantity:.2f}"),
    ])
    return _costing_line("Glue", glue_total, p.quantity, trace, glue_total / p.quantity, "box", formulas["glue_total_cost"], formulas)

def _calculate_punching(p, wrapper_final, formulas=DEFAULT_FORMULAS):
    punch          = dict(PUNCHING_RATES.get(p.punching_material, PUNCHING_RATES["Kappa"]))
    configured_speed = getattr(p, "punching_speed", None)
    configured_setup = getattr(p, "punching_setup_hours", None)
    if configured_speed is not None:
        punch["speed"] = configured_speed
    if configured_setup is not None:
        punch["setup_hours"] = configured_setup
    is_wrapper = p.punching_material == "Wrapper"
    punch_quantity = int((wrapper_final or 0) if is_wrapper else p.quantity)
    prod_hrs = punch_quantity / punch["speed"]
    punching_total = evaluate_formula("punching_complete_total_cost", {
        "wrapper_final_sheets": wrapper_final or 0, "is_wrapper": 1 if is_wrapper else 0,
        "quantity": p.quantity, "speed": punch["speed"], "setup_hours": punch["setup_hours"],
        "machine_rate": p.punching_machine_rate_per_hour,
    }, formulas)
    punch_unit = "sheet" if p.punching_material == "Wrapper" else "box"
    punch_unit_count = punch_quantity if punch_unit == "sheet" else p.quantity
    return _costing_line("Punching", punching_total, p.quantity, [
        ("Speed",            punch["speed"]),
        ("Production hrs",   f"{prod_hrs:.4f}"),
        ("Setup hrs",        punch["setup_hours"]),
        ("Machine rate",     f"₹{p.punching_machine_rate_per_hour:.2f} / hr"),
        ("Cost / Box",       f"₹{punching_total / p.quantity:.2f}"),
    ], punching_total / punch_unit_count if punch_unit_count else 0, punch_unit, formulas["punching_complete_total_cost"], formulas)

def _calculate_embellishments(p, formulas=DEFAULT_FORMULAS):
    emb_raw = p.embellishment_area_sq_in * p.embellishment_rate_per_sq_in + p.embellishment_setup
    emb_total = evaluate_formula("embellishments_complete_total_cost", {
        "pricing_method": 0, "area_sq_in": p.embellishment_area_sq_in,
        "rate_per_sq_in": p.embellishment_rate_per_sq_in, "setup_cost": p.embellishment_setup,
        "minimum_cost": p.embellishment_minimum, "rate_per_100_sq_in": 0,
        "quantity": p.quantity, "sheet_length_in": 0, "sheet_width_in": 0,
        "input_sheets": 0, "rate_per_box": 0,
    }, formulas)
    return _costing_line("Embellishments", emb_total, p.quantity, [
        ("Raw cost",         f"₹{emb_raw:.2f}"),
        ("Tool Cost",        f"₹{p.embellishment_minimum:.2f}"),
        ("Applied cost",     f"₹{emb_total:.2f}"),
        ("Cost / Box",       f"₹{emb_total / p.quantity:.2f}"),
    ], emb_total / p.quantity, "box", formulas["embellishments_complete_total_cost"], formulas)

def _calculate_accessories(p, formulas=DEFAULT_FORMULAS):
    accessory_costs = [item.quantity_per_box * item.unit_cost * p.quantity for item in p.accessories]
    acc_total = evaluate_formula("accessories_total_cost", {"accessory_costs": accessory_costs}, formulas)
    return _costing_line("Accessories", acc_total, p.quantity, [
        ("Formula",          "Qty/box × unit cost × order qty"),
        ("Items",            len(p.accessories)),
        ("Cost / Box",       f"₹{acc_total / p.quantity:.2f}"),
    ], acc_total / p.quantity, "box", formulas["accessories_total_cost"], formulas)

def _calculate_conversion_for_material(p, material, formulas=DEFAULT_FORMULAS):
    material = material.strip().upper()
    conversion_type = p.conversion_type.strip().lower()
    is_kappa = material in {"KAPPA", "KAPPA BOARD", "BASE MATERIAL"}
    formula_inputs = {
        "pricing_method": -1, "quantity": p.quantity,
        "contract_rate_per_box": 0, "automatic_boxes_per_hour": 1,
        "automatic_machine_rate": 0, "automatic_setup_hours": 0,
        "automatic_setup_rate": 0, "semi_workers": 0, "monthly_salary": 0,
        "working_days": 1, "hours_per_day": 1, "semi_boxes_per_hour": 1,
        "side_pasting_rate_per_box": 0,
    }

    if conversion_type == "contract":
        rate = p.conversion_contract_rate_per_box
        if rate is None:
            return None, "Contract conversion rate per box is not configured."
        formula_inputs.update(pricing_method=0, contract_rate_per_box=rate)
        trace = [("Method", "Contract"), ("Rate / box", rate), ("Order quantity", p.quantity)]
    elif conversion_type == "automatic" and is_kappa:
        boxes_per_hour = p.conversion_automatic_boxes_per_hour
        machine_rate = p.conversion_automatic_machine_rate
        setup_rate = p.conversion_automatic_setup_rate
        setup_hours = p.conversion_automatic_setup_hours
        if any(value is None for value in (boxes_per_hour, machine_rate, setup_rate, setup_hours)):
            return None, "Automatic Kappa conversion parameters are not configured."
        machine_hours = p.quantity / boxes_per_hour * 2
        formula_inputs.update(
            pricing_method=1, automatic_boxes_per_hour=boxes_per_hour,
            automatic_machine_rate=machine_rate, automatic_setup_hours=setup_hours,
            automatic_setup_rate=setup_rate,
        )
        trace = [("Method", "Automatic"), ("Machine hours", machine_hours), ("Machine rate / hr", machine_rate), ("Setup hours", setup_hours), ("Setup rate / hr", setup_rate)]
    elif conversion_type == "semi automatic" and is_kappa:
        boxes_per_hour = p.conversion_semi_boxes_per_hour
        workers = p.conversion_semi_workers
        salary = p.conversion_monthly_salary
        workdays = p.conversion_working_days
        hours_per_day = p.conversion_hours_per_day
        if any(value is None for value in (boxes_per_hour, workers, salary, workdays, hours_per_day)):
            return None, "Semi-automatic Kappa conversion parameters are not configured."
        machine_hours = p.quantity / boxes_per_hour * 2
        formula_inputs.update(
            pricing_method=2, semi_boxes_per_hour=boxes_per_hour,
            semi_workers=workers, monthly_salary=salary,
            working_days=workdays, hours_per_day=hours_per_day,
        )
        trace = [("Method", "Semi Automatic"), ("Machine hours", machine_hours), ("Workers", workers), ("Monthly salary", salary), ("Working days", workdays), ("Hours per day", hours_per_day)]
    elif material in {"FBB", "DUPLEX", "DUPLEX BOARD", "KRAFT"} and conversion_type == "semi automatic":
        rate = p.conversion_side_pasting_rate_per_box
        if rate is None:
            return None, "Side-pasting rate per box is not configured."
        formula_inputs.update(pricing_method=3, side_pasting_rate_per_box=rate)
        trace = [("Method", "Side Pasting"), ("Rate / box", rate), ("Order quantity", p.quantity)]
    else:
        return None, f"{p.conversion_type.title()} conversion is not configured for {material}."

    total = evaluate_formula("conversion_complete_total_cost", formula_inputs, formulas)
    formula = formulas["conversion_complete_total_cost"]
    return _costing_line("Conversion", total, p.quantity, trace, total / p.quantity, "box", formula, formulas), None

def _calculate_eb(p):
    return _costing_line("EB", 0, p.quantity, [
        ("Status",           "CONFIGURATION REQUIRED"),
        ("Formula",          "Not defined"),
    ], 0, "box", "Not defined", DEFAULT_FORMULAS)

def _run_calculation(p: EstimateInput, formulas=DEFAULT_FORMULAS, master_rates=None) -> dict:
    """Calculate the complete estimate in dependency order."""
    if p.components is not None:
        return _run_component_calculation(p, formulas, master_rates=master_rates)

    qty = p.quantity

    kappa_line = _calculate_kappa(p, formulas)
    wrapper_line, wrapper_final = _calculate_wrapper(p, formulas)
    printing_line = _calculate_printing(p, wrapper_final, formulas)
    lamination_line = _calculate_lamination(p, wrapper_final, formulas)
    glue_line = _calculate_glue(p, formulas)
    punching_line = _calculate_punching(p, wrapper_final, formulas)
    embellishments_line = _calculate_embellishments(p, formulas)
    accessories_line = _calculate_accessories(p, formulas)
    conversion_line, conversion_failure = _calculate_conversion_for_material(p, p.conversion_base_material, formulas)
    if conversion_line is None:
        conversion_line = _costing_line("Conversion", 0, p.quantity, [
            ("Status", "CONFIGURATION REQUIRED"),
            ("Detail", conversion_failure),
        ], 0, "box", "Not configured", formulas)
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
        "configuration_required":   ["EB", *(["Conversion"] if conversion_failure else [])],
    }

def _component_master_values(p, component, process, module, rates):
    inputs = {
        **component.process_inputs.get(module, {}),
        **component.process_inputs.get(process, {}),
    }
    values = {}

    def set_rate(input_key, rate_key):
        if rate_key in rates:
            values[input_key] = rates[rate_key]

    material = component.material.strip().upper()
    if module in {"Kappa", "Insert"}:
        if module == "Kappa" or material not in {"EVA", "EPE", "PU"}:
            set_rate("kappa_wastage_percent", "kappa_wastage_percent")
            material_rate_key = (
                "fbb_rate_per_kg" if "FBB" in material
                else "duplex_board_rate_per_kg" if "DUPLEX" in material
                else "kappa_rate_per_kg"
            )
            set_rate("kappa_rate_per_kg", material_rate_key)
            set_rate("kappa_master_rate", material_rate_key)
        if module == "Insert" and material in {"EVA", "EPE", "PU"}:
            for key in ("foam_insert_rate_per_10mm", "foam_insert_fixed_rate_per_piece", "foam_insert_rate_per_kg"):
                set_rate(key, key)
    elif module == "Wrapper":
        for key in ("wrapper_wastage_percent", "wrapper_make_ready_sheets"):
            set_rate(key, key)
        set_rate("wrapper_rate_per_kg", "wrapper_rate_per_kg")
        set_rate("wrapper_master_rate", "wrapper_rate_per_kg")
    elif module == "Printing":
        sheet_size = str(inputs.get("print_sheet_size", p.print_sheet_size)).strip().lower().replace("×", "x").replace(" ", "")
        first_key = f"print_{sheet_size}_first"
        additional_key = f"print_{sheet_size}_additional"
        set_rate("print_master_rate", first_key)
        set_rate("print_additional_rate", additional_key)
    elif module == "Lamination":
        lamination_type = str(inputs.get("lamination_type", p.lamination_type)).strip().lower()
        finish = str(inputs.get("lamination_finish", p.lamination_finish)).strip().lower().replace(" ", "_")
        method_finish_key = f"lamination_rate_{lamination_type}_{finish}"
        method_finish_rate = rates.get(method_finish_key)
        rate_key = f"lamination_{lamination_type}"
        effective_rate = method_finish_rate if method_finish_rate is not None and method_finish_rate > 0 else rates.get(rate_key)
        if effective_rate is not None:
            values["lam_master_rate"] = effective_rate
        values["lamination_method_finish_rates"] = {
            f"{method}_{configured_finish}": rates.get(
                f"lamination_rate_{method}_{configured_finish}",
                p.lamination_method_finish_rates.get(f"{method}_{configured_finish}", 0),
            )
            for method in ("thermal", "cold", "dry")
            for configured_finish in ("matte", "gloss", "soft_touch", "other")
        }
    elif module == "Glue":
        set_rate("glue_rate_per_kg", "glue_rate_per_kg")
    elif module == "Punching":
        speed_key = (
            "punching_speed_wrapper" if "ART PAPER" in material or "WRAPPER" in material
            else "punching_speed_fbb" if "FBB" in material
            else "punching_speed_duplex" if "DUPLEX" in material
            else "punching_speed_foam" if material in {"EVA", "EPE", "PU", "FOAM/EVA/EPE"}
            else "punching_speed_kappa"
        )
        set_rate("punching_machine_rate_per_hour", "punching_machine_rate_per_hour")
        set_rate("punching_speed", speed_key)
        set_rate("punching_setup_hours", "punching_setup_hours")
    elif module == "Embellishments":
        for key in (
            "embellishment_rate_per_sq_in", "embellishment_setup", "embellishment_minimum",
            "foiling_rate_per_100_sq_in", "spot_uv_rate_per_100_sq_in",
            "embossing_cost_per_box", "debossing_cost_per_box",
        ):
            set_rate(key, key)
    elif module == "Conversion":
        for key in (
            "conversion_semi_boxes_per_hour", "conversion_semi_workers", "conversion_monthly_salary",
            "conversion_working_days", "conversion_hours_per_day", "conversion_side_pasting_rate_per_box",
            "conversion_automatic_boxes_per_hour", "conversion_automatic_machine_rate",
            "conversion_automatic_setup_rate", "conversion_automatic_setup_hours",
            "conversion_contract_rate_per_box",
        ):
            set_rate(key, key)
    elif module == "One Time Cost":
        for key in (
            "punching_die_15x20", "punching_die_20x28", "punching_die_25x36",
            "punching_die_28x40", "emboss_deboss_die_rate_per_sq_cm",
            "foil_stamp_die_rate_per_sq_cm",
        ):
            set_rate(key, key)
    return values

def _component_estimate_input(p, component, process, module, master_rates=None):
    values = p.model_dump(exclude={"components"})
    if master_rates is not None:
        values.update(_component_master_values(p, component, process, module, master_rates))
    values.update(component.process_inputs.get(module, {}))
    values.update(component.process_inputs.get(process, {}))
    values["quantity"] = p.quantity
    row_values = {
        **component.process_inputs.get(module, {}),
        **component.process_inputs.get(process, {}),
    }
    if module == "Lamination":
        material = component.material.strip().upper()
        sheet_process = (
            "Wrapper" if "ART PAPER" in material or "WRAPPER" in material
            else "Insert" if "DUPLEX" in material or "FBB" in material
            else "Kappa" if "KAPPA" in material
            else None
        )
        sheet_inputs = component.process_inputs.get(sheet_process, {}) if sheet_process else {}
        for dimension, lamination_key, sheet_key in (
            ("length", "lamination_sheet_length_in", f"{sheet_process.lower()}_sheet_length_mm" if sheet_process else ""),
            ("width", "lamination_sheet_width_in", f"{sheet_process.lower()}_sheet_width_mm" if sheet_process else ""),
        ):
            if lamination_key not in row_values and sheet_inputs.get(sheet_key) is not None:
                values[lamination_key] = sheet_inputs[sheet_key] / 25.4
    if module == "Glue" and any(key in row_values for key in ("glue_area_sq_in", "glue_gsm", "glue_rate_per_kg")):
        values["glue_lines"] = [{
            "name": f"{component.component_name} glue",
            "area_sq_in": row_values.get("glue_area_sq_in", 0),
            "gsm": row_values.get("glue_gsm", 20),
            "rate_per_kg": row_values.get("glue_rate_per_kg", values["glue_rate_per_kg"]),
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

def _has_component_wastage(component, module, process):
    module_inputs = component.process_inputs.get(module, {})
    process_inputs = component.process_inputs.get(process, {})
    return (
        module_inputs.get("kappa_wastage_percent") is not None
        or process_inputs.get("kappa_wastage_percent") is not None
    )

def _has_explicit_component_value(p, component, module, process, key):
    value = getattr(p, key, None)
    if key in p.model_fields_set and value is not None and (not isinstance(value, str) or value.strip()):
        return True
    return any(
        inputs.get(key) is not None
        and (not isinstance(inputs[key], str) or inputs[key].strip())
        for inputs in (component.process_inputs.get(module, {}), component.process_inputs.get(process, {}))
    )

def _calculate_component_line(module, process, component, p, formulas, wrapper_final, master_rates=None):
    master_rates = master_rates or {}
    is_foam_insert = module == "Insert" and component.material.strip().upper() in {"EVA", "EPE", "PU"}
    if module in {"Kappa", "Insert"} and not is_foam_insert and "kappa_wastage_percent" not in p.model_fields_set:
        if not _has_component_wastage(component, module, process) and "kappa_wastage_percent" not in master_rates:
            return None, "Set Base Material wastage in Master Configuration or for this component."
    if module == "Wrapper" and "wrapper_wastage_percent" not in p.model_fields_set:
        module_inputs = component.process_inputs.get(module, {})
        process_inputs = component.process_inputs.get(process, {})
        if (
            module_inputs.get("wrapper_wastage_percent") is None
            and process_inputs.get("wrapper_wastage_percent") is None
            and "wrapper_wastage_percent" not in master_rates
        ):
            return None, "Set Wrapper wastage in Master Configuration or for this component."
    row_input = _component_estimate_input(p, component, process, module, master_rates)
    if module in {"Kappa", "Insert"}:
        if module == "Insert":
            material = component.material.strip().upper()
            if material in {"EVA", "EPE", "PU"}:
                method = (row_input.insert_pricing_method or "").strip().lower()
                pieces_per_box = row_input.insert_quantity_per_box
                if method == "thickness-based":
                    thickness = row_input.insert_thickness_mm
                    if thickness is None or pieces_per_box is None:
                        return None, "Select thickness-based insert pricing and enter thickness and pieces per box."
                    pricing_method = 1
                    trace = [("Pricing method", "Thickness-based"), ("Thickness (mm)", thickness), ("Cost / 10 mm", row_input.foam_insert_rate_per_10mm), ("Pieces / box", pieces_per_box)]
                elif method == "fixed per insert":
                    if pieces_per_box is None or row_input.foam_insert_fixed_rate_per_piece <= 0:
                        return None, "Configure the fixed cost per insert and enter pieces per box."
                    pricing_method = 2
                    trace = [("Pricing method", "Fixed per insert"), ("Cost / insert", row_input.foam_insert_fixed_rate_per_piece), ("Pieces / box", pieces_per_box)]
                elif method == "per kg":
                    weight = row_input.insert_weight_g_per_piece
                    if pieces_per_box is None or weight is None or row_input.foam_insert_rate_per_kg <= 0:
                        return None, "Configure the foam insert rate per kg and enter insert weight and pieces per box."
                    pricing_method = 3
                    trace = [("Pricing method", "Per kg"), ("Weight / insert (g)", weight), ("Rate / kg", row_input.foam_insert_rate_per_kg), ("Pieces / box", pieces_per_box)]
                else:
                    return None, "Choose a valid EVA/EPE/PU insert pricing method."
                total = evaluate_formula("insert_complete_total_cost", {
                    "pricing_method": pricing_method, "quantity": row_input.quantity,
                    "ups": 1, "wastage_percent": 0, "sheet_length_mm": 0,
                    "sheet_width_mm": 0, "gsm": 0, "rate_per_kg": row_input.foam_insert_rate_per_kg,
                    "rate_per_10mm": row_input.foam_insert_rate_per_10mm,
                    "thickness_mm": row_input.insert_thickness_mm or 0,
                    "pieces_per_box": pieces_per_box,
                    "rate_per_piece": row_input.foam_insert_fixed_rate_per_piece,
                    "weight_g_per_piece": row_input.insert_weight_g_per_piece or 0,
                }, formulas)
                formula = formulas["insert_complete_total_cost"]
                line = _costing_line("Insert", total, row_input.quantity, trace, total / row_input.quantity, "box", formula, formulas)
                line.update({
                    "component_name": component.component_name,
                    "material": component.material,
                    "component_label": component_label(component.model_dump()),
                    "process": process,
                })
                return line, None
            if any(getattr(row_input, key) is None for key in ("insert_gsm", "insert_ups", "insert_sheet_length_mm", "insert_sheet_width_mm")):
                return None, "Insert GSM, UPS, and sheet dimensions are required before costing."
            material_rates = {
                "KAPPA": row_input.kappa_master_rate,
                "KAPPA BOARD": row_input.kappa_master_rate,
                "FBB": row_input.fbb_rate_per_kg,
                "DUPLEX": row_input.duplex_board_rate_per_kg,
                "DUPLEX BOARD": row_input.duplex_board_rate_per_kg,
            }
            if material not in material_rates:
                return None, f"Insert costing for {component.material} is not configured."
            row_input.kappa_master_rate = material_rates[material]
            row_input.kappa_rate_per_kg = row_input.kappa_override_rate if row_input.kappa_override_rate is not None else material_rates[material]
            line = _calculate_insert(row_input, formulas)
        else:
            material = component.material.strip().upper()
            if "FBB" in material:
                material_rate = row_input.fbb_rate_per_kg
            elif "DUPLEX" in material:
                material_rate = row_input.duplex_board_rate_per_kg
            else:
                material_rate = row_input.kappa_rate_per_kg
            row_input.kappa_master_rate = material_rate
            line = _calculate_kappa(row_input, formulas)
    elif module == "Wrapper":
        line, _ = _calculate_wrapper(row_input, formulas)
    elif module == "Printing":
        if wrapper_final is None:
            return None, "Wrapper final sheets are unavailable. Calculate an applicable Wrapper row first."
        if component.source == "pdf_text" and not _has_explicit_component_value(p, component, module, process, "print_method"):
            return None, "Confirm the printing method before costing."
        if not row_input.print_method.strip():
            return None, "Confirm the printing method before costing."
        if component.source == "pdf_text" and not _has_explicit_component_value(p, component, module, process, "print_colour_configuration"):
            return None, "Confirm the print colour configuration before costing."
        if row_input.print_method.strip().lower() != "offset":
            return None, "Digital printing rates are not configured."
        line = _calculate_printing(row_input, wrapper_final, formulas)
    elif module == "Lamination":
        if wrapper_final is None:
            return None, "Wrapper final sheets are unavailable. Calculate an applicable Wrapper row first."
        if component.source == "pdf_text" and not _has_explicit_component_value(p, component, module, process, "lamination_type"):
            return None, "Confirm the lamination method before costing."
        if not row_input.lamination_type.strip():
            return None, "Confirm the lamination method before costing."
        finish_field = component.extracted_fields.get("lamination_finish", {})
        if (
            process == "Lamination"
            and component.source == "pdf_text"
            and not finish_field.get("normalized_value")
            and not _has_explicit_component_value(p, component, module, process, "lamination_finish")
        ):
            return None, "Confirm the extracted lamination finish before costing."
        finish_key = row_input.lamination_finish.strip().lower().replace(" ", "_")
        rate_key = f"{row_input.lamination_type.strip().lower()}_{finish_key}"
        finish_rate = row_input.lamination_method_finish_rates.get(rate_key)
        if finish_rate is None or finish_rate <= 0:
            finish_rate = row_input.lam_master_rate
        if finish_rate is None:
            finish_rate = LAMINATION_RATES.get(row_input.lamination_type.strip().lower(), LAMINATION_RATES["thermal"])
        row_input.lam_master_rate = finish_rate
        line = _calculate_lamination(row_input, wrapper_final, formulas)
    elif module == "Glue":
        if not _has_explicit_component_value(p, component, module, process, "glue_area_sq_in"):
            return None, "Enter the glue area (sq.in) for this component."
        if not _has_explicit_component_value(p, component, module, process, "glue_gsm"):
            return None, "Enter the glue GSM for this component."
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
            raw_cost_per_box = row_input.embellishment_area_sq_in * rate / 100
            total = evaluate_formula("embellishments_complete_total_cost", {
                "pricing_method": 1, "area_sq_in": row_input.embellishment_area_sq_in,
                "rate_per_sq_in": 0, "setup_cost": 0,
                "minimum_cost": row_input.embellishment_minimum, "rate_per_100_sq_in": rate,
                "quantity": row_input.quantity, "sheet_length_in": 0, "sheet_width_in": 0,
                "input_sheets": 0, "rate_per_box": 0,
            }, formulas)
            line = _costing_line("Embellishments", total, row_input.quantity, [
                ("Process", process), ("Component area (sq.in)", row_input.embellishment_area_sq_in),
                ("Rate / 100 sq.in", rate), ("Raw cost / box", raw_cost_per_box),
                ("Minimum cost / box", row_input.embellishment_minimum),
            ], total / row_input.quantity, "box", formulas["embellishments_complete_total_cost"], formulas)
        elif process in {"Spot UV", "Drip-Off"}:
            if wrapper_final is None:
                return None, "Wrapper final sheets are unavailable for surface finishing."
            rate_key = "spot_uv_rate_per_100_sq_in" if process == "Spot UV" else "drip_off_rate_per_100_sq_in"
            rate = getattr(row_input, rate_key)
            if rate is None:
                return None, f"{process} rate per 100 sq.in is CONFIGURATION REQUIRED."
            cost_per_sheet = row_input.lamination_sheet_length_in * row_input.lamination_sheet_width_in * rate / 100
            total = evaluate_formula("embellishments_complete_total_cost", {
                "pricing_method": 2, "area_sq_in": 0, "rate_per_sq_in": 0, "setup_cost": 0,
                "minimum_cost": 0, "rate_per_100_sq_in": rate, "quantity": row_input.quantity,
                "sheet_length_in": row_input.lamination_sheet_length_in,
                "sheet_width_in": row_input.lamination_sheet_width_in,
                "input_sheets": wrapper_final, "rate_per_box": 0,
            }, formulas)
            line = _costing_line("Embellishments", total, row_input.quantity, [
                ("Process", process), ("Rate / 100 sq.in", rate),
                ("Cost / sheet", cost_per_sheet), ("Wrapper final sheets", wrapper_final),
            ], cost_per_sheet, "sheet", formulas["embellishments_complete_total_cost"], formulas)
        elif process in {"Embossing", "Debossing"}:
            rate_key = "embossing_cost_per_box" if process == "Embossing" else "debossing_cost_per_box"
            rate = getattr(row_input, rate_key)
            if rate is None:
                return None, f"{process} direct cost per box is CONFIGURATION REQUIRED."
            total = evaluate_formula("embellishments_complete_total_cost", {
                "pricing_method": 3, "area_sq_in": 0, "rate_per_sq_in": 0, "setup_cost": 0,
                "minimum_cost": 0, "rate_per_100_sq_in": 0, "quantity": row_input.quantity,
                "sheet_length_in": 0, "sheet_width_in": 0, "input_sheets": 0, "rate_per_box": rate,
            }, formulas)
            line = _costing_line("Embellishments", total, row_input.quantity, [("Process", process), ("Direct cost / box", rate)], total / row_input.quantity, "box", formulas["embellishments_complete_total_cost"], formulas)
        else:
            return None, f"{process} is CONFIGURATION REQUIRED."
    elif module == "Accessories":
        line = _calculate_accessories(row_input, formulas)
    elif module == "Conversion":
        line, failure = _calculate_conversion_for_material(row_input, component.material, formulas)
        if line is None:
            return None, failure
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
            total = evaluate_formula("tooling_complete_total_cost", {
                "pricing_method": 0, "fixed_die_rate": rate, "area_sq_cm": 0, "rate_per_sq_cm": 0,
            }, formulas)
            formula = formulas["tooling_complete_total_cost"]
            trace = [("Tooling type", tooling_type), ("Entered sheet size", tooling.get("sheet_size")), ("Nearest configured size", size_key), ("Die rate", rate)]
        elif tooling_type in {"Emboss/Deboss Die", "Foil Stamp Die"}:
            area = tooling.get("area_sq_cm")
            rate_key = "foil_stamp_die_rate_per_sq_cm" if tooling_type == "Foil Stamp Die" else "emboss_deboss_die_rate_per_sq_cm"
            rate = getattr(row_input, rate_key)
            if area is None or rate is None:
                return None, f"Area and configured rate are required for {tooling_type}."
            total = evaluate_formula("tooling_complete_total_cost", {
                "pricing_method": 1, "fixed_die_rate": 0,
                "area_sq_cm": float(area), "rate_per_sq_cm": rate,
            }, formulas)
            formula = formulas["tooling_complete_total_cost"]
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

def _run_component_calculation(p, formulas=DEFAULT_FORMULAS, only_module=None, master_rates=None):
    """Calculate routed rows from the submitted matrix without creating NO rows."""
    master_rates = master_rates or {}
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
        if (
            "wrapper_wastage_percent" not in p.model_fields_set
            and component.process_inputs.get("Wrapper", {}).get("wrapper_wastage_percent") is None
            and "wrapper_wastage_percent" not in master_rates
        ):
            wrapper_rows.append({
                "status": "CONFIGURATION REQUIRED",
                "component_label": component_label(component.model_dump()),
                "detail": "Set Wrapper wastage in Master Configuration or for this component.",
            })
            continue
        try:
            row_input = _component_estimate_input(p, component, "Wrapper", "Wrapper", master_rates)
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
    configuration_details = []
    for module in module_order:
        if only_module and module != only_module:
            continue
        if module == "Wrapper":
            rows = [row for row in wrapper_rows if row.get("status") != "CONFIGURATION REQUIRED"]
            failures = [row for row in wrapper_rows if row.get("status") == "CONFIGURATION REQUIRED"]
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
                    line, failure = _calculate_component_line(
                        module, process, component, p, formulas, wrapper_final, master_rates
                    )
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
            configuration_details.extend({"module": module, **failure} for failure in failures)
        if not rows:
            continue
        total = sum(row["total_cost"] for row in rows)
        trace = [{"label": "Applicable component rows", "value": str(len(rows))}]
        for component_row in rows:
            component = component_row.get("component_label", component_row.get("component_name", module))
            trace.append({"label": f"{component} total cost", "value": str(component_row["total_cost"])})
            trace.append({"label": f"{component} cost per box", "value": str(component_row["cost_per_box"])})
            trace.extend({
                "label": f"{component} · {detail['label']}",
                "value": str(detail["value"]),
            } for detail in component_row.get("trace", []))
            trace.append({"label": f"{component} formula", "value": component_row.get("formula", "Not available")})
        cost_per_box = evaluate_formula("module_cost_per_box", {"total_cost": total, "quantity": quantity}, formulas)
        trace.append({"label": "Module cost per box", "value": str(round(cost_per_box, 4))})
        line = {
            "module": module,
            "total_cost": round(total, 4),
            "cost_per_box": round(cost_per_box, 4),
            "unit_cost": round(cost_per_box, 4),
            "unit_label": "box",
            "formula": f"Module total = sum(component costs); Cost per box = {formulas['module_cost_per_box']}",
            "trace": trace,
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
        "configuration_details": configuration_details,
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

def _effective_master_rates(config):
    rates = {**MASTER_RATE_DEFAULTS, **(config.rates if config else {})}
    for key in ("kappa_wastage_percent", "wrapper_wastage_percent"):
        if rates[key] is None:
            rates[key] = MASTER_RATE_DEFAULTS[key]
    return rates

@router.get("/master-config")
def get_master_config(db: Session = Depends(get_db), current=Depends(_require_config_permission("MASTER_CONFIG_VIEW"))):
    config = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
    rates = _effective_master_rates(config)
    return {"rates": rates, "version": _configuration_version(rates)}

@router.put("/master-config")
def update_master_config(body: MasterRatesUpdate, db: Session = Depends(get_db), current=Depends(_require_config_permission("MASTER_RATES_EDIT"))):
    unknown = set(body.rates) - set(MASTER_RATE_DEFAULTS)
    if unknown:
        raise HTTPException(422, f"Unknown master rates: {', '.join(sorted(unknown))}")
    optional_defaults = {"kappa_wastage_percent", "wrapper_wastage_percent"}
    if any(
        value is None and key not in optional_defaults
        or value is not None and (not isfinite(value) or value < 0)
        for key, value in body.rates.items()
    ):
        raise HTTPException(422, "Master values must be finite non-negative numbers")
    default_margin = body.rates.get("default_margin_percent", MASTER_RATE_DEFAULTS["default_margin_percent"])
    if default_margin is not None and default_margin >= 100:
        raise HTTPException(422, "Default margin must be less than 100 percent")

    config = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
    if config is None:
        config = MasterConfiguration(id=1, rates=dict(MASTER_RATE_DEFAULTS))
        db.add(config)
    previous = _effective_master_rates(config)
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
        master_record = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
        return _run_calculation(payload, _active_formulas(db), _effective_master_rates(master_record))
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
    if body.module == "EB":
        raise HTTPException(409, f"{body.module} is CONFIGURATION REQUIRED")
    formulas = _active_formulas(db)
    master_record = db.query(MasterConfiguration).filter(MasterConfiguration.id == 1).first()
    master_rates = _effective_master_rates(master_record)
    matrix_mode = body.components is not None
    if matrix_mode:
        try:
            inputs = EstimateInput.model_validate({**body.inputs, "components": body.components})
            result = _run_component_calculation(
                inputs, formulas, only_module=body.module, master_rates=master_rates
            )
        except (ValidationError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
            raise HTTPException(422, str(exc)) from exc
        line = next((item for item in result["lines"] if item["module"] == body.module), None)
        if line is None:
            return {
                "line": None,
                "stored": False,
                "configuration_required": result["configuration_required"],
                "configuration_details": [
                    detail for detail in result["configuration_details"]
                    if detail["module"] == body.module
                ],
            }
        wrapper_final = result["wrapper_final_sheets"] if body.module == "Wrapper" else None
    else:
        model = module_models.get(body.module)
        if body.module == "Conversion":
            model = EstimateInput
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
            elif body.module == "Conversion":
                line, failure = _calculate_conversion_for_material(inputs, inputs.conversion_base_material, formulas)
                if line is None:
                    raise HTTPException(409, failure)
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
    master_rates = _effective_master_rates(master_record)
    result = _run_calculation(payload, formulas, master_rates)
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
    subtotal = round(unit_price * quantity, 2)
    gst_amt = round(subtotal * body.gst_percent / 100, 2)
    grand = round(evaluate_formula("quotation_complete_grand_total", {
        "unit_price": unit_price, "quantity": quantity, "gst_percent": body.gst_percent,
    }, formulas), 2)

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
    subtotal = round(unit_price * quantity, 2)
    gst_amount = round(subtotal * body.gst_percent / 100, 2)
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
        "grand_total": round(evaluate_formula("quotation_complete_grand_total", {
            "unit_price": unit_price, "quantity": quantity, "gst_percent": body.gst_percent,
        }, formulas), 2),
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
    subtotal = round(unit_price * quantity, 2)
    gst_amount = round(subtotal * body.gst_percent / 100, 2)
    grand_total = round(evaluate_formula("quotation_complete_grand_total", {
        "unit_price": unit_price, "quantity": quantity, "gst_percent": body.gst_percent,
    }, formulas), 2)
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
