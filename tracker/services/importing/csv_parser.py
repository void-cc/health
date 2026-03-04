import csv
import io
from datetime import datetime
from typing import List

from django.utils import timezone as tz

from .candidates import ParsedMeasurementCandidate


def parse_csv(file_content: str) -> List[ParsedMeasurementCandidate]:
    """Parse CSV content into a list of ParsedMeasurementCandidate objects.

    Expected columns: Date, Name, Value, Unit, Normal Min, Normal Max
    Rows missing Date, Name, or Value are silently skipped.
    """
    stream = io.StringIO(file_content, newline=None)
    reader = csv.DictReader(stream)
    candidates: List[ParsedMeasurementCandidate] = []

    for row in reader:
        raw_line = ','.join(str(v) for v in row.values())
        date_str = (row.get('Date') or '').strip()
        name = (row.get('Name') or '').strip()
        value_str = (row.get('Value') or '').strip()
        unit = (row.get('Unit') or '').strip()
        ref_min_str = (row.get('Normal Min') or '').strip()
        ref_max_str = (row.get('Normal Max') or '').strip()

        if not date_str or not name or not value_str:
            continue

        try:
            observed_at = tz.make_aware(datetime.strptime(date_str, '%Y-%m-%d'))
        except ValueError:
            continue

        try:
            value = float(value_str)
        except ValueError:
            continue

        ref_min = None
        ref_max = None
        try:
            if ref_min_str:
                ref_min = float(ref_min_str)
        except ValueError:
            pass
        try:
            if ref_max_str:
                ref_max = float(ref_max_str)
        except ValueError:
            pass

        candidates.append(ParsedMeasurementCandidate(
            raw_name=name,
            raw_line=raw_line,
            value=value,
            unit=unit,
            observed_at=observed_at,
            ref_min=ref_min,
            ref_max=ref_max,
        ))

    return candidates
