import pytest
import sys
import os

# Add the load_and_search directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "load_and_search"))
from normalization_logic import normalize_name


@pytest.mark.parametrize(
    "input_name, expected",
    [
        # Standard Suffixes
        ("ABC Private Limited", "ABC PVT LTD"),
        ("ABC Pvt. Ltd.", "ABC PVT LTD"),
        ("ABC Pvt Ltd", "ABC PVT LTD"),
        ("ABC Pte Ltd", "ABC PVT LTD"),
        ("Global Corporation", "GLOBAL CORP"),
        ("Global Corp.", "GLOBAL CORP"),
        ("Example Incorporated", "EXAMPLE INC"),
        ("Example Inc.", "EXAMPLE INC"),
        ("Test Company", "TEST CO"),
        ("Smith Brothers", "SMITH BROS"),
        # Punctuation Removal
        ("ABC, Private Limited.", "ABC PVT LTD"),
        ("A.B.C. Corp", "ABC CORP"),
        # Safety Checks (Context Awareness)
        (
            "Private Detectives Inc.",
            "PRIVATE DETECTIVES INC",
        ),  # 'Private' at start preserved
        ("The Private Bank", "THE PRIVATE BANK"),  # 'Private' in middle preserved
        ("Company of Heroes", "COMPANY OF HEROES"),  # 'Company' at start preserved
        (
            "Bad Company",
            "BAD CO",
        ),  # 'Company' at end replaced (Debatable, but consistent with rules)
        ("Brothers in Arms", "BROTHERS IN ARMS"),  # 'Brothers' at start preserved
        # Complex Combinations
        ("Smith & Sons Ltd", "SMITH & SONS LTD"),
        ("Department of Justice", "DEPT OF JUSTICE"),
        # Edge Cases
        ("", None),
        (None, None),
        ("   ", ""),
    ],
)
def test_normalize_name(input_name, expected):
    assert normalize_name(input_name) == expected
