def normalize_status(status: str) -> str:
    return " ".join(status.replace("_", " ").replace("-", " ").split()).casefold()


def status_badge_class(status: str) -> str:
    normalized_status = normalize_status(status)
    if normalized_status in {
        "submitted",
        "matched",
        "interviewing",
        "awaiting rematch",
        "open",
    }:
        return "status-badge status-in-progress"
    if normalized_status in {"offered", "awaiting student response"}:
        return "status-badge status-awaiting"
    if normalized_status in {"accepted", "placed", "filled"}:
        return "status-badge status-success"
    if normalized_status in {
        "rejected by company",
        "declined by student",
        "not matched",
    }:
        return "status-badge status-negative"
    if (
        normalized_status in {"closed", "cycle closed", "position closed"}
        or normalized_status.startswith("closed ")
    ):
        return "status-badge status-closed"
    return "status-badge status-neutral"


def status_label(status: str) -> str:
    return " ".join(status.replace("_", " ").replace("-", " ").split()).title()
