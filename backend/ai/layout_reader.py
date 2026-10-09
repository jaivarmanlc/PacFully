"""Extract packaging specifications from native PDF text, then OCR if needed."""

import base64
import os
import re
import shutil

try:
	from component_process import PROCESS_TO_MODULE
except ModuleNotFoundError:
	from ..component_process import PROCESS_TO_MODULE


MATRIX_PROCESSES = (
	"Base Material", "Wrapper", "Printing", "Lamination", "Punching", "Die Cutting",
	"Glue", "Foiling", "Spot UV", "Drip-Off", "Embossing", "Debossing",
	"Accessories", "Insert", "Conversion", "EB", "One Time Cost",
)

FIELD_LABELS = {
	"component_name": (r"component\s*(?:id|name)",),
	"material": (r"component\s+material", r"material"),
	"sheet_size": (r"sheet\s+size",),
	"thickness_mm": (r"thickness",),
	"gsm_per_mm": (r"gsm\s+per\s+1\s*mm", r"gsm\s+at\s+1\s*mm"),
	"gsm": (r"gsm",),
	"ups": (r"ups",),
	"Wrapper": (r"wrapper",),
	"Punching": (r"punching",),
	"Die Cutting": (r"die\s*cutting",),
	"Lamination": (r"lamination",),
	"Printing": (r"printing",),
	"Foiling": (r"foiling", r"foiling\s*/\s*foil\s+stamp"),
	"Spot UV": (r"spot\s*uv",),
	"Drip-Off": (r"drip[\s-]*off",),
	"Embossing": (r"embossing",),
	"Debossing": (r"debossing",),
	"Glue": (r"glue",),
	"Accessories": (r"accessories?",),
	"Insert": (r"insert",),
	"Conversion": (r"conversion",),
	"EB": (r"eb",),
	"One Time Cost": (r"one\s*time\s*cost",),
	"Base Material": (r"base\s+material(?:\s+process)?",),
	"project_name": (r"project\s+name",),
	"customer_name": (r"customer\s*/\s*brand", r"customer\s+name"),
	"product_name": (r"product\s+name",),
	"box_type": (r"box\s+type",),
	"finished_box_size": (r"finished\s+box\s+size(?:\s*\([^)]*\))?",),
	"quantity": (r"quantity", r"order\s+quantity"),
	"revision": (r"revision\s+no\.?",),
	"drawing_version": (r"drawing\s+version",),
	"prepared_date": (r"prepared\s+date",),
}
_LABEL_PATTERNS = tuple(
	(key, re.compile(rf"^(?:{'|'.join(patterns)})(?=$|\s|[:=-])", re.IGNORECASE))
	for key, patterns in sorted(FIELD_LABELS.items(), key=lambda item: max(map(len, item[1])), reverse=True)
)


def _clean_text(value):
	value = str(value or "").replace("\u00d7", "x")
	value = value.replace("\u201c", '"').replace("\u201d", '"').replace("\u2033", '"')
	return re.sub(r"\s+", " ", value).strip()


def _strip_value_prefix(value):
	return re.sub(r"^[\s\-:;|]+", "", _clean_text(value)).strip()


def _header_key(value):
	normalized = re.sub(r"\s+", " ", value.strip().lower())
	if normalized in {"component", "component id", "component name", "component_name"}:
		return "component_name"
	if normalized in {"material", "component material"}:
		return "material"
	if normalized in {"punching / die cutting", "punching/die cutting", "punching-die cutting"}:
		return "punching_die_cutting"
	for process in PROCESS_TO_MODULE:
		if normalized == process.lower():
			return process
	return None


def parse_component_process_table(text):
	"""Read explicit YES/NO values in legacy pipe-delimited matrix tables."""
	lines = [line.strip() for line in text.splitlines() if "|" in line]
	components = []
	header_keys = None
	process_columns = []

	for line in lines:
		cells = [cell.strip() for cell in line.strip("| ").split("|")]
		keys = [_header_key(cell) for cell in cells]
		if "component_name" in keys and "material" in keys:
			header_keys = keys
			process_columns = [
				(index, key)
				for index, key in enumerate(keys)
				if key not in {None, "component_name", "material"}
			]
			continue
		if header_keys is None or len(cells) < len(header_keys):
			continue
		name_index = header_keys.index("component_name")
		material_index = header_keys.index("material")
		component_name = cells[name_index].strip()
		material = cells[material_index].strip()
		if not component_name or not material:
			continue

		processes = {process: None for process in MATRIX_PROCESSES}
		explicit_process_found = False
		for index, process in process_columns:
			state = cells[index].strip().upper()
			if state not in {"YES", "NO"}:
				continue
			explicit_process_found = True
			target_process = process
			if process == "punching_die_cutting":
				target_process = "Die Cutting" if material.strip().upper() in {"EVA", "EPE", "PU"} else "Punching"
			processes[target_process] = state == "YES"
			if process == "punching_die_cutting":
				other_process = "Punching" if target_process == "Die Cutting" else "Die Cutting"
				processes[other_process] = False
		if explicit_process_found:
			components.append({
				"component_name": component_name,
				"material": material,
				"source": "pdf_text",
				"processes": processes,
				"process_inputs": {},
			})
	return components


def _label_for_line(line):
	cleaned = _clean_text(line)
	for key, pattern in _LABEL_PATTERNS:
		match = pattern.match(cleaned)
		if not match:
			continue
		remainder = cleaned[match.end():]
		if remainder and remainder[0] not in ":=- \t":
			continue
		return key, _strip_value_prefix(remainder)
	return None, ""


def _extract_labeled_values(text):
	lines = [_clean_text(line) for line in text.splitlines()]
	lines = [(index, line) for index, line in enumerate(lines) if line]
	values = {}
	for position, (line_index, line) in enumerate(lines):
		key, value = _label_for_line(line)
		if not key:
			continue
		if not value:
			for _, candidate in lines[position + 1:]:
				if _label_for_line(candidate)[0]:
					break
				value = _strip_value_prefix(candidate)
				if value:
					break
		if value:
			values[key] = {"raw_value": value, "line_index": line_index}
	return values


def _number(value):
	match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", _clean_text(value))
	if not match:
		return None
	try:
		return float(match.group().replace(",", ""))
	except ValueError:
		return None


def _field(raw_value=None, page=None, source="pymupdf_text", confidence=0.99, normalized_value=None, review_status=None, bbox=None):
	if raw_value is None or not _clean_text(raw_value):
		return {
			"value": None,
			"normalized_value": None,
			"confidence": 0.0,
			"source": "not_found",
			"page": page,
			"review_status": "Confirmation Required",
		}
	status = review_status or "Review Required"
	result = {
		"value": _clean_text(raw_value),
		"normalized_value": normalized_value,
		"confidence": round(float(confidence), 3),
		"source": source,
		"page": page,
		"review_status": status,
	}
	if bbox:
		result["bbox"] = [round(float(value), 2) for value in bbox]
	return result


def _sheet_size(raw_value):
	dimensions, unit = _parse_dimensions(raw_value)
	if not dimensions or len(dimensions) < 2:
		return None, "Confirmation Required"
	if not unit:
		return {"length": dimensions[0], "width": dimensions[1], "unit": None}, "Confirmation Required"
	return {"length": dimensions[0], "width": dimensions[1], "unit": unit}, "Review Required"


def _parse_dimensions(raw_value):
	cleaned = _clean_text(raw_value).lower()
	cleaned = re.sub(r"(?<=\d)\s*\ufffd+\s*(?=\d)", " x ", cleaned)
	cleaned = re.sub(r"(?<=\d)\ufffd+", " ", cleaned).replace('"', " ")
	match = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)(?:\s*x\s*(\d+(?:\.\d+)?))?", cleaned)
	if not match:
		return None, None
	dimensions = [float(match.group(index)) for index in (1, 2, 3) if match.group(index)]
	unit_match = re.search(r"(mm|millimeters?|inches?|inch|in)\b", cleaned)
	unit = unit_match.group(1) if unit_match else None
	unit = "mm" if unit and unit.startswith("mm") else "in" if unit else None
	return dimensions, unit


def _process_value(raw_value):
	match = re.match(r"^\s*(yes|no)\b", _clean_text(raw_value), re.IGNORECASE)
	return None if not match else match.group(1).lower() == "yes"


def _page_bbox(page, value):
	if not value:
		return None
	try:
		rectangles = page.search_for(value)
	except Exception:
		return None
	return tuple(rectangles[0]) if rectangles else None


def _ocr_page(page):
	"""OCR one scanned page after local OpenCV cleanup; return text and confidence."""
	try:
		import cv2
		import numpy as np
		import pymupdf
		import pytesseract
		from pytesseract import Output
	except ImportError:
		return "", 0.0

	configured = os.getenv("TESSERACT_CMD")
	if not configured:
		configured = shutil.which("tesseract")
	if not configured:
		for candidate in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"D:\pacakges\tesseract\tesseract.exe"):
			if os.path.isfile(candidate):
				configured = candidate
				break
	if configured:
		pytesseract.pytesseract.tesseract_cmd = configured

	pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
	image = cv2.imdecode(np.frombuffer(pixmap.tobytes("png"), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
	if image is None:
		return "", 0.0
	image = cv2.medianBlur(image, 3)
	image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
	try:
		data = pytesseract.image_to_data(image, config="--psm 6", output_type=Output.DICT)
	except Exception:
		return "", 0.0
	lines = {}
	confidences = []
	for index, word in enumerate(data.get("text", [])):
		word = _clean_text(word)
		if not word:
			continue
		try:
			confidence = float(data["conf"][index])
		except (TypeError, ValueError, KeyError):
			continue
		if confidence >= 0:
			confidences.append(confidence / 100)
		key = tuple(data[name][index] for name in ("page_num", "block_num", "par_num", "line_num"))
		lines.setdefault(key, []).append(word)
	text = "\n".join(" ".join(words) for words in lines.values())
	return text, sum(confidences) / len(confidences) if confidences else 0.0


def _vision_fallback(page, page_number):
	"""Optionally resolve labels only after native text and OCR remain ambiguous."""
	api_key = os.getenv("GEMINI_API_KEY")
	if not api_key:
		return "", 0.0
	try:
		import pymupdf
		import requests
		pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
		image_data = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
		model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
		response = requests.post(
			f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
			params={"key": api_key},
			json={"contents": [{"parts": [
				{"text": "Resolve only visible component-to-label relationships on this page. Return exact component IDs, materials, dimensions, and explicit process YES/NO labels as plain label: value lines. Do not infer missing values or process decisions. This is PDF page " + str(page_number) + "."},
				{"inline_data": {"mime_type": "image/png", "data": image_data}},
			]}]},
			timeout=30,
		)
		response.raise_for_status()
		payload = response.json()
		text = payload["candidates"][0]["content"]["parts"][0].get("text", "")
		return text, 0.65 if text else 0.0
	except Exception:
		return "", 0.0


def _page_geometry(page):
	"""Report native PDF vectors and OpenCV geometry from a small page raster."""
	drawings = page.get_drawings()
	images = page.get_images(full=True)
	geometry = {
		"vector_path_count": len(drawings),
		"raster_image_count": len(images),
		"opencv_edge_pixels": 0,
		"opencv_contour_count": 0,
		"opencv_line_count": 0,
	}
	try:
		import cv2
		import numpy as np
		import pymupdf
		pixmap = page.get_pixmap(matrix=pymupdf.Matrix(0.4, 0.4), alpha=False)
		image = cv2.imdecode(np.frombuffer(pixmap.tobytes("png"), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
		if image is not None:
			edges = cv2.Canny(image, 60, 160)
			contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
			lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=30, maxLineGap=8)
			geometry.update({
				"opencv_edge_pixels": int(cv2.countNonZero(edges)),
				"opencv_contour_count": len(contours),
				"opencv_line_count": 0 if lines is None else len(lines),
			})
	except ImportError:
		pass
	return geometry


def _normalise_component(raw_fields, page, source, confidence):
	component_field_names = ("component_name", "material", "sheet_size", "gsm", "gsm_per_mm", "thickness_mm", "ups")
	fields = {}
	for name in component_field_names:
		entry = raw_fields.get(name)
		if entry:
			raw = entry["raw_value"]
			line_confidence = confidence if source in {"tesseract_ocr", "vision"} else 0.99
			normalized = None
			status = "Confirmation Required" if source == "vision" or line_confidence < 0.85 else "Review Required"
			if name in {"gsm", "gsm_per_mm", "thickness_mm", "ups"}:
				normalized = _number(raw)
				if normalized is None:
					status = "Confirmation Required"
			elif name == "component_name":
				normalized = _strip_value_prefix(raw)
			elif name == "sheet_size":
				normalized, status = _sheet_size(raw)
			elif name == "material":
				normalized = _strip_value_prefix(raw)
			fields[name] = _field(raw, page, source, line_confidence, normalized, status, entry.get("bbox"))
		else:
			fields[name] = _field(page=page)

	component_name = fields["component_name"]["normalized_value"]
	material = fields["material"]["normalized_value"]
	if not component_name or not material:
		return None
	processes = {process: None for process in MATRIX_PROCESSES}
	for process in MATRIX_PROCESSES:
		entry = raw_fields.get(process)
		if entry:
			raw = entry["raw_value"]
			value = _process_value(raw)
			field_confidence = confidence if source in {"tesseract_ocr", "vision"} else 0.99
			route_value = value if source != "vision" and field_confidence >= 0.85 else None
			fields[f"process_{process}"] = _field(
				raw, page, source, field_confidence,
				value,
				"Review Required" if route_value is not None else "Confirmation Required",
				entry.get("bbox"),
			)
			if route_value is not None:
				processes[process] = route_value
		else:
			fields[f"process_{process}"] = _field(page=page)
	if processes.get("Printing") is True:
		fields["printing_method"] = _field(page=page)
	if processes.get("Lamination") is True:
		fields["lamination_method"] = _field(page=page)
		lamination_raw = raw_fields.get("Lamination", {}).get("raw_value", "")
		finish_raw = re.sub(r"^\s*yes\b\s*/?\s*", "", lamination_raw, flags=re.IGNORECASE).strip()
		finish_match = re.search(r"\b(matt|matte|gloss|glossy|soft\s*touch)\b", finish_raw, re.IGNORECASE)
		finish_value = None
		if finish_match:
			finish_value = "Matte" if finish_match.group(1).lower() in {"matt", "matte"} else "Gloss" if "gloss" in finish_match.group(1).lower() else "Soft Touch"
		fields["lamination_finish"] = _field(
			finish_raw or None,
			page,
			source,
			confidence if source in {"tesseract_ocr", "vision"} else 0.99,
			finish_value,
			"Review Required" if finish_value and source != "vision" and confidence >= 0.85 else "Confirmation Required",
			_page_bbox(page, finish_raw),
		)

	process_inputs = {}
	sheet = fields["sheet_size"]["normalized_value"]
	if sheet and sheet["unit"]:
		factor = 25.4 if sheet["unit"] == "in" else 1
		sheet_length_mm = round(sheet["length"] * factor, 4)
		sheet_width_mm = round(sheet["width"] * factor, 4)
		if "KAPPA" in material.upper():
			module_inputs = {
				"kappa_sheet_length_mm": sheet_length_mm,
				"kappa_sheet_width_mm": sheet_width_mm,
			}
			if fields["thickness_mm"]["normalized_value"] is not None:
				module_inputs["kappa_thickness_mm"] = fields["thickness_mm"]["normalized_value"]
			if fields["gsm_per_mm"]["normalized_value"] is not None:
				module_inputs["kappa_gsm_at_1mm"] = fields["gsm_per_mm"]["normalized_value"]
			if fields["ups"]["normalized_value"] is not None:
				module_inputs["kappa_ups"] = int(fields["ups"]["normalized_value"])
			process_inputs["Kappa"] = module_inputs
		elif "ART PAPER" in material.upper():
			module_inputs = {
				"wrapper_sheet_length_mm": sheet_length_mm,
				"wrapper_sheet_width_mm": sheet_width_mm,
			}
			if fields["gsm"]["normalized_value"] is not None:
				module_inputs["wrapper_gsm"] = fields["gsm"]["normalized_value"]
			if fields["ups"]["normalized_value"] is not None:
				module_inputs["wrapper_ups"] = int(fields["ups"]["normalized_value"])
			process_inputs["Wrapper"] = module_inputs
		elif "DUPLEX" in material.upper():
			process_inputs["Insert"] = {
				"extracted_sheet_length_mm": sheet_length_mm,
				"extracted_sheet_width_mm": sheet_width_mm,
			}
	if "ART PAPER" in material.upper() and fields["gsm"]["normalized_value"] is not None:
		process_inputs.setdefault("Wrapper", {})["wrapper_gsm"] = fields["gsm"]["normalized_value"]
	if "Lamination" in raw_fields:
		finish = re.search(r"\b(matt|matte|gloss|glossy|soft\s*touch)\b", raw_fields["Lamination"]["raw_value"], re.IGNORECASE)
		if finish:
			value = "Matte" if finish.group(1).lower() in {"matt", "matte"} else "Gloss" if "gloss" in finish.group(1).lower() else "Soft Touch"
			process_inputs.setdefault("Lamination", {})["lamination_finish"] = value

	return {
		"component_name": component_name,
		"material": material,
		"source": "pdf_text" if source == "pymupdf_text" else source,
		"processes": processes,
		"process_inputs": process_inputs,
		"extracted_fields": fields,
	}


def _normalise_document_fields(raw_fields, page, source, confidence):
	fields = {}
	for name in ("project_name", "customer_name", "product_name", "box_type", "finished_box_size", "quantity", "revision", "drawing_version", "prepared_date"):
		entry = raw_fields.get(name)
		if not entry:
			fields[name] = _field(page=page)
			continue
		raw = entry["raw_value"]
		normalized = None
		status = "Review Required"
		if name == "quantity":
			normalized = _number(raw)
			if normalized is None or normalized <= 0:
				status = "Confirmation Required"
			else:
				normalized = int(normalized)
		elif name == "finished_box_size":
			dimensions, unit = _parse_dimensions(raw)
			normalized = {"length": dimensions[0], "width": dimensions[1], "height": dimensions[2], "unit": unit} if dimensions and len(dimensions) == 3 else None
			if normalized is None or unit is None:
				status = "Confirmation Required"
		elif name == "revision" and raw.strip(" -") == "":
			status = "Confirmation Required"
		fields[name] = _field(raw, page, source, confidence if source in {"tesseract_ocr", "vision"} else 0.99, normalized, status, entry.get("bbox"))
	return fields


def _extract_page_fields(page, page_number, source, text, confidence):
	raw_fields = _extract_labeled_values(text)
	section_process = None
	for line in text.splitlines():
		section = _clean_text(line)
		if re.match(r"^base\s+material(?:\s*[-–]?\s*\d+)?$", section, re.IGNORECASE):
			section_process = "Base Material"
			break
		if re.fullmatch(r"wrapper", section, re.IGNORECASE):
			section_process = "Wrapper"
			break
		if re.fullmatch(r"inserts?", section, re.IGNORECASE):
			section_process = "Insert"
			break
	if section_process:
			raw_fields[section_process] = {"raw_value": "Yes", "line_index": None}
	for entry in raw_fields.values():
		entry["bbox"] = _page_bbox(page, entry["raw_value"]) if entry.get("line_index") is not None else None
	components = []
	if raw_fields.get("component_name") and raw_fields.get("material"):
		component = _normalise_component(raw_fields, page_number, source, confidence)
		if component:
			components.append(component)
	document_fields = _normalise_document_fields(raw_fields, page_number, source, confidence)
	return components, document_fields


def _extract_table_text(page):
	"""Convert reliably labeled PyMuPDF table cells into parser-compatible text."""
	try:
		tables = page.find_tables().tables
	except (AttributeError, TypeError, ValueError):
		return "", 0

	lines = []
	for table in tables:
		try:
			rows = table.extract()
		except (AttributeError, TypeError, ValueError):
			continue
		headers = None
		for row in rows:
			cells = [_clean_text(cell) for cell in row]
			if not any(cells):
				continue
			keys = [_header_key(cell) for cell in cells]
			if "component_name" in keys and "material" in keys:
				headers = cells
				lines.append(" | ".join(cells))
				continue
			if headers and len(cells) >= len(headers):
				lines.append(" | ".join(cells[:len(headers)]))
				continue
			if len(cells) >= 2 and _label_for_line(cells[0])[0] and cells[1]:
				lines.append(f"{cells[0]}: {cells[1]}")
				continue
			for label_index, cell in enumerate(row):
				label_lines = [_clean_text(line) for line in str(cell or "").splitlines() if _clean_text(line)]
				if not label_lines or not all(_label_for_line(line)[0] for line in label_lines):
					continue
				for value_index, value_cell in enumerate(row):
					if value_index == label_index:
						continue
					value_lines = [_strip_value_prefix(line) for line in str(value_cell or "").splitlines() if _clean_text(line)]
					if len(value_lines) == len(label_lines) and all(value_lines):
						lines.extend(f"{label}: {value}" for label, value in zip(label_lines, value_lines))
						break
				else:
					continue
				break
			else:
				lines.extend(line for cell in row for line in str(cell or "").splitlines() if _clean_text(line))
	return "\n".join(lines), len(tables)


def extract_pdf_layout(content):
	"""Extract normalized component data, document data, and page diagnostics."""
	try:
		import pymupdf
	except ImportError:
		import fitz as pymupdf

	document = pymupdf.open(stream=content, filetype="pdf")
	components = []
	document_field_candidates = {}
	page_results = []
	layout_dimensions = []
	vision_used = False
	try:
		for page_index, page in enumerate(document):
			page_number = page_index + 1
			native_text = page.get_text("text")
			table_text, table_count = _extract_table_text(page)
			source = "pymupdf_text"
			text = native_text
			confidence = 0.99
			native_fields = _extract_labeled_values(native_text)
			native_has_component = bool(native_fields.get("component_name") and native_fields.get("material"))
			native_has_document_fields = any(native_fields.get(name) for name in (
				"project_name", "customer_name", "product_name", "finished_box_size", "quantity",
			))
			if not native_has_component and not native_has_document_fields and table_text:
				text = "\n".join(part for part in (native_text, table_text) if part.strip())
				native_fields = _extract_labeled_values(text)
				native_has_component = bool(native_fields.get("component_name") and native_fields.get("material"))
			native_has_process = any(native_fields.get(process) for process in MATRIX_PROCESSES)
			needs_ocr = len(_clean_text(native_text)) < 35 or (
				bool(page.get_images(full=True)) and (not native_has_component or not native_has_process)
			)
			if needs_ocr:
				ocr_text, ocr_confidence = _ocr_page(page)
				ocr_fields = _extract_labeled_values(ocr_text)
				ocr_has_component = bool(ocr_fields.get("component_name") and ocr_fields.get("material"))
				ocr_has_process = any(ocr_fields.get(process) for process in MATRIX_PROCESSES)
				if ocr_text.strip() and (not native_has_component or (ocr_has_component and (not native_has_process or ocr_has_process))):
					text, confidence, source = ocr_text, ocr_confidence, "tesseract_ocr"
			if not text.strip():
				text, confidence = _vision_fallback(page, page_number)
				if text.strip():
					source = "vision"
					vision_used = True
			page_components, page_fields = _extract_page_fields(page, page_number, source, text, confidence)
			if not page_components:
				for legacy_component in parse_component_process_table(text):
					name = legacy_component["component_name"]
					material = legacy_component["material"]
					fields = {
						"component_name": _field(name, page_number, source, confidence, name, bbox=_page_bbox(page, name)),
						"material": _field(material, page_number, source, confidence, material, bbox=_page_bbox(page, material)),
					}
					for process in MATRIX_PROCESSES:
						value = legacy_component["processes"].get(process)
						fields[f"process_{process}"] = _field(
							None if value is None else "Yes" if value else "No",
							page_number,
							source,
							confidence,
							value,
							"Review Required" if value is not None else "Confirmation Required",
						)
					legacy_component.update({
						"source_page": page_number,
						"confidence": confidence,
						"extracted_fields": fields,
					})
					page_components.append(legacy_component)
			if not page_components and source != "vision" and re.search(r"\b(component|material)\b", text, re.IGNORECASE):
				vision_text, vision_confidence = _vision_fallback(page, page_number)
				if vision_text.strip():
					vision_components, vision_fields = _extract_page_fields(
						page, page_number, "vision", vision_text, vision_confidence,
					)
					if vision_components:
						page_components, page_fields = vision_components, vision_fields
						vision_used = True
			components.extend(page_components)
			for name, value in page_fields.items():
				if value["value"] is not None:
					document_field_candidates.setdefault(name, []).append(value)
			finished_size_on_page = page_fields["finished_box_size"]["value"] is not None
			finished_size_seen = bool(document_field_candidates.get("finished_box_size"))
			if finished_size_on_page or (page_number == len(document) and not finished_size_seen):
				for match in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?\s*mm\b", text, re.IGNORECASE):
					value = _clean_text(match.group())
					layout_dimensions.append(_field(value, page_number, source, confidence if source == "tesseract_ocr" else 0.99, _number(value), "Review Required"))
			geometry = _page_geometry(page)
			page_results.append({
				"page": page_number,
				"text_source": source,
				"text_characters": len(text),
				"native_text_characters": len(native_text),
				"table_count": table_count,
				**geometry,
			})
	finally:
		document.close()

	document_fields = {}
	for name in ("project_name", "customer_name", "product_name", "box_type", "finished_box_size", "quantity", "revision", "drawing_version", "prepared_date"):
		candidates = document_field_candidates.get(name, [])
		document_fields[name] = max(candidates, key=lambda candidate: candidate["confidence"]) if candidates else _field()
	for component in components:
		component["source_page"] = component["extracted_fields"]["component_name"]["page"]
		component["confidence"] = min(field["confidence"] for field in component["extracted_fields"].values() if field["source"] != "not_found")

	return {
		"components": components,
		"document_fields": document_fields,
		"layout_dimensions": layout_dimensions,
		"pages": page_results,
		"vision_used": vision_used,
		"vision_status": "used" if vision_used else "configured" if os.getenv("GEMINI_API_KEY") else "not_configured",
		"source": "PyMuPDF with OCR/Vision fallback as needed",
		"message": f"Extracted {len(components)} component(s). Review extracted values and confirm every process before costing." if components else "No component records found. Add components and confirm all required values manually.",
	}


def extract_pdf_component_processes(content):
	"""Backward-compatible helper returning only component records."""
	return extract_pdf_layout(content)["components"]


def extract_pdf_component_processes_legacy(content):
	"""Extract explicit pipe-delimited rows without requiring component pages."""
	try:
		import pymupdf
	except ImportError:
		import fitz as pymupdf
	document = pymupdf.open(stream=content, filetype="pdf")
	try:
		text = "\n".join(page.get_text("text") for page in document)
	finally:
		document.close()
	return parse_component_process_table(text)
