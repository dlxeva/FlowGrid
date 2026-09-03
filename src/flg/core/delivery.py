"""Health checks for an optional, machine-readable active delivery contract."""

from datetime import datetime, timedelta

REQUIRED_FIELDS = (
    "code_root",
    "candidate_version",
    "owner",
    "as_of",
    "gates",
    "evidence",
    "next_action",
)
STRING_FIELDS = ("code_root", "candidate_version", "owner", "next_action")


def active_delivery_issues(state: dict, *, now: datetime | None = None) -> list[str]:
    """Return actionable issues without mutating project state.

    The active_delivery extension is optional and only applies while a project
    is actively shipping a candidate.
    """
    delivery = state.get("active_delivery")
    if delivery is None:
        return []
    if not isinstance(delivery, dict):
        return ["active_delivery must be an object"]

    issues = [
        f"active_delivery missing {field}"
        for field in REQUIRED_FIELDS
        if field not in delivery or delivery[field] is None or delivery[field] == ""
    ]
    if issues:
        return issues

    for field in STRING_FIELDS:
        value = delivery[field]
        if not isinstance(value, str) or not value.strip():
            issues.append(f"active_delivery {field} must be a non-empty string")

    for field in ("gates", "evidence"):
        value = delivery[field]
        if not isinstance(value, list):
            issues.append(f"active_delivery {field} must be a list")
        elif not value or any(not isinstance(item, str) or not item.strip() for item in value):
            issues.append(f"active_delivery {field} must contain non-empty strings")

    as_of_value = delivery["as_of"]
    if not isinstance(as_of_value, str):
        issues.append("active_delivery as_of must be an ISO-8601 timestamp")
        return issues
    try:
        as_of = datetime.fromisoformat(as_of_value.replace("Z", "+00:00"))
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            issues.append("active_delivery as_of must include a timezone")
        else:
            reference = now or datetime.now(as_of.tzinfo)
            if reference.tzinfo is None or reference.utcoffset() is None:
                issues.append("active_delivery comparison time must include a timezone")
            elif as_of - reference > timedelta(minutes=5):
                issues.append("active_delivery as_of is in the future")
            elif reference - as_of > timedelta(days=14):
                issues.append(
                    "active_delivery is older than 14 days; "
                    "refresh its evidence or explicitly retire it"
                )
    except (TypeError, ValueError):
        issues.append("active_delivery as_of must be an ISO-8601 timestamp")
    return issues
