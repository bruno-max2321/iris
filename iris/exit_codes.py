"""Stable CLI exit codes. Every JSON error carries `code`, `message` and `retryable`."""

OK = 0
USAGE = 2
VALIDATION = 3
BUDGET_EXHAUSTED = 4
PROVIDER = 5  # retryable
PARTIAL = 6
LOCKED = 7
INPUT_UNAVAILABLE = 8
NOT_IMPLEMENTED = 9

NAMES = {
    OK: "ok",
    USAGE: "usage",
    VALIDATION: "validation",
    BUDGET_EXHAUSTED: "budget_exhausted",
    PROVIDER: "provider",
    PARTIAL: "partial",
    LOCKED: "locked",
    INPUT_UNAVAILABLE: "input_unavailable",
    NOT_IMPLEMENTED: "not_implemented",
}

RETRYABLE = {PROVIDER, LOCKED}


def error_payload(code: int, message: str, **extra: object) -> dict:
    payload = {
        "ok": False,
        "code": NAMES.get(code, str(code)),
        "exit_code": code,
        "message": message,
        "retryable": code in RETRYABLE,
    }
    payload.update(extra)
    return payload
