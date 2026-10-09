# Kakada End-to-End Costing Log

**Run date:** 2026-10-07  
**PDF:** `Kakada_Ramprasad_Premium Sweets_kappa_Ups Plan2.pdf`  
**Order quantity:** 5,000 boxes  
**Status:** Extraction and routing verified. The returned cost is a partial, default-rate scenario and is not ready for quotation.

## 1. Process Log

1. Uploaded the five-page PDF to `POST /api/layout/extract`.
2. Extracted project fields from page 1, component records from pages 2-5, and the 18 page-1 dieline dimensions.
3. Normalized safe values and units: Kappa sheet sizes to millimetres, wrapper sheet size to millimetres, box size to millimetres, and quantity to an integer.
4. Set component routes from explicit YES/NO values and the component section headings. Unknown processes stayed REVIEW.
5. Passed extracted component inputs into module calculation. WR-01's extracted wrapper values now prefill the shared wrapper and printing stock controls.
6. Calculated applicable modules and held unsupported Duplex costs for confirmation.

## 2. Component Routing and Inputs

| Component | Cost routes from PDF | Inputs sent to costing | Notes |
|---|---|---|---|
| Top-KAPPA-01 | Base Material, Punching | Sheet 787.4 x 520.7 mm; thickness 1.5 mm; GSM/mm 750; UPS 6 | Printing NO; Lamination NO |
| Bottom-KAPPA-02 | Base Material, Punching | Sheet 787.4 x 520.7 mm; thickness 1.5 mm; GSM/mm 750; UPS 5 | Printing NO; Lamination NO |
| WR-01 | Wrapper, Printing, Lamination, Punching | Sheet 508 x 711.2 mm (20 x 28 in); GSM 128; UPS 2; finish Matte | Printing method/colour and lamination method are not specified in the PDF |
| INS-DUPLEX-01 | Insert, Lamination, Punching | GSM 230; UPS 2 | Insert material cost blocked: `30x20` unit absent. Lamination blocked: `glass` unresolved |

The Base Material, Wrapper, and Insert routes are derived from the PDF's named component sections. Printing, Lamination, and Punching use the component-level YES/NO entries. Do not change REVIEW values to NO without confirmation.

## 3. Wrapper-to-Printing Dependency

For WR-01, wrapper UPS is 2 and quantity is 5,000:

- Base wrapper sheets: 5,000 / 2 = 2,500
- Wastage: 10% of 2,500 = 250 sheets (current estimator default)
- Make-ready: 150 sheets (current estimator default)
- Final wrapper sheets: 2,500 + 250 + 150 = 2,900

Printing consumes those 2,900 final wrapper sheets. The PDF's 20 x 28 in stock is converted to the supported `20x28` print-size tier. Calculate Wrapper before an isolated Printing calculation; Calculate All can calculate dependent modules in sequence.

## 4. Costing Result

The following trace uses extracted quantity/material inputs, extracted wrapper stock size, the current default formula set, and current local default/master estimate settings. Rates, wastage, make-ready, print method, colour, and lamination method are not specified in the PDF.

| Module | Total (INR) | Cost per box (INR) | Routed component(s) | Status |
|---|---:|---:|---|---|
| Kappa / Base Material | 73,098.75 | 14.6198 | Top-KAPPA-01, Bottom-KAPPA-02 | Calculated |
| Wrapper | 12,740.52 | 2.5481 | WR-01 | Calculated; final sheets 2,900 |
| Printing | 4,450.00 | 0.8900 | WR-01 | Calculated using 20x28 tier and estimator defaults |
| Lamination | 35,728.00 | 7.1456 | WR-01 | Calculated for Matte; Insert finish blocked |
| Punching | 16,066.67 | 3.2133 | All four components | Calculated |
| Insert | Not included | Not included | INS-DUPLEX-01 | Configuration required: sheet-size unit missing |

**Current partial total:** INR 142,083.94  
**Current partial cost per box:** INR 28.4168  
**Configuration required:** Insert; Lamination (the Duplex component's finish)

The total includes only the resolved WR-01 Lamination row, not the Duplex Insert Lamination row. It also excludes the Duplex Insert material cost. Therefore, this is not a complete manufacturing cost or a quote-ready amount.

## 5. What Must Be Confirmed Before Quoting

1. Confirm whether `30x20` Duplex sheets are inches, centimetres, or another unit.
2. Clarify whether `glass` means Gloss or a different finish; enter the confirmed value.
3. Confirm the lamination method. The PDF says Matte for WR-01 but gives no method.
4. Confirm printing method and colour configuration for WR-01; the PDF only says Printing YES.
5. Review current master rates, wastage, and 150-sheet make-ready assumptions. They are not sourced from the PDF.
6. Review Base Material/Wrapper/Insert section-derived routes and all REVIEW cells before finalizing.

## 6. Code and Test Record

- PDF section-heading routing is implemented in `backend/ai/layout_reader.py`.
- Unconfirmed Insert sheet units and lamination finishes are prevented from silently using unrelated defaults in `backend/routes.py`.
- Upload handling applies the extracted quantity/customer/project, wrapper GSM/UPS/sheet dimensions, and supported print-sheet tier in `frontend/src/pages/CostEstimator.jsx`.
- Real-PDF regression coverage is in `tests/test_component_process.py`.
- Backend tests: 40 passed, 1 skipped (the optional legacy Plan PDF is not present; Plan2 passed).
- Frontend `npm run build`: passed.

## 7. Running the Updated Project

The Vite frontend is available at `http://127.0.0.1:5174/` and is configured to use the updated API on port 8001. The estimator route requires sign-in. Port 8000 was already in use by a pre-existing Pacfully API and was left untouched.
