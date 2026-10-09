import ast
import math
import operator


FORMULA_DEFINITIONS = {
    "kappa_effective_gsm": {
        "group": "Base Material", "title": "Effective GSM",
        "description": "GSM at 1 mm multiplied by material thickness.",
        "default_expression": "gsm_at_1mm * thickness_mm",
        "variables": {"gsm_at_1mm": "Material GSM at 1 mm", "thickness_mm": "Material thickness in millimetres"},
    },
    "kappa_sheet_area": {
        "group": "Base Material", "title": "Sheet Area",
        "description": "Sheet dimensions in millimetres are converted to inches, then to square metres using the formula reference conversion factor.",
        "default_expression": "sheet_length_mm / 25.4 * sheet_width_mm / 25.4 * 0.00064516",
        "variables": {"sheet_length_mm": "Sheet length in millimetres", "sheet_width_mm": "Sheet width in millimetres"},
    },
    "kappa_kg_per_sheet": {
        "group": "Base Material", "title": "KG per Sheet",
        "description": "Sheet area multiplied by effective GSM.",
        "default_expression": "sheet_area_m2 * effective_gsm / 1000",
        "variables": {"sheet_area_m2": "Sheet area in square metres", "effective_gsm": "Effective GSM"},
    },
    "kappa_base_sheets": {
        "group": "Base Material", "title": "Base Sheets",
        "description": "Order quantity divided by sheets per box, rounded up.",
        "default_expression": "ceil(quantity / ups)",
        "variables": {"quantity": "Order quantity", "ups": "Units produced per sheet"},
    },
    "kappa_wastage_sheets": {
        "group": "Base Material", "title": "Wastage Sheets",
        "description": "Base sheets multiplied by wastage percentage, rounded up.",
        "default_expression": "ceil(base_sheets * wastage_percent / 100)",
        "variables": {"base_sheets": "Base sheet count", "wastage_percent": "Wastage percentage"},
    },
    "kappa_final_sheets": {
        "group": "Base Material", "title": "Final Sheets",
        "description": "Base sheets plus wastage sheets.",
        "default_expression": "base_sheets + wastage_sheets",
        "variables": {"base_sheets": "Base sheet count", "wastage_sheets": "Wastage sheet count"},
    },
    "kappa_total_kg": {
        "group": "Base Material", "title": "Total KG",
        "description": "Final sheets multiplied by kilograms per sheet.",
        "default_expression": "final_sheets * kg_per_sheet",
        "variables": {"final_sheets": "Final sheet count", "kg_per_sheet": "Kilograms per sheet"},
    },
    "kappa_total_cost": {
        "group": "Base Material", "title": "Total Cost",
        "description": "Material weight multiplied by the effective rate.",
        "default_expression": "total_kg * rate_per_kg",
        "variables": {"total_kg": "Total material weight in kilograms", "rate_per_kg": "Effective rate per kilogram"},
    },
    "kappa_per_sheet": {
        "group": "Base Material", "title": "Per Sheet Cost",
        "description": "Weight per sheet multiplied by the effective rate.",
        "default_expression": "kg_per_sheet * rate_per_kg",
        "variables": {"kg_per_sheet": "Kilograms per sheet", "rate_per_kg": "Effective rate per kilogram"},
    },
    "wrapper_total_cost": {
        "group": "Wrapper", "title": "Total Cost",
        "description": "Wrapper weight multiplied by the effective rate.",
        "default_expression": "total_kg * rate_per_kg",
        "variables": {"total_kg": "Total wrapper weight in kilograms", "rate_per_kg": "Effective rate per kilogram"},
    },
    "wrapper_base_sheets": {
        "group": "Wrapper", "title": "Base Sheets",
        "description": "Order quantity divided by sheets per box, rounded up.",
        "default_expression": "ceil(quantity / ups)",
        "variables": {"quantity": "Order quantity", "ups": "Units produced per sheet"},
    },
    "wrapper_wastage_sheets": {
        "group": "Wrapper", "title": "Wastage Sheets",
        "description": "Base sheets multiplied by wastage percentage, rounded up.",
        "default_expression": "ceil(base_sheets * wastage_percent / 100)",
        "variables": {"base_sheets": "Base sheet count", "wastage_percent": "Wastage percentage"},
    },
    "wrapper_final_sheets": {
        "group": "Wrapper", "title": "Final Sheets",
        "description": "Base sheets plus wastage and make-ready sheets.",
        "default_expression": "base_sheets + wastage_sheets + make_ready_sheets",
        "variables": {"base_sheets": "Base sheet count", "wastage_sheets": "Wastage sheet count", "make_ready_sheets": "Make-ready sheet count"},
    },
    "wrapper_kg_per_sheet": {
        "group": "Wrapper", "title": "KG per Sheet",
        "description": "Sheet dimensions and GSM converted to kilograms.",
        "default_expression": "sheet_length_mm * sheet_width_mm * gsm / 1000000000",
        "variables": {"sheet_length_mm": "Sheet length in millimetres", "sheet_width_mm": "Sheet width in millimetres", "gsm": "Wrapper GSM"},
    },
    "wrapper_total_kg": {
        "group": "Wrapper", "title": "Total KG",
        "description": "Final sheets multiplied by kilograms per sheet.",
        "default_expression": "final_sheets * kg_per_sheet",
        "variables": {"final_sheets": "Final sheet count", "kg_per_sheet": "Kilograms per sheet"},
    },
    "wrapper_per_sheet": {
        "group": "Wrapper", "title": "Per Sheet Cost",
        "description": "Wrapper weight per sheet multiplied by the effective rate.",
        "default_expression": "kg_per_sheet * rate_per_kg",
        "variables": {"kg_per_sheet": "Kilograms per sheet", "rate_per_kg": "Effective rate per kilogram"},
    },
    "printing_total_cost": {
        "group": "Printing", "title": "Total Cost",
        "description": "First-tier rate plus any additional-sheet charges.",
        "default_expression": "first_rate if input_sheets <= 1000 else first_rate + (input_sheets - 1000) * additional_rate",
        "variables": {"first_rate": "Rate for the first 1,000 sheets", "input_sheets": "Number of wrapper sheets", "additional_rate": "Rate per sheet after the first 1,000"},
    },
    "printing_per_sheet": {
        "group": "Printing", "title": "Per Sheet Cost",
        "description": "Total printing cost divided by the number of sheets.",
        "default_expression": "total_cost / input_sheets if input_sheets else 0",
        "variables": {"total_cost": "Total printing cost", "input_sheets": "Number of wrapper sheets"},
    },
    "lamination_total_cost": {
        "group": "Lamination", "title": "Total Cost",
        "description": "Cost per sheet multiplied by wrapper sheets.",
        "default_expression": "cost_per_sheet * wrapper_final_sheets",
        "variables": {"cost_per_sheet": "Lamination cost per sheet", "wrapper_final_sheets": "Final wrapper sheet count"},
    },
    "lamination_per_sheet": {
        "group": "Lamination", "title": "Per Sheet Cost",
        "description": "Sheet area multiplied by the rate per 100 square inches.",
        "default_expression": "sheet_length_in * sheet_width_in * rate_per_100_sq_in / 100",
        "variables": {"sheet_length_in": "Sheet length in inches", "sheet_width_in": "Sheet width in inches", "rate_per_100_sq_in": "Rate per 100 square inches"},
    },
    "glue_total_cost": {
        "group": "Glue", "title": "Total Cost",
        "description": "Sum of glue component costs for the order.",
        "default_expression": "sum(component_costs)",
        "variables": {"component_costs": "Order cost for each glue component"},
    },
    "glue_kg_per_box": {
        "group": "Glue", "title": "Glue KG per Box",
        "description": "Glue area converted from square inches, multiplied by GSM.",
        "default_expression": "area_sq_in * 0.00064516 * gsm / 1000",
        "variables": {"area_sq_in": "Glue area in square inches", "gsm": "Glue GSM"},
    },
    "glue_component_cost": {
        "group": "Glue", "title": "Component Order Cost",
        "description": "Glue weight per box multiplied by rate and order quantity.",
        "default_expression": "kg_per_box * rate_per_kg * quantity",
        "variables": {"kg_per_box": "Glue kilograms per box", "rate_per_kg": "Glue rate per kilogram", "quantity": "Order quantity"},
    },
    "module_cost_per_box": {
        "group": "Estimate Totals", "title": "Module Cost / Box",
        "description": "Module total cost divided by order quantity.",
        "default_expression": "total_cost / quantity",
        "variables": {"total_cost": "This module's total cost", "quantity": "Order quantity"},
    },
    "punching_input_quantity": {
        "group": "Punching", "title": "Input Quantity",
        "description": "Wrapper punching uses final wrapper sheets; other materials use order quantity.",
        "default_expression": "wrapper_final_sheets if is_wrapper else quantity",
        "variables": {"wrapper_final_sheets": "Final wrapper sheet count", "is_wrapper": "Whether selected material is Wrapper", "quantity": "Order quantity"},
    },
    "punching_production_hours": {
        "group": "Punching", "title": "Production Hours",
        "description": "Punching input quantity divided by machine speed.",
        "default_expression": "input_quantity / speed",
        "variables": {"input_quantity": "Punching input quantity", "speed": "Machine sheets per hour"},
    },
    "punching_unit_cost": {
        "group": "Punching", "title": "Unit Cost",
        "description": "Punching total divided by the applicable box or sheet quantity.",
        "default_expression": "total_cost / unit_quantity",
        "variables": {"total_cost": "Total punching cost", "unit_quantity": "Applicable box or sheet quantity"},
    },
    "punching_total_cost": {
        "group": "Punching", "title": "Total Cost",
        "description": "Production and setup hours multiplied by the machine rate.",
        "default_expression": "(production_hours + setup_hours) * machine_rate",
        "variables": {"production_hours": "Punching production hours", "setup_hours": "Punching setup hours", "machine_rate": "Machine rate per hour"},
    },
    "embellishments_raw_cost": {
        "group": "Embellishments", "title": "Raw Cost",
        "description": "Area charge plus setup cost, before applying Tool Cost.",
        "default_expression": "area_sq_in * rate_per_sq_in + setup_cost",
        "variables": {"area_sq_in": "Embellishment area in square inches", "rate_per_sq_in": "Rate per square inch", "setup_cost": "Setup cost"},
    },
    "embellishments_total_cost": {
        "group": "Embellishments", "title": "Total Cost",
        "description": "The greater of raw cost and Tool Cost.",
        "default_expression": "max(raw_cost, tool_cost)",
        "variables": {"raw_cost": "Raw embellishment cost", "tool_cost": "Minimum tool cost"},
    },
    "embellishment_direct_cost_total": {
        "group": "Embellishments", "title": "Direct Cost Total",
        "description": "Configured per-box embossing or debossing cost multiplied by order quantity.",
        "default_expression": "rate_per_box * quantity",
        "variables": {"rate_per_box": "Configured embellishment cost per box", "quantity": "Order quantity"},
    },
    "embellishment_area_raw_cost": {
        "group": "Embellishments", "title": "Area-based Raw Cost",
        "description": "Component area multiplied by the configured rate per 100 square inches.",
        "default_expression": "area_sq_in * rate_per_100_sq_in / 100",
        "variables": {"area_sq_in": "Component embellishment area in square inches", "rate_per_100_sq_in": "Configured rate per 100 square inches"},
    },
    "embellishment_area_total_cost": {
        "group": "Embellishments", "title": "Area-based Order Cost",
        "description": "The greater of area cost per box and minimum cost per box, multiplied by order quantity.",
        "default_expression": "max(raw_cost_per_box, minimum_cost_per_box) * quantity",
        "variables": {"raw_cost_per_box": "Area-based embellishment cost per box", "minimum_cost_per_box": "Configured minimum cost per box", "quantity": "Order quantity"},
    },
    "tooling_area_die_cost": {
        "group": "Tooling / Dies", "title": "Area-based Die Cost",
        "description": "Configured die rate per square centimetre multiplied by tooling area.",
        "default_expression": "area_sq_cm * rate_per_sq_cm",
        "variables": {"area_sq_cm": "Die area in square centimetres", "rate_per_sq_cm": "Configured rate per square centimetre"},
    },
    "accessories_total_cost": {
        "group": "Accessories", "title": "Total Cost",
        "description": "Sum of accessory costs for the order.",
        "default_expression": "sum(accessory_costs)",
        "variables": {"accessory_costs": "Order cost for each accessory"},
    },
    "accessory_component_cost": {
        "group": "Accessories", "title": "Accessory Line Cost",
        "description": "Accessory quantity per box multiplied by unit cost and order quantity.",
        "default_expression": "quantity_per_box * unit_cost * quantity",
        "variables": {"quantity_per_box": "Accessory quantity per box", "unit_cost": "Accessory unit cost", "quantity": "Order quantity"},
    },
    "conversion_total_cost": {
        "group": "Conversion", "title": "Total Cost",
        "description": "Machine, labour, and setup cost. Conversion remains configuration-required until confirmed.",
        "default_expression": "machine_rate * machine_hours + labour_rate * labour_hours + setup_cost",
        "variables": {"machine_rate": "Machine rate", "machine_hours": "Machine hours", "labour_rate": "Labour rate", "labour_hours": "Labour hours", "setup_cost": "Setup cost"},
    },
    "conversion_semi_machine_hours": {
        "group": "Conversion", "title": "Semi-automatic Machine Hours",
        "description": "Twice the production duration at the configured boxes-per-hour rate.",
        "default_expression": "quantity / boxes_per_hour * 2",
        "variables": {"quantity": "Order quantity", "boxes_per_hour": "Configured boxes converted per hour"},
    },
    "conversion_semi_total_cost": {
        "group": "Conversion", "title": "Semi-automatic Labour Cost",
        "description": "Workers multiplied by hourly labour rate and machine hours.",
        "default_expression": "workers * (monthly_salary / (working_days * hours_per_day)) * machine_hours",
        "variables": {"workers": "Configured number of labourers", "monthly_salary": "Monthly salary per labourer", "working_days": "Working days per month", "hours_per_day": "Working hours per day", "machine_hours": "Calculated machine hours"},
    },
    "conversion_side_pasting_total_cost": {
        "group": "Conversion", "title": "Side Pasting Cost",
        "description": "Configured side-pasting rate per box multiplied by order quantity.",
        "default_expression": "rate_per_box * quantity",
        "variables": {"rate_per_box": "Configured side-pasting rate per box", "quantity": "Order quantity"},
    },
    "conversion_automatic_machine_hours": {
        "group": "Conversion", "title": "Automatic Machine Hours",
        "description": "Twice the production duration at the configured boxes-per-hour rate.",
        "default_expression": "quantity / boxes_per_hour * 2",
        "variables": {"quantity": "Order quantity", "boxes_per_hour": "Configured boxes converted per hour"},
    },
    "conversion_automatic_total_cost": {
        "group": "Conversion", "title": "Automatic Conversion Cost",
        "description": "Machine running cost plus two configured setup cycles.",
        "default_expression": "machine_hours * machine_rate + setup_hours * 2 * setup_rate",
        "variables": {"machine_hours": "Calculated machine hours", "machine_rate": "Machine rate per hour", "setup_hours": "Configured setup hours", "setup_rate": "Setup rate per hour"},
    },
    "conversion_contract_total_cost": {
        "group": "Conversion", "title": "Contract Conversion Cost",
        "description": "Configured contract rate per box multiplied by order quantity.",
        "default_expression": "rate_per_box * quantity",
        "variables": {"rate_per_box": "Configured contract rate per box", "quantity": "Order quantity"},
    },
    "estimate_total_cost": {
        "group": "Estimate Totals", "title": "Total Manufacturing Cost",
        "description": "Sum of all module totals.",
        "default_expression": "sum(module_totals)",
        "variables": {"module_totals": "Total cost for every costing module"},
    },
    "estimate_cost_per_box": {
        "group": "Estimate Totals", "title": "Overall Cost / Box",
        "description": "Total manufacturing cost divided by order quantity.",
        "default_expression": "total_cost / quantity",
        "variables": {"total_cost": "Total manufacturing cost", "quantity": "Order quantity"},
    },
    "selling_price_per_box": {
        "group": "Estimate Totals", "title": "Selling Price / Box",
        "description": "Overall cost per box adjusted for margin.",
        "default_expression": "cost_per_box / (1 - margin_percent / 100)",
        "variables": {"cost_per_box": "Overall cost per box", "margin_percent": "Margin percentage"},
    },
    "order_value": {
        "group": "Estimate Totals", "title": "Order Value",
        "description": "Selling price per box multiplied by order quantity.",
        "default_expression": "selling_price_per_box * quantity",
        "variables": {"selling_price_per_box": "Selling price per box", "quantity": "Order quantity"},
    },
    "module_weightage": {
        "group": "Estimate Totals", "title": "Module Weightage (%)",
        "description": "Module total divided by estimate total, expressed as a percentage.",
        "default_expression": "module_total / total_cost * 100 if total_cost else 0",
        "variables": {"module_total": "This module's total cost", "total_cost": "Total manufacturing cost"},
    },
    "quotation_subtotal": {
        "group": "Quotation / Proforma", "title": "Subtotal",
        "description": "Document unit price multiplied by order quantity.",
        "default_expression": "unit_price * quantity",
        "variables": {"unit_price": "Document unit price", "quantity": "Document order quantity"},
    },
    "quotation_gst_amount": {
        "group": "Quotation / Proforma", "title": "GST Amount",
        "description": "Subtotal multiplied by the GST percentage.",
        "default_expression": "subtotal * gst_percent / 100",
        "variables": {"subtotal": "Document subtotal", "gst_percent": "GST percentage"},
    },
    "quotation_grand_total": {
        "group": "Quotation / Proforma", "title": "Grand Total",
        "description": "Subtotal plus GST amount.",
        "default_expression": "subtotal + gst_amount",
        "variables": {"subtotal": "Document subtotal", "gst_amount": "Document GST amount"},
    },
}

DEFAULT_FORMULAS = {key: item["default_expression"] for key, item in FORMULA_DEFINITIONS.items()}

_BINARY_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_COMPARISON_OPERATORS = {
    ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
    ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne,
}
_FUNCTIONS = {"abs": abs, "ceil": math.ceil, "floor": math.floor, "max": max, "min": min, "round": round, "sum": sum}
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.IfExp, ast.Compare, ast.Call,
    ast.Name, ast.Load, ast.Constant, ast.List, ast.Tuple,
    *tuple(_BINARY_OPERATORS), *tuple(_UNARY_OPERATORS), *tuple(_COMPARISON_OPERATORS),
)


def _evaluate_node(node, variables):
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body, variables)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in _FUNCTIONS:
            return _FUNCTIONS[node.id]
        raise ValueError(f"Unknown formula variable: {node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left, variables)
        right = _evaluate_node(node.right, variables)
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in (left, right)):
            raise ValueError("Arithmetic operators require numeric operands")
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise ValueError("Formula exponent must be between -12 and 12")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if isinstance(result, (int, float)) and (not math.isfinite(result) or abs(result) > 1e100):
            raise ValueError("Formula intermediate value is outside the supported range")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand, variables))
    if isinstance(node, ast.IfExp):
        branch = node.body if _evaluate_node(node.test, variables) else node.orelse
        return _evaluate_node(branch, variables)
    if isinstance(node, ast.Compare):
        left = _evaluate_node(node.left, variables)
        for comparison, comparator in zip(node.ops, node.comparators):
            if type(comparison) not in _COMPARISON_OPERATORS:
                raise ValueError("Unsupported formula comparison")
            right = _evaluate_node(comparator, variables)
            if not _COMPARISON_OPERATORS[type(comparison)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS and not node.keywords:
        return _FUNCTIONS[node.func.id](*[_evaluate_node(arg, variables) for arg in node.args])
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_evaluate_node(item, variables) for item in node.elts]
        return values if isinstance(node, ast.List) else tuple(values)
    raise ValueError("Unsupported formula syntax")


def evaluate_formula(key, variables, formulas=None):
    expression = (formulas or DEFAULT_FORMULAS).get(key)
    if expression is None:
        raise ValueError(f"Unknown formula: {key}")
    tree = ast.parse(expression, mode="eval")
    allowed_variables = set(FORMULA_DEFINITIONS[key]["variables"])
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    unknown = names - allowed_variables - set(_FUNCTIONS)
    if unknown:
        raise ValueError(f"Unknown formula variable: {', '.join(sorted(unknown))}")
    if any(not isinstance(node, _ALLOWED_NODES) for node in ast.walk(tree)):
        raise ValueError("Unsupported formula syntax")
    result = _evaluate_node(tree, variables)
    if not isinstance(result, (int, float)) or isinstance(result, bool) or not math.isfinite(result) or abs(result) > 1e100:
        raise ValueError("Formula must return a finite number within the supported range")
    return float(result)


def validate_formula(key, expression):
    if key not in FORMULA_DEFINITIONS:
        raise ValueError(f"Unknown formula: {key}")
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 500:
        raise ValueError("Formula must contain between 1 and 500 characters")
    sample_variables = {
        name: [1.0, 2.0] if name.endswith(("costs", "totals")) else
        20.0 if name == "margin_percent" else
        10.0 if name in {"quantity", "input_sheets", "wrapper_final_sheets", "unit_count"} else 2.0
        for name in FORMULA_DEFINITIONS[key]["variables"]
    }
    evaluate_formula(key, sample_variables, {**DEFAULT_FORMULAS, key: expression.strip()})
    return expression.strip()


def validate_formula_set(formulas):
    unknown = set(formulas) - set(FORMULA_DEFINITIONS)
    if unknown:
        raise ValueError(f"Unknown formulas: {', '.join(sorted(unknown))}")
    validated = dict(DEFAULT_FORMULAS)
    for key, expression in formulas.items():
        validated[key] = validate_formula(key, expression)
    return validated