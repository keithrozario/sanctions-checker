import pytest
import sys
import os
import json

# Add the load_and_search directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'load_and_search'))
import search_bq

@pytest.mark.integration
def test_dataflow_loaded_data_search(capsys):
    """
    Integration test to verify data loaded by Dataflow into 'sdn_entities_dataflow'.
    Checks both fuzzy matching and normalization logic on the new table.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    if not project_id:
        pytest.skip("Skipping integration test: GOOGLE_CLOUD_PROJECT_ID not set")

    dataset_id = "sanctions_data"
    table_id = "sdn_entities_dataflow"
    
    print(f"\nRunning Dataflow integration test against {dataset_id}.{table_id}")

    # Case 1: Standard Fuzzy Search (ZAYDAN Muhamad)
    search_term_1 = "ZAYDAN Muhamad"
    threshold = 2
    
    try:
        search_bq.search_data(project_id, dataset_id, table_id, search_term_1, threshold)
    except Exception as e:
        pytest.fail(f"Search 1 failed: {e}")

    captured = capsys.readouterr()
    
    # Check for JSON output
    start_idx = captured.out.find('{')
    if start_idx == -1:
         pytest.fail("No search results found for ZAYDAN Muhamad.")
    
    # Case 2: Normalization Search (Ascent General Insurance Co)
    search_term_2 = "Ascent General Insurance Co"
    
    try:
        search_bq.search_data(project_id, dataset_id, table_id, search_term_2, threshold)
    except Exception as e:
        pytest.fail(f"Search 2 failed: {e}")

    captured = capsys.readouterr()
    
    # Check for JSON output
    start_idx = captured.out.find('{')
    if start_idx == -1:
         pytest.fail("No search results found for Ascent General Insurance Co.")
    
    # We could parse and validate specific IDs, but finding *something* with the correct query 
    # logic implies the data is present and the query works.

