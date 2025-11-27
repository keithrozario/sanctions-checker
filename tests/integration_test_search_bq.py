import pytest
import json
import sys
import os

# Add the load_and_search directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'load_and_search'))
import search_bq

@pytest.mark.integration
def test_integration_search_real_bq(capsys):
    """
    Integration test that connects to the actual BigQuery instance.
    Requires GOOGLE_CLOUD_PROJECT_ID to be set in the environment.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    if not project_id:
        pytest.skip("Skipping integration test: GOOGLE_CLOUD_PROJECT_ID not set")

    dataset_id = "sanctions_data"
    table_id = "sdn_entities"
    # Use a search term close in length to the target "ZAYDAN Muhammad" to pass the length filter optimization
    search_term = "ZAYDAN Muhamad" 
    threshold = 2

    print(f"\nRunning integration test against Project: {project_id}, Dataset: {dataset_id}, Table: {table_id}")

    try:
        # Run the actual search function against the cloud
        search_bq.search_data(project_id, dataset_id, table_id, search_term, threshold)
    except Exception as e:
        pytest.fail(f"Integration test failed with error: {e}")

    # Capture output
    captured = capsys.readouterr()
    
    # Basic assertions
    assert f"Searching for '{search_term}' with threshold {threshold}..." in captured.out
    
    # Robustly find the start of JSON content
    start_idx = captured.out.find('{')
    if start_idx == -1:
         pytest.fail("No JSON start '{' found in output.")
         
    json_content = captured.out[start_idx:]
    
    # Treat the output as a string and use a decoder to read objects one by one.
    decoder = json.JSONDecoder()
    pos = 0
    found_entities = []
    
    while pos < len(json_content):
        # Skip whitespace
        while pos < len(json_content) and json_content[pos].isspace():
            pos += 1
        if pos >= len(json_content):
            break
        
        try:
            obj, end_pos = decoder.raw_decode(json_content, pos)
            found_entities.append(obj)
            pos = end_pos
        except json.JSONDecodeError:
            # If we fail to parse, break
            break
    
    if not found_entities:
         pytest.fail(f"Failed to decode any JSON from output: {json_content[:100]}...")

    # Assert we found the specific entity
    target_id = 2674
    found_target = False
    for entity in found_entities:
        if entity.get("entity_id") == target_id:
            found_target = True
            # Check name
            names = [n["full_name"] for n in entity.get("names", [])]
            assert any("ZAYDAN" in name for name in names), f"Name ZAYDAN not found in entity {target_id}"
            break
    
    assert found_target, f"Target Entity ID {target_id} not found in results."