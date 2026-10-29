"""lab_text.py — minimal label normalization utilities (stdlib only)."""


def normalize_label(value: str, max_length: int = 80) -> str:
    """Normalize a label string.

    Raises:
        TypeError: if value is not a str, or max_length is not an int
            (bools are rejected even though bool subclasses int).
        ValueError: if max_length <= 0.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"value must be str, got {type(value).__name__}"
        )
    if isinstance(max_length, bool) or not isinstance(max_length, int):
        raise TypeError(
            f"max_length must be int, got {type(max_length).__name__}"
        )
    if max_length <= 0:
        raise ValueError(
            f"max_length must be positive, got {max_length}"
        )
    # str.split() with no args splits on any Unicode whitespace run,
    # which both collapses runs and trims the edges; empty input -> [].
    collapsed = " ".join(value.split())
    # Truncate to max_length Unicode characters, then drop any
    # trailing space left behind by cutting mid-run.
    return collapsed[:max_length].rstrip(" ")
