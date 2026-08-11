import re
import string
import unicodedata

_ASCII_LOWER_TRANS = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def normalize_slug(text: str) -> str:
    """Return a normalized slug using the transferred task rules."""
    normalized = text.translate(_ASCII_LOWER_TRANS)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = "".join(
        char
        for char in normalized
        if char == "-"
        or not (char in string.punctuation or unicodedata.category(char).startswith("P"))
    )
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")
