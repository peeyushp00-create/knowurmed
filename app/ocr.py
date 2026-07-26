"""
Prescription OCR pipeline.

Extracts text from an uploaded prescription image/PDF via Tesseract, then uses
plain regex + fuzzy string matching (no LLM, no ML model) to guess candidate
medicine names/strengths/frequencies/durations against our own verified
MEDICINE catalog. Every result is treated as a *candidate* — the caller is
responsible for making the user confirm or edit each one before it's used
for anything downstream.
"""
import difflib
import re

from django.conf import settings
from django.db.models import Q
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

LOW_CONFIDENCE_THRESHOLD = 50

STRENGTH_RE = re.compile(r'\b\d+(\.\d+)?\s?(mg|mcg|g|ml)\b', re.IGNORECASE)
DURATION_RE = re.compile(r'\bfor\s+\d+\s+days?\b', re.IGNORECASE)
FREQUENCY_PATTERNS = [
    re.compile(r'\b(once|twice|three times|four times)\s+(a\s+)?day\b', re.IGNORECASE),
    re.compile(r'\b(OD|BD|TDS|QID|BID)\b'),
    re.compile(r'\b\d-\d-\d\b'),
]


def _extract_lines_from_image(image):
    """Return [(line_text, avg_word_confidence), ...] grouped by Tesseract's line numbering."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    lines = {}
    for i, word in enumerate(data['text']):
        word = word.strip()
        if not word:
            continue
        try:
            conf = float(data['conf'][i])
        except (TypeError, ValueError):
            continue
        if conf < 0:
            continue
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        bucket = lines.setdefault(key, {'words': [], 'confs': []})
        bucket['words'].append(word)
        bucket['confs'].append(conf)

    result = []
    for key in sorted(lines.keys()):
        words = lines[key]['words']
        confs = lines[key]['confs']
        result.append((' '.join(words), sum(confs) / len(confs) if confs else 0))
    return result


def _images_from_file(file_path, content_type):
    if content_type == 'application/pdf':
        from pdf2image import convert_from_path
        kwargs = {'poppler_path': settings.POPPLER_PATH} if settings.POPPLER_PATH else {}
        return convert_from_path(file_path, **kwargs)
    return [Image.open(file_path)]


def run_ocr(file_path, content_type):
    """Returns (raw_text, overall_confidence, lines)."""
    images = _images_from_file(file_path, content_type)
    all_lines = []
    for image in images:
        all_lines.extend(_extract_lines_from_image(image))

    raw_text = '\n'.join(text for text, _ in all_lines)
    confidences = [c for _, c in all_lines if c > 0]
    overall_confidence = sum(confidences) / len(confidences) if confidences else 0
    return raw_text, overall_confidence, all_lines


def match_medicine(name_guess):
    """Fuzzy-match a detected name against our own verified MEDICINE catalog. Never invents a match."""
    from .models import MEDICINE

    name_guess = (name_guess or '').strip()
    if len(name_guess) < 3:
        return None

    catalog = list(MEDICINE.objects.values_list('Medicine_name', flat=True)) + \
        list(MEDICINE.objects.values_list('Generic_Name', flat=True))
    close = difflib.get_close_matches(name_guess, catalog, n=1, cutoff=0.72)
    if not close:
        return None
    return MEDICINE.objects.filter(Q(Medicine_name=close[0]) | Q(Generic_Name=close[0])).first()


def _parse_line(text):
    strength_match = STRENGTH_RE.search(text)
    strength = strength_match.group(0) if strength_match else ''

    duration_match = DURATION_RE.search(text)
    duration = duration_match.group(0) if duration_match else ''

    frequency = ''
    for pattern in FREQUENCY_PATTERNS:
        match = pattern.search(text)
        if match:
            frequency = match.group(0)
            break

    name_guess = text[:strength_match.start()].strip(' ,.-') if strength_match else text.strip()
    return {'name_guess': name_guess, 'strength': strength, 'frequency': frequency, 'duration': duration}


def build_prescription_items(prescription, lines):
    """Build (unsaved) PrescriptionItem instances from OCR lines. Caller saves them."""
    from .models import PrescriptionItem

    items = []
    for text, confidence in lines:
        parsed = _parse_line(text)
        if not parsed['name_guess']:
            continue

        medicine = match_medicine(parsed['name_guess'])

        # Skip lines with no medicine match AND no dosage-like signal at all —
        # these are almost always headers, doctor names, dates, etc., not medicines.
        if not medicine and not (parsed['strength'] or parsed['frequency'] or parsed['duration']):
            continue

        items.append(PrescriptionItem(
            prescription=prescription,
            detected_name=parsed['name_guess'] or (medicine.Medicine_name if medicine else ''),
            detected_strength=parsed['strength'],
            detected_frequency=parsed['frequency'],
            detected_duration=parsed['duration'],
            ocr_confidence=confidence,
            matched_medicine=medicine,
            position=len(items),
        ))
    return items


def process_prescription_file(prescription_file):
    """
    Runs OCR on an already-saved PrescriptionFile, stores the OCRResult, and creates
    PrescriptionItem candidates on its Prescription. Returns the OCRResult.
    """
    from .models import OCRResult

    raw_text, overall_confidence, lines = run_ocr(
        prescription_file.file.path, prescription_file.content_type,
    )

    ocr_result = OCRResult.objects.create(
        prescription_file=prescription_file,
        raw_text=raw_text,
        confidence=overall_confidence,
    )

    items = build_prescription_items(prescription_file.prescription, lines)
    if items:
        from .models import PrescriptionItem
        PrescriptionItem.objects.bulk_create(items)

    return ocr_result
