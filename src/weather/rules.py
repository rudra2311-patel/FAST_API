import json
from pathlib import Path
from typing import Dict, Any, List


# ----------------------------------------------------------
# Load rules JSON (dynamic, scalable)
# ----------------------------------------------------------

RULES_FILE = Path(__file__).parent / "crops_rules.json"


def load_rules(crop: str = "generic") -> Dict[str, Any]:
    """
    Load rule definitions for a given crop.
    If crop does not exist, fallback to generic rules.
    """
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        all_rules = json.load(f)

    if crop in all_rules:
        return all_rules[crop]

    return all_rules.get("generic", {})


# ----------------------------------------------------------
# Helper to convert string to float
# ----------------------------------------------------------

def _to_float(val: Any) -> float:
    try:
        return float(val)
    except:
        return 0.0


# ----------------------------------------------------------
# Simple operators: >, <, >=, <=
# ----------------------------------------------------------

def _matches_simple_operator(value: float, condition: str) -> bool:
    """
    Example:
        value = 80
        condition = ">75"  → True
    """

    if condition.startswith(">="):
        return value >= _to_float(condition[2:])

    if condition.startswith("<="):
        return value <= _to_float(condition[2:])

    if condition.startswith(">"):
        return value > _to_float(condition[1:])

    if condition.startswith("<"):
        return value < _to_float(condition[1:])

    return False


# ----------------------------------------------------------
# Range rules: [min, max]
# ----------------------------------------------------------

def _matches_range(value: float, range_list: List[float]) -> bool:
    if not isinstance(range_list, list) or len(range_list) != 2:
        return False
    low, high = range_list
    return low <= value <= high


# ----------------------------------------------------------
# Evaluate ALL rule conditions
# ----------------------------------------------------------

def evaluate_conditions(weather: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
    """
    weather = {
        "temperature": 27,
        "humidity": 85,
        "rainfall_mm": 12,
        "rain_probability": 70,
        "wind_speed": 30,
        "consecutive_rain_days": 2
    }
    """

    for key, cond in conditions.items():

        # Case 1: range rule
        if isinstance(cond, list):
            if not _matches_range(weather.get(key, 0), cond):
                return False

        # Case 2: string operator rule
        elif isinstance(cond, str) and (cond.startswith(">") or cond.startswith("<")):
            if not _matches_simple_operator(weather.get(key, 0), cond):
                return False

        # Case 3: exact match rule (rare)
        else:
            if weather.get(key) != cond:
                return False

    return True


# ----------------------------------------------------------
# Apply all rules for crop → return highest severity rule
# ----------------------------------------------------------

SEVERITY_PRIORITY = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}


def apply_rules(weather: Dict[str, Any], crop: str = "generic") -> Dict[str, Any]:
    rules = load_rules(crop)

    best_rule = None
    best_severity_value = 0

    for rule_name, rule_def in rules.items():
        conditions = rule_def.get("conditions", {})

        if evaluate_conditions(weather, conditions):

            severity = rule_def.get("severity", "low")
            sev_value = SEVERITY_PRIORITY.get(severity, 1)

            # pick highest severity rule
            if sev_value > best_severity_value:
                best_severity_value = sev_value
                best_rule = {
                    "risk": rule_name,
                    "severity": severity,
                    "message": rule_def.get("message", ""),
                    "advice": rule_def.get("advice", "")
                }

    if best_rule:
        return best_rule

    # Default safe result - Good weather conditions
    return {
        "risk": "none",
        "severity": "low",
        "message": "Weather conditions are favorable. No immediate risks detected for your crops.",
        "advice": "Continue regular monitoring and maintenance routines."
    }
