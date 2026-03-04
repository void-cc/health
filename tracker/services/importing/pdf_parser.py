import io
import re
from datetime import datetime
from typing import List

from django.utils import timezone as tz

from .candidates import ParsedMeasurementCandidate


def _extract_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber with pytesseract OCR fallback."""
    text = ''
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
                for table in page.extract_tables():
                    for row in table:
                        row_text = ' '.join(str(cell) for cell in row if cell)
                        if row_text not in text:
                            text += row_text + '\n'
    except Exception:
        pass

    if len(text.strip()) < 50:
        try:
            import pdf2image
            import pytesseract
            text = ''
            for img in pdf2image.convert_from_bytes(pdf_bytes):
                text += pytesseract.image_to_string(img) + '\n'
        except Exception:
            pass

    return text


def parse_pdf(pdf_bytes: bytes, known_names: List[str]) -> List[ParsedMeasurementCandidate]:
    """Parse PDF bytes into a list of ParsedMeasurementCandidate objects.

    Uses fuzzy matching against *known_names* to identify measurement lines.
    Lines with no numeric value are skipped.
    """
    from thefuzz import fuzz
    from thefuzz import process as fuzz_process

    text = _extract_text(pdf_bytes)

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})|(\d{1,2}/\d{1,2}/\d{4})', text)
    pdf_date: datetime = tz.now()
    if date_match:
        if date_match.group(1):
            try:
                pdf_date = tz.make_aware(datetime.strptime(date_match.group(1), '%Y-%m-%d'))
            except ValueError:
                pass
        else:
            try:
                pdf_date = tz.make_aware(datetime.strptime(date_match.group(2), '%m/%d/%Y'))
            except ValueError:
                pass

    candidates: List[ParsedMeasurementCandidate] = []
    seen_names: set = set()

    for line in text.split('\n'):
        line = line.strip()
        if not line or not known_names:
            continue

        best_match = fuzz_process.extractOne(line, known_names, scorer=fuzz.partial_ratio)
        if not best_match or best_match[1] <= 85:
            continue

        t_name = best_match[0]
        if len(t_name) <= 3 and t_name not in line.split():
            continue
        if t_name in seen_names:
            continue

        nums = re.findall(r'[-+]?\d*\.\d+|\d+', line)
        if not nums:
            continue

        seen_names.add(t_name)
        candidates.append(ParsedMeasurementCandidate(
            raw_name=t_name,
            raw_line=line,
            value=float(nums[0]),
            observed_at=pdf_date,
        ))

    return candidates
