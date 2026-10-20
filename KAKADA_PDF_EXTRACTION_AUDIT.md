# Kakada PDF Extraction Audit

**Verification updated:** 2026-10-20
**Input:** `Kakada_Ramprasad_Premium Sweets_kappa_Ups Plan2.pdf`  
**Method:** Real PDF upload through `POST /api/layout/extract`; native PyMuPDF text extraction.  
**Result:** Project data and all four component records extracted. The 18 drawing dimensions are recovered from page 1. Extraction retains the Duplex `30x20` unit as null and the ambiguous `glass` finish as unconfirmed; the user later confirmed inches and Gloss for costing.

This PDF-specific audit records the current extraction behavior. The existing general `PROJECT_PROCESS_DATA.md` was left unchanged.

## 1. Project Fields

| Field | PDF text | Extracted / normalized result | PDF page |
|---|---|---|---:|
| Project name | Kakada premium sweet box | `Kakada premium sweet box` | 1 |
| Customer / brand | Kakada | `Kakada` | 1 |
| Product name | sweet box | `sweet box` | 1 |
| Box type | Top and bottom | `Top and bottom` | 1 |
| Finished box size | 208x148x36mm | 208 x 148 x 36 mm | 1 |
| Quantity | 5000 qty | 5000 | 1 |
| Revision | `-` | Blank; confirmation required | 1 |
| Drawing version | v1 | `v1` | 1 |
| Prepared date | 06.10.2026 | `06.10.2026` (raw text retained) | 1 |

Descriptive strings are extracted as values and shown for review; they do not need a numeric normalized value. Revision is blank in the source and is not filled with an invented value.

## 2. Component Values

| Component | Material | Sheet size | Other extracted values | Page |
|---|---|---|---|---:|
| Top-KAPPA-01 | White Back Kappa Board | 31 x 20.5 in; normalized to 787.4 x 520.7 mm | Thickness 1.5 mm; GSM per 1 mm 750; UPS 6 | 2 |
| Bottom-KAPPA-02 | White Back Kappa Board | 31 x 20.5 in; normalized to 787.4 x 520.7 mm | Thickness 1.5 mm; GSM per 1 mm 750; UPS 5 | 3 |
| WR-01 | Art Paper | 20 x 28 in; normalized to 508 x 711.2 mm | GSM 128; UPS 2 sets (top and bottom) | 4 |
| INS-DUPLEX-01 | Duplex | 30 x 20; unit not stated | GSM 230; UPS 2 | 5 |

The headings `BASE MATERIAL-1`, `BASE MATERIAL-2`, `WRAPPER`, and `INSERTS` identify their respective component routes. The extractor now maps those section headings to Base Material, Wrapper, and Insert, respectively. These heading-derived routes should still be reviewed against the intended manufacturing process.

## 3. Extracted Process Matrix

`YES` creates a route, `NO` excludes a route, and an absent value remains `REVIEW` until confirmed.

| Component | Base Material | Wrapper | Printing | Lamination | Punching | Insert |
|---|---|---|---|---|---|---|
| Top-KAPPA-01 | YES (section) | REVIEW | NO | NO | YES | REVIEW |
| Bottom-KAPPA-02 | YES (section) | REVIEW | NO | NO | YES | REVIEW |
| WR-01 | REVIEW | YES (section) | YES | YES, Matte | YES | REVIEW |
| INS-DUPLEX-01 | REVIEW | REVIEW | NO | YES, finish unresolved | YES | YES (section) |

Other process columns are unmarked in the PDF and remain REVIEW; they are not treated as NO.

## 4. Dieline Dimensions

All 18 explicit millimetre dimensions are extracted from page 1:

```text
208, 148, 36, 212.4, 152.9, 22, 256.75, 197.25, 318.75,
258.25, 295.15, 235.15, 348.55, 287.55, 206.28, 75.35,
206.28, 75.35 mm
```

They are preserved as drawing dimensions; the system does not assign them to component sheet sizes without an explicit relationship. Extraction supports both layouts tested: this Plan2 file has the drawing on page 1, while the older Plan filename referenced in the test is not present in the current workspace.

## 5. Confirmation Items

- **Duplex sheet unit:** The PDF says `30x20` without a unit. The user confirmed inches, so the costing run used 762 x 508 mm. The extractor still leaves unit null until a user enters that confirmation.
- **Duplex lamination finish:** The raw PDF says `Yes/glass`. The user confirmed Gloss; the extractor does not make this normalization itself.
- **Printing method and colour:** The PDF marks Printing YES but does not give Offset/Digital or a colour configuration. The user requested an editable colour field; the estimator now allows presets or custom text. The client method and colour remain to be entered.
- **Lamination method:** WR-01 finish `matt` is normalized to Matte, but the PDF does not specify the lamination method. The method remains unselected pending client confirmation.
- **Wastage and rates:** The user confirmed 10% Kappa/Wrapper wastage and accepted current saved master rates. Wastage is editable in Master Configuration and per estimate/component. Updates affect new/recalculated estimates; saved estimates retain their configuration snapshots.

## 6. Verification

- Live API upload returned HTTP 200 with 4 components, quantity 5000, finished size 208 x 148 x 36 mm, and 18 dimensions.
- The current workspace contains Plan2 only; the optional test for the older Plan filename is skipped when that file is absent.
- Focused formula/component tests: 55 passed, 1 skipped.
- Frontend production build: passed.
- No estimate, draft, quotation, or database configuration was created or changed during verification.
