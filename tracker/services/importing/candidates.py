from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ParsedMeasurementCandidate:
    """Intermediate representation of a parsed measurement before DB persistence."""

    raw_name: str
    raw_line: str
    value: float
    unit: str = ''
    observed_at: Optional[datetime] = None
    ref_min: Optional[float] = None
    ref_max: Optional[float] = None
    confidence: Optional[float] = None
    measurement_type_name: Optional[str] = None
