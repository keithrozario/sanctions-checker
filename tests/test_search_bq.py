import pytest
from unittest.mock import MagicMock, patch
from google.cloud import bigquery
import json
import sys
import os

# Add the load_and_search directory to the path so we can import the module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'load_and_search'))
import search_bq

@pytest.fixture
def mock_bigquery_client():
    with patch('google.cloud.bigquery.Client') as MockClient:
        mock_client = MockClient.return_value
        yield mock_client

def test_search_data_found(mock_bigquery_client, capsys):
    # Mock the query job result
    mock_query_job = MagicMock()
    
    # Use plain dictionaries to mock BigQuery rows. 
    # dict(row) works perfectly on a plain dict.
    
    name_row_data = {"full_name": "Test Entity", "is_primary": True, "type_id": "1"}
    
    entity_data = {
        "entity_id": 123,
        "names": [name_row_data],
        "type": "Entity",
        "programs": ["TEST_PROG"],
        "addresses": [],
        "remarks": None
    }
    
    # Setup the results iterator
    mock_results = MagicMock()
    mock_results.total_rows = 1
    mock_results.__iter__.return_value = iter([entity_data])
    
    mock_query_job.result.return_value = mock_results
    mock_bigquery_client.query.return_value = mock_query_job

    # Run the search function
    search_bq.search_data("test-project", "test-dataset", "test-table", "Test Entity", 2)

    # Capture stdout
    captured = capsys.readouterr()
    
    # Verify output
    assert "Searching for 'Test Entity' with threshold 2..." in captured.out
    
    # The output JSON is printed after the searching message. 
    # It spans multiple lines due to indent=2.
    # We split by the first newline and take the rest.
    output_parts = captured.out.split('\n', 1)
    assert len(output_parts) > 1
    json_str = output_parts[1]
    
    output_json = json.loads(json_str)
    assert output_json["entity_id"] == 123
    assert output_json["names"][0]["full_name"] == "Test Entity"

def test_search_data_not_found(mock_bigquery_client, capsys):
    # Mock empty results
    mock_query_job = MagicMock()
    mock_results = MagicMock()
    mock_results.total_rows = 0
    
    mock_query_job.result.return_value = mock_results
    mock_bigquery_client.query.return_value = mock_query_job

    # Run search
    search_bq.search_data("test-project", "test-dataset", "test-table", "Nonexistent", 2)

    # Capture stdout
    captured = capsys.readouterr()
    
    # Verify output
    assert "No matching entities found." in captured.out

def test_query_construction(mock_bigquery_client):
    # Setup minimal mock results to avoid TypeError
    mock_query_job = MagicMock()
    mock_results = MagicMock()
    mock_results.total_rows = 0
    mock_query_job.result.return_value = mock_results
    mock_bigquery_client.query.return_value = mock_query_job

    # Run search to trigger query construction
    search_bq.search_data("my-project", "my-dataset", "my-table", "SearchTerm", 5)
    
    # Get the call args
    call_args = mock_bigquery_client.query.call_args
    query_str = call_args[0][0]
    job_config = call_args[1]['job_config']
    
    # Verify project/dataset/table replacement
    assert "`my-project.my-dataset.my-table`" in query_str
    
    # Verify parameters
    assert job_config.query_parameters[0].name == "search_term"
    assert job_config.query_parameters[0].value == "SearchTerm"
    assert job_config.query_parameters[1].name == "threshold"
    assert job_config.query_parameters[1].value == 5
