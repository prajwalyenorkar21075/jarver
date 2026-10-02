"""Engineering measurement and unit parser/normalizer."""
import re
import math
from typing import Optional, Tuple


UNIT_CONVERSIONS_TO_MM = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "millimetre": 1.0,
    "millimetres": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "centimetre": 10.0,
    "centimetres": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "metre": 1000.0,
    "metres": 1000.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
    "\"": 25.4,
    "ft": 304.8,
    "foot": 304.8,
    "feet": 304.8,
    "'": 304.8,
    "thou": 0.0254,
    "mil": 0.0254,
}

ANGLE_CONVERSIONS_TO_DEG = {
    "deg": 1.0,
    "degree": 1.0,
    "degrees": 1.0,
    "°": 1.0,
    "rad": 180.0 / math.pi,
    "radian": 180.0 / math.pi,
    "radians": 180.0 / math.pi,
}


def parse_fraction(s: str) -> Optional[float]:
    """Parse string fraction like '1/2' or '3/8' or mixed '1 1/2'."""
    s = s.strip()
    if "/" in s:
        parts = s.split()
        if len(parts) == 2:
            try:
                whole = float(parts[0])
                num, den = parts[1].split("/")
                return whole + float(num) / float(den)
            except Exception:
                return None
        elif len(parts) == 1:
            try:
                num, den = parts[0].split("/")
                return float(num) / float(den)
            except Exception:
                return None
    try:
        return float(s)
    except Exception:
        return None


def parse_dimension(val_or_str, default_unit: str = "mm") -> Tuple[float, str]:
    """
    Parse a dimension value and return (normalized_value_in_mm, original_unit).
    Examples:
      - 50 -> (50.0, 'mm')
      - '100 mm' -> (100.0, 'mm')
      - '2.5 inch' -> (63.5, 'inch')
      - '5 cm' -> (50.0, 'cm')
      - '1/2 inch' -> (12.7, 'inch')
    """
    if isinstance(val_or_str, (int, float)):
        scale = UNIT_CONVERSIONS_TO_MM.get(default_unit.lower(), 1.0)
        return float(val_or_str) * scale, default_unit

    text = str(val_or_str).strip().lower()
    
    # Check for unit suffix
    match = re.search(r"^(-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?)\s*([a-z\"']*)", text)
    if match:
        num_str = match.group(1).replace(" ", "")
        unit_str = match.group(2).strip() or default_unit
        num = parse_fraction(num_str)
        if num is not None:
            scale = UNIT_CONVERSIONS_TO_MM.get(unit_str, 1.0)
            return round(num * scale, 4), unit_str

    try:
        return float(text), default_unit
    except Exception:
        return 0.0, default_unit


def parse_angle(val_or_str, default_unit: str = "deg") -> Tuple[float, str]:
    """
    Parse an angle value and return (normalized_value_in_deg, original_unit).
    Examples:
      - 45 -> (45.0, 'deg')
      - '90 deg' -> (90.0, 'deg')
      - '3.14159 rad' -> (180.0, 'rad')
    """
    if isinstance(val_or_str, (int, float)):
        scale = ANGLE_CONVERSIONS_TO_DEG.get(default_unit.lower(), 1.0)
        return float(val_or_str) * scale, default_unit

    text = str(val_or_str).strip().lower()
    match = re.search(r"^(-?\d+(?:\.\d+)?)\s*([a-z°]*)", text)
    if match:
        num = float(match.group(1))
        unit = match.group(2).strip() or default_unit
        scale = ANGLE_CONVERSIONS_TO_DEG.get(unit, 1.0)
        return round(num * scale, 4), unit

    try:
        return float(text), default_unit
    except Exception:
        return 0.0, default_unit


def format_dimension(val_mm: float, unit: str = "mm") -> str:
    """Format millimeter value in target unit."""
    factor = UNIT_CONVERSIONS_TO_MM.get(unit.lower(), 1.0)
    display_val = val_mm / factor
    if abs(display_val - round(display_val)) < 0.001:
        return f"{int(round(display_val))} {unit}"
    return f"{display_val:.2f} {unit}"
