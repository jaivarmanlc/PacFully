# Kakada End-to-End Costing Log

**Verification update:** 2026-10-20
**PDF:** `Kakada_Ramprasad_Premium Sweets_kappa_Ups Plan2.pdf`  
**Order quantity:** 5,000 boxes  
**Status:** Client-confirmed inputs were applied and the calculation was rerun. Printing and lamination remain blocked pending method/colour choices, so the returned module subtotal is partial and is not a quotation. No estimate, draft, or quotation was saved.

## 1. Process Log

1. Uploaded the five-page PDF to `POST /api/layout/extract`.
2. Extracted project fields from page 1, component records from pages 2-5, and the 18 page-1 dieline dimensions.
3. Normalized safe values and units: Kappa and Wrapper sheet sizes to millimetres, Duplex `30x20` to 762x508 mm only after the user confirmed inches, finished box size to millimetres, and quantity to an integer.
4. Set component routes from explicit YES/NO values and the component section headings. Unknown processes stayed REVIEW.
5. Passed extracted component inputs into module calculation. WR-01's extracted wrapper values prefill the shared wrapper and printing stock controls.
6. Applied the user's confirmed 10% Kappa/Wrapper wastage and Gloss Duplex finish. Verified that missing print and lamination methods remain blocked instead of using defaults.

## 2. Component Routing and Inputs

| Component | Cost routes from PDF | Inputs sent to costing | Notes |
|---|---|---|---|
| Top-KAPPA-01 | Base Material, Punching | Sheet 787.4 x 520.7 mm; thickness 1.5 mm; GSM/mm 750; UPS 6 | Printing NO; Lamination NO |
| Bottom-KAPPA-02 | Base Material, Punching | Sheet 787.4 x 520.7 mm; thickness 1.5 mm; GSM/mm 750; UPS 5 | Printing NO; Lamination NO |
| WR-01 | Wrapper, Printing, Lamination, Punching | Sheet 508 x 711.2 mm (20 x 28 in); GSM 128; UPS 2; finish Matte | Printing method/colour and lamination method are not specified in the PDF |
| INS-DUPLEX-01 | Insert, Lamination, Punching | GSM 230; UPS 2; user-confirmed sheet 30 x 20 in = 762 x 508 mm; Gloss finish confirmed | Unit and finish were confirmed by the user; lamination method still needs selection |

The Base Material, Wrapper, and Insert routes are derived from the PDF's named component sections. Printing, Lamination, and Punching use the component-level YES/NO entries. Do not change REVIEW values to NO without confirmation.

## 3. Wrapper-to-Printing Dependency

WR-01 has 2 UPS and 5,000 boxes. With the user-confirmed 10% wastage and 150-sheet make-ready, final Wrapper sheets are `2,500 + 250 + 150 = 2,900`. Printing consumes those 2,900 sheets but remains blocked until its method and colour configuration are supplied. The PDF's `20 x 28 in` stock maps to the supported `20x28` print-size tier.

## 4. Costing Result

The read-only local Master Configuration contains:

- Margin: 20%; Kappa ₹82/kg; Wrapper ₹95/kg; Duplex ₹72/kg.
- Saved database wastage values were null; for this job the user confirmed 10% for Kappa and Wrapper. The application now uses 10% as the editable Master Configuration fallback, and estimate/component inputs remain editable.
- 20x28 printing: ₹3,500 first tier and ₹0.50 additional rate.
- Lamination base rates: thermal ₹1.10, cold ₹0.70, dry ₹0.80; method/finish overrides are zero.
- Punching machine rate: ₹400/hour.

The following module rows calculate using the confirmed inputs and current Master Configuration rates:

| Module | Calculated module cost (INR) | Status |
|---|---:|---|
| Kappa / Base Material | 76,325.65 | Calculated at 10% wastage |
| Wrapper | 12,740.52 | Calculated; final sheets 2,900 |
| Insert | 17,628.35 | Calculated with 30x20 in Duplex and 10% wastage |
| Punching | 16,066.67 | Calculated for all four components |
| Printing | Not included | Configuration required: printing method and colour |
| Lamination | Not included | Configuration required: lamination method |

**Calculated-module subtotal only:** INR 122,761.19. This is not a manufacturing total or quote because Printing and Lamination are unresolved. Do not use the API's partial aggregate, cost-per-box, selling-price, or order-value fields as a client quote.

The underlying `data/pacfully.db` record was not changed. The application now resolves unset saved wastage to the user-confirmed 10% default. Master Configuration changes apply to new/recalculated estimates; saved estimates keep their configuration snapshots, as requested.

## 5. What Must Be Confirmed Before Quoting

1. Confirm the printing method and the actual colour configuration for WR-01. Custom colour configurations can now be entered as text; the PDF only says Printing YES.
2. Select the lamination method for WR-01 and Duplex. The PDF says Matte for WR-01 but does not specify a method.
3. Review current master rates and the 150-sheet make-ready assumption. These are not sourced from the PDF.
4. Review Base Material/Wrapper/Insert section-derived routes and all REVIEW cells before finalizing.

## 6. Code and Test Record

- PDF section-heading routing is implemented in `backend/ai/layout_reader.py`.
- Unitless sheet dimensions remain unconfirmed and are not converted to millimetres in `backend/ai/layout_reader.py`; confirmed dimensions and finishes can be entered per component in the costing UI.
- Printing colour accepts suggested presets or custom user-entered text. PDF printing/lamination methods and colour are required to be explicit before costing.
- Upload handling applies the extracted quantity/customer/project, wrapper GSM/UPS/sheet dimensions, and supported print-sheet tier in `frontend/src/pages/CostEstimator.jsx`.
- Real-PDF regression coverage is in `tests/test_component_process.py`.
- Focused formula/component tests: 55 passed, 1 skipped.
- Frontend `npm run build`: passed.
- No database values were changed; no estimate/draft/quotation was created.

## 7. Running the Updated Project

The estimator route requires sign-in. No server or estimate was started/saved for this verification.
