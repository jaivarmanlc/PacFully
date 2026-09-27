"""
Pacfully Cost Intelligence — complete API routes.
Covers: health, costing engine (stateless), customers CRUD,
estimates CRUD + finalize, quotations + PDF generation, audit log.
"""

import os
from datetime import datetime
from math import ceil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from database import get_db
from models import AuditEvent, CostLine, Customer, Estimate, Quotation
from quotation.pdf_generator import generate_quotation_pdf, generate_proforma_pdf

router = APIRouter()

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

class EstimateInput(BaseModel):
    # meta
    customer_id:   int | None = None
    customer_name: str = ""
    job_name:      str = ""
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
    print_override_rate:       float | None = Field(default=None, ge=0)
    lamination_type:           str   = "thermal"
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
    print_override_rate: float | None = Field(default=None, ge=0)

class LaminationModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    wrapper_final_sheets: int = Field(gt=0)
    lamination_type: str = "thermal"
    lamination_sheet_length_in: float = Field(gt=0)
    lamination_sheet_width_in: float = Field(gt=0)
    lam_override_rate: float | None = Field(default=None, ge=0)

class GlueModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    glue_lines: list[GlueLine]

class PunchingModuleInput(BaseModel):
    quantity: int = Field(gt=0)
    punching_material: str = "Kappa"
    punching_machine_rate_per_hour: float = Field(ge=0)
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
    estimate_id: int | None = Field(default=None, gt=0)

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
    estimate_id:      int
    doc_type:         str   = "Quotation"   # "Quotation" | "Proforma Invoice"
    customer_address: str   = ""
    gst_percent:      float = 18.0
    validity_days:    int   = 15
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

def _costing_line(module, total, quantity, rows):
    return {
        "module":      module,
        "total_cost":  round(total, 4),
        "cost_per_box":round(total / quantity, 4),
        "trace":       [{"label": l, "value": str(v)} for l, v in rows],
    }

def _effective_rate(override_rate, master_rate, fallback_rate):
    return override_rate if override_rate is not None else master_rate if master_rate is not None else fallback_rate

def _calculate_kappa(p):
    qty = p.quantity
    eff_kappa_gsm  = p.kappa_gsm_at_1mm * p.kappa_thickness_mm
    kappa_area_m2  = p.kappa_sheet_length_mm * p.kappa_sheet_width_mm / 1_000_000
    kappa_kg_sheet = kappa_area_m2 * eff_kappa_gsm / 1000
    kappa_base     = ceil(qty / p.kappa_ups)
    kappa_waste    = ceil(kappa_base * p.kappa_wastage_percent / 100)
    kappa_final    = kappa_base + kappa_waste
    kappa_kg       = kappa_final * kappa_kg_sheet
    rate           = _effective_rate(p.kappa_override_rate, p.kappa_master_rate, p.kappa_rate_per_kg)
    kappa_per_sheet_cost = kappa_kg_sheet * rate
    kappa_total    = kappa_kg * rate
    line = _costing_line("Kappa", kappa_total, qty, [
        ("Effective GSM",    f"{p.kappa_gsm_at_1mm} × {p.kappa_thickness_mm} = {eff_kappa_gsm}"),
        ("Base sheets",      kappa_base), ("Wastage sheets", kappa_waste),
        ("Final sheets",     kappa_final), ("Total KG", f"{kappa_kg:.4f}"),
        ("Per Sheet Cost",   f"{kappa_kg_sheet:.4f} × ₹{rate:g} = ₹{kappa_per_sheet_cost:.2f} / sheet"),
    ])
    return line

def _calculate_wrapper(p):
    qty = p.quantity
    wrapper_base   = ceil(qty / p.wrapper_ups)
    wrapper_waste  = ceil(wrapper_base * p.wrapper_wastage_percent / 100)
    wrapper_final  = wrapper_base + wrapper_waste + p.wrapper_make_ready_sheets
    wrapper_kg_sh  = p.wrapper_sheet_length_mm * p.wrapper_sheet_width_mm * p.wrapper_gsm / 1_000_000_000
    wrapper_kg     = wrapper_final * wrapper_kg_sh
    rate           = _effective_rate(p.wrapper_override_rate, p.wrapper_master_rate, p.wrapper_rate_per_kg)
    wrapper_total  = wrapper_kg * rate
    line = _costing_line("Wrapper", wrapper_total, qty, [
        ("Base sheets",      wrapper_base), ("Wastage sheets", wrapper_waste),
        ("Make-ready",       p.wrapper_make_ready_sheets),
        ("Final sheets",     wrapper_final), ("Total KG", f"{wrapper_kg:.4f}"),
    ])
    return line, wrapper_final

def _calculate_printing(p, wrapper_final):
    pr             = PRINT_RATES.get(p.print_sheet_size, PRINT_RATES["28x40"])
    first_rate     = p.print_override_rate if p.print_override_rate is not None else pr["first"]
    printing_total = first_rate if wrapper_final <= 1000 else first_rate + (wrapper_final - 1000) * pr["additional"]
    return _costing_line("Printing", printing_total, p.quantity, [
        ("Input",            f"{wrapper_final} final wrapper sheets"),
        ("Sheet tier",       p.print_sheet_size),
        ("Additional rate",  pr["additional"]),
    ])

def _calculate_lamination(p, wrapper_final):
    master_rate    = LAMINATION_RATES.get(p.lamination_type, 1.10)
    lam_rate       = p.lam_override_rate if p.lam_override_rate is not None else master_rate
    lam_per_sheet  = p.lamination_sheet_length_in * p.lamination_sheet_width_in * lam_rate / 100
    lamination_total = lam_per_sheet * wrapper_final
    return _costing_line("Lamination", lamination_total, p.quantity, [
        ("Rate/100 sq.in",   lam_rate),
        ("Cost/sheet",       f"{lam_per_sheet:.4f}"),
        ("Input",            f"{wrapper_final} wrapper sheets"),
    ])

def _calculate_glue(p):
    # Glue: weight per box × rate × quantity = total order glue cost
    glue_total     = sum(
        (g.area_sq_in * 0.00064516 * g.gsm / 1000) * g.rate_per_kg * p.quantity
        for g in p.glue_lines
    )
    return _costing_line("Glue", glue_total, p.quantity, [
        ("Formula",          "Area × 0.00064516 × GSM / 1000 × rate"),
        ("Components",       len(p.glue_lines)),
    ])

def _calculate_punching(p, wrapper_final):
    punch          = PUNCHING_RATES.get(p.punching_material, PUNCHING_RATES["Kappa"])
    punch_quantity = wrapper_final if p.punching_material == "Wrapper" else p.quantity
    prod_hrs       = punch_quantity / punch["speed"]
    punching_total = (prod_hrs + punch["setup_hours"]) * p.punching_machine_rate_per_hour
    return _costing_line("Punching", punching_total, p.quantity, [
        ("Speed",            punch["speed"]),
        ("Production hrs",   f"{prod_hrs:.4f}"),
        ("Setup hrs",        punch["setup_hours"]),
    ])

def _calculate_embellishments(p):
    emb_raw        = p.embellishment_area_sq_in * p.embellishment_rate_per_sq_in + p.embellishment_setup
    emb_total      = max(emb_raw, p.embellishment_minimum)
    return _costing_line("Embellishments", emb_total, p.quantity, [
        ("Raw cost",         emb_raw), ("Minimum", p.embellishment_minimum),
    ])

def _calculate_accessories(p):
    acc_total      = sum(a.quantity_per_box * a.unit_cost * p.quantity for a in p.accessories)
    return _costing_line("Accessories", acc_total, p.quantity, [
        ("Formula",          "Qty/box × unit cost × order qty"),
        ("Items",            len(p.accessories)),
    ])

def _calculate_conversion(p):
    conv_total     = (p.conversion_machine_rate * p.conversion_machine_hours
                    + p.conversion_labour_rate  * p.conversion_labour_hours
                    + p.conversion_setup)
    return _costing_line("Conversion", conv_total, p.quantity, [
        ("Status",           "CONFIGURATION REQUIRED"),
        ("Machine+Labour+Setup", conv_total),
    ])

def _calculate_eb(p):
    return _costing_line("EB", 0, p.quantity, [
        ("Status",           "CONFIGURATION REQUIRED"),
        ("Formula",          "Not defined"),
    ])

def _run_calculation(p: EstimateInput) -> dict:
    """Calculate the complete estimate in dependency order."""
    qty = p.quantity

    kappa_line = _calculate_kappa(p)
    wrapper_line, wrapper_final = _calculate_wrapper(p)
    printing_line = _calculate_printing(p, wrapper_final)
    lamination_line = _calculate_lamination(p, wrapper_final)
    glue_line = _calculate_glue(p)
    punching_line = _calculate_punching(p, wrapper_final)
    embellishments_line = _calculate_embellishments(p)
    accessories_line = _calculate_accessories(p)
    conversion_line = _calculate_conversion(p)
    eb_line = _calculate_eb(p)

    lines = [
        kappa_line, wrapper_line, printing_line, lamination_line, glue_line,
        punching_line, embellishments_line, accessories_line, conversion_line, eb_line,
    ]

    total        = sum(l["total_cost"] for l in lines)
    cpb          = total / qty
    selling_p    = cpb / (1 - p.margin_percent / 100)
    order_val    = selling_p * qty

    for l in lines:
        l["weightage_percent"] = round(l["total_cost"] / total * 100, 4) if total else 0

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

# ═══════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
def health():
    return {"status": "ok", "service": "pacfully-cost-intelligence"}

# ═══════════════════════════════════════════════════════════════
# Costing engine — stateless calculate (no DB)
# ═══════════════════════════════════════════════════════════════

@router.post("/estimates/calculate")
def calculate_estimate(payload: EstimateInput):
    return _run_calculation(payload)

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
    if body.module in {"Conversion", "EB"}:
        raise HTTPException(409, f"{body.module} is CONFIGURATION REQUIRED")
    model = module_models.get(body.module)
    if model is None:
        raise HTTPException(404, "Unknown costing module")
    try:
        inputs = model.model_validate(body.inputs)
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc

    if body.module == "Kappa":
        line = _calculate_kappa(inputs)
        wrapper_final = None
    elif body.module == "Wrapper":
        line, wrapper_final = _calculate_wrapper(inputs)
    elif body.module == "Printing":
        line = _calculate_printing(inputs, inputs.wrapper_final_sheets)
        wrapper_final = None
    elif body.module == "Lamination":
        line = _calculate_lamination(inputs, inputs.wrapper_final_sheets)
        wrapper_final = None
    elif body.module == "Glue":
        line = _calculate_glue(inputs)
        wrapper_final = None
    elif body.module == "Punching":
        if inputs.punching_material == "Wrapper" and inputs.wrapper_final_sheets is None:
            raise HTTPException(422, "Calculate Wrapper first to determine Final Wrapper Sheets.")
        line = _calculate_punching(inputs, inputs.wrapper_final_sheets)
        wrapper_final = None
    elif body.module == "Embellishments":
        line = _calculate_embellishments(inputs)
        wrapper_final = None
    else:
        line = _calculate_accessories(inputs)
        wrapper_final = None

    line["weightage_percent"] = None
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
            total = sum(item.total_cost for item in stored_lines)
            line["weightage_percent"] = round(line["total_cost"] / total * 100, 4) if total else 0
            cost_line.weightage_pct = line["weightage_percent"]
            estimate.total_manufacturing_cost = round(total, 4)
            estimate.cost_per_box = round(total / estimate.order_quantity, 4)
            estimate.selling_price_per_box = round(
                estimate.cost_per_box / (1 - estimate.margin_percent / 100), 4
            )
            estimate.order_value = round(estimate.selling_price_per_box * estimate.order_quantity, 4)
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
    result = _run_calculation(payload)
    num    = _next_estimate_number(db)

    est = Estimate(
        estimate_number          = num,
        customer_id              = payload.customer_id,
        customer_name            = payload.customer_name,
        job_name                 = payload.job_name,
        status                   = "Draft",
        input_snapshot           = payload.model_dump(),
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
    est = db.query(Estimate).filter(Estimate.id == body.estimate_id).first()
    if not est:
        raise HTTPException(404, "Estimate not found")

    q_num    = _next_quotation_number(db, body.doc_type)
    subtotal = round(est.selling_price_per_box * est.order_quantity, 2)
    gst_amt  = round(subtotal * body.gst_percent / 100, 2)
    grand    = round(subtotal + gst_amt, 2)

    q = Quotation(
        quotation_number = q_num,
        estimate_id      = est.id,
        doc_type         = body.doc_type,
        customer_name    = est.customer_name,
        customer_address = body.customer_address,
        job_name         = est.job_name,
        order_quantity   = est.order_quantity,
        unit_price       = est.selling_price_per_box,
        subtotal         = subtotal,
        gst_percent      = body.gst_percent,
        gst_amount       = gst_amt,
        grand_total      = grand,
        validity_days    = body.validity_days,
        notes            = body.notes,
        status           = "Draft",
    )
    db.add(q)
    db.flush()

    # Generate PDF
    pdf_data = {
        "quotation_number": q_num, "doc_type": body.doc_type,
        "customer_name": est.customer_name, "customer_address": body.customer_address,
        "job_name": est.job_name, "order_quantity": est.order_quantity,
        "unit_price": est.selling_price_per_box, "subtotal": subtotal,
        "gst_percent": body.gst_percent, "gst_amount": gst_amt, "grand_total": grand,
        "validity_days": body.validity_days, "notes": body.notes,
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
           detail=f"{est.customer_name} — Grand Total ₹{grand:,.2f}",
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
            "notes": q.notes or "",
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
def get_audit_log(db: Session = Depends(get_db)):
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
