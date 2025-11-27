import re

# Define the normalization rules as a list of (regex_pattern, replacement_string) tuples.
# Order matters! More specific or context-sensitive rules should generally come first.
NORMALIZATION_RULES = [
    (r"[^A-Z0-9\s&]", ""),  # 1. Remove punctuation (keep &) - global
    (
        r"\b(PRIVATE|PVT|PTE)\s+(LIMITED|LTD)\b",
        "PVT LTD",
    ),  # 2. Handle PRIVATE LIMITED combo
    (r"\bPTE\b", "PVT"),  # 3. Handle PTE specifically (often safe as suffix)
    (r"\bLIMITED$", "LTD"),  # 4. LIMITED at end of string
    (r"\bCORPORATION\b", "CORP"),  # 5. CORPORATION anywhere
    (r"\bINCORPORATED\b", "INC"),  # 6. INCORPORATED anywhere
    (r"\bCOMPANY$", "CO"),  # 7. COMPANY at end only
    (r"\bDEPARTMENT\b", "DEPT"),  # 8. DEPARTMENT anywhere
    (r"\bBROTHERS$", "BROS"),  # 9. BROTHERS at end
    (r"\bAND\b", "&"),  # 10. AND anywhere
    (r"\s+", " "),  # 11. Cleanup multiple spaces to single space
]


def normalize_name(name):
    if not name:
        return None

    norm = name.upper().strip()

    for pattern, replacement in NORMALIZATION_RULES:
        norm = re.sub(pattern, replacement, norm)

    return norm.strip()

