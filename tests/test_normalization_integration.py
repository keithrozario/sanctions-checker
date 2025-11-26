import pytest
import sys
import os
import json

# Add the load_and_search directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'load_and_search'))
import search_bq

@pytest.mark.integration
def test_search_normalization_abbreviations(capsys):
    """
    Integration test to verify that common corporate abbreviations are handled correctly.
    Target Entity: 49843
    Name in DB: "Ascent General Insurance Company"
    Search Term: "Ascent General Insurance Co"
    
    Without normalization, this fails because 'Company' vs 'Co' has an edit distance of 5.
    With normalization, 'COMPANY' -> 'CO', resulting in a match.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    if not project_id:
        pytest.skip("Skipping integration test: GOOGLE_CLOUD_PROJECT_ID not set")

    dataset_id = "sanctions_data"
    table_id = "sdn_entities"
    
    # Search using abbreviation 'Co' instead of 'Company'
    search_term = "Ascent General Insurance Co"
    threshold = 2

    print(f"\nRunning normalization test for term: '{search_term}'")

    try:
        search_bq.search_data(project_id, dataset_id, table_id, search_term, threshold)
    except Exception as e:
        pytest.fail(f"Search failed with error: {e}")

    captured = capsys.readouterr()
    
    # Robustly find JSON
    start_idx = captured.out.find('{')
    if start_idx == -1:
         pytest.fail("No search results found (JSON start '{' missing).")
         
    json_content = captured.out[start_idx:]
    
    decoder = json.JSONDecoder()
    pos = 0
    found_entities = []
    
    while pos < len(json_content):
        while pos < len(json_content) and json_content[pos].isspace():
            pos += 1
        if pos >= len(json_content): break
        try:
            obj, end_pos = decoder.raw_decode(json_content, pos)
            found_entities.append(obj)
            pos = end_pos
        except json.JSONDecodeError:
            break
            
    target_id = 49843
    found = any(e.get("entity_id") == target_id for e in found_entities)
    
    assert found, f"Expected to find Entity {target_id} ('Ascent General Insurance Company') when searching for '{search_term}'"
