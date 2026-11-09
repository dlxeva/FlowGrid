"""Read the explicitly supplied downstream consequence of a decision."""


def decision_impact(candidate: dict) -> str:
    value = candidate.get("decision_impact")
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value or value.startswith("(") or len(value.splitlines()) != 1:
        return ""
    if value.casefold() in {"n/a", "none", "unknown", "tbd", "待定", "无"}:
        return ""
    return value
