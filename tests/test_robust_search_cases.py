import pytest
import sys
import os
import json

# Add the load_and_search directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'load_and_search'))
import search_bq

@pytest.mark.integration
@pytest.mark.parametrize("search_term, expected_entity_id, description", [
    ("AERO-CARIBBEAN", 36, "Exact match on alias with hyphen"),
    ("AEROCARIBBEAN", 36, "Fuzzy match removing hyphen"),
    ("BLUE LAGOON GROUP", 23665, "Exact match"),
    ("Blue Lagoon Grp", 23665, "Fuzzy match with custom abbreviation, expect to fail without normalization, pass with"),
    ("Blue Lagoon Group Ltd", 23665, "Exact with suffix"),
    ("Blue Lagoon Group Limited", 23665, "Normalization (Limited -> Ltd)"),
    ("Hamza", 29862, "Substring match (Al Ali and Al Hamza LLC)"),
    ("Hital Exchange", 26556, "Exact match"),
    ("Hital Xchange", 26556, "Fuzzy typo (Exchange -> Xchange)"),
    
    # New cases for common terms
    ("Corp", 8255, "Search for common abbreviation 'Corp'"), # Entity 8255 has CARGO AIRCRAFT LEASING CORP.
    ("Corporation", 8255, "Search for full word 'Corporation' leading to 'Corp' entity"), # Entity 8255 has CARGO AIRCRAFT LEASING CORP.
    ("James", 16910, "Search for common first name"), # Entity 16910 has CHUOL James Koang
    ("Bank", 306, "Search for common word 'Bank' in entity name"), # Entity 306 has NATIONAL BANK OF CUBA
])
def test_robust_search_cases(capsys, search_term, expected_entity_id, description):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    if not project_id:
        pytest.skip("Skipping integration test: GOOGLE_CLOUD_PROJECT_ID not set")

    dataset_id = "sanctions_data"
    table_id = "sdn_entities"
    threshold = 2
    
    print(f"\nRunning test: {description} | Term: '{search_term}'")

    try:
        search_bq.search_data(project_id, dataset_id, table_id, search_term, threshold)
    except Exception as e:
        pytest.fail(f"Search failed with error: {e}")

    captured = capsys.readouterr()
    
    # Robustly find JSON
    start_idx = captured.out.find('{')
    if start_idx == -1:
         pytest.fail(f"No search results found for '{search_term}'.")
         
    json_content = captured.out[start_idx:]
    
    decoder = json.JSONDecoder()
    pos = 0
    found_entities = []
    
    while pos < len(json_content):
        while pos < len(json_content) and json_content[pos].isspace(): pos += 1
        if pos >= len(json_content): break
        try:
            obj, end_pos = decoder.raw_decode(json_content, pos)
            found_entities.append(obj)
            pos = end_pos
        except json.JSONDecodeError:
            break
            
    found = any(e.get("entity_id") == expected_entity_id for e in found_entities)
    
    assert found, f"Expected to find Entity {expected_entity_id} for '{search_term}' ({description})"
