import os
import argparse
import json
from google.cloud import bigquery
from normalization_logic import normalize_name

def search_data(project_id, dataset_id, table_id, search_term, threshold):
    client = bigquery.Client(project=project_id)
    
    # Normalize the search term in Python
    normalized_search_term = normalize_name(search_term)
    # Regex pattern for exact word match on original name (case-insensitive)
    regex_pattern = r'(?i)\b{}\b'.format(search_term.upper() if search_term else "") # Ensure uppercase for regex match

    query = f"""
    DECLARE search_term STRING DEFAULT @search_term;
    DECLARE normalized_search_term STRING DEFAULT @normalized_search_term;
    DECLARE threshold INT64 DEFAULT @threshold;
    DECLARE regex_pattern STRING DEFAULT @regex_pattern;
    DECLARE normalized_regex_pattern STRING DEFAULT @normalized_regex_pattern;

    SELECT 
        t.*
    FROM 
        `{{project_id}}.{dataset_id}.{table_id}` AS t
    WHERE
        t.entity_id IN (
            SELECT 
                entity_id
            FROM 
                `{{project_id}}.{dataset_id}.{table_id}`,
                UNNEST(names) AS n
            WHERE 
                (
                    -- Normalized Fuzzy Match
                    EDIT_DISTANCE(n.normalized_name, normalized_search_term) <= threshold
                )
                OR
                (
                    -- Exact Word Match (Substring) on Original Name
                    REGEXP_CONTAINS(n.full_name, regex_pattern)
                )
                OR
                (
                    -- Exact Word Match (Substring) on Normalized Name
                    REGEXP_CONTAINS(n.normalized_name, normalized_regex_pattern)
                )
            GROUP BY entity_id
            ORDER BY 
                -- Prioritize Exact Matches, then Normalized Word Matches, then Normalized Fuzzy Matches
                MIN(
                    CASE 
                        WHEN REGEXP_CONTAINS(n.full_name, regex_pattern) THEN 0
                        WHEN REGEXP_CONTAINS(n.normalized_name, normalized_regex_pattern) THEN 0
                        WHEN EDIT_DISTANCE(n.normalized_name, normalized_search_term) <= threshold 
                             THEN EDIT_DISTANCE(n.normalized_name, normalized_search_term)
                        ELSE 100
                    END
                ) ASC
            -- LIMIT 10 -- Temporarily removed for debugging
        )
    ORDER BY t.entity_id ASC;
    """.format(project_id=project_id, dataset_id=dataset_id, table_id=table_id)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("search_term", "STRING", search_term),
            bigquery.ScalarQueryParameter("normalized_search_term", "STRING", normalized_search_term),
            bigquery.ScalarQueryParameter("threshold", "INT64", threshold),
            bigquery.ScalarQueryParameter("regex_pattern", "STRING", regex_pattern),
            bigquery.ScalarQueryParameter("normalized_regex_pattern", "STRING", r'\b' + normalized_search_term + r'\b'), # Pass the fully constructed regex for normalized search
        ]
    )

    print(f"Searching for '{search_term}' (Normalized: '{normalized_search_term}') with threshold {threshold}...")
    query_job = client.query(query, job_config=job_config)
    
    results = query_job.result()
    
    if results.total_rows > 0:
        for row in results:
            # Convert BigQuery Row to a dictionary and then to JSON
            entity_dict = dict(row)
            # The 'names' field is a list of Row objects, convert them to dicts too
            entity_dict['names'] = [dict(name_row) for name_row in entity_dict['names']]
            
            # The 'addresses' field is also a list of Row objects
            if 'addresses' in entity_dict and entity_dict['addresses']:
                entity_dict['addresses'] = [dict(addr_row) for addr_row in entity_dict['addresses']]

            print(json.dumps(entity_dict, indent=2))
    else:
        print("No matching entities found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search BigQuery Sanctions Data.")
    parser.add_argument("search_term", type=str, help="The term to search for.")
    parser.add_argument("--threshold", type=int, default=2, help="Maximum allowed typo distance.")
    parser.add_argument("--output_table", type=str, default="sanctions_data.sdn_entities", 
                        help="Output BigQuery table to search (format: DATASET.TABLE).")
    args = parser.parse_args()

    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", "your-project-id") 
    
    # Split the output_table argument into dataset_id and table_id
    try:
        DATASET_ID, TABLE_ID = args.output_table.split('.')
    except ValueError:
        print("Error: --output_table must be in the format DATASET.TABLE")
        sys.exit(1)

    if PROJECT_ID == "your-project-id":
        print("Please set GOOGLE_CLOUD_PROJECT_ID env var or edit the script with your Project ID.")
    else:
        search_data(PROJECT_ID, DATASET_ID, TABLE_ID, args.search_term, args.threshold)
