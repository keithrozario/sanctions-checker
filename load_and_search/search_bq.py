from google.cloud import bigquery
import os
import argparse
import json

def search_data(project_id, dataset_id, table_id, search_term, threshold):
    client = bigquery.Client(project=project_id)
    
    query = f"""
    DECLARE search_term STRING DEFAULT @search_term;
    DECLARE threshold INT64 DEFAULT @threshold;

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
                ABS(LENGTH(n.full_name) - LENGTH(search_term)) <= threshold
                AND EDIT_DISTANCE(UPPER(n.full_name), UPPER(search_term)) <= threshold
            GROUP BY entity_id
            ORDER BY MIN(EDIT_DISTANCE(UPPER(n.full_name), UPPER(search_term))) ASC
            LIMIT 10
        )
    ORDER BY t.entity_id ASC;
    """.format(project_id=project_id, dataset_id=dataset_id, table_id=table_id)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("search_term", "STRING", search_term),
            bigquery.ScalarQueryParameter("threshold", "INT64", threshold),
        ]
    )

    print(f"Searching for '{search_term}' with threshold {threshold}...")
    query_job = client.query(query, job_config=job_config)
    
    results = query_job.result()
    
    if results.total_rows > 0:
        for row in results:
            # Convert BigQuery Row to a dictionary and then to JSON
            entity_dict = dict(row)
            # The 'names' field is a list of Row objects, convert them to dicts too
            entity_dict['names'] = [dict(name_row) for name_row in entity_dict['names']]
            print(json.dumps(entity_dict, indent=2))
    else:
        print("No matching entities found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search BigQuery Sanctions Data.")
    parser.add_argument("search_term", type=str, help="The term to search for.")
    parser.add_argument("--threshold", type=int, default=2, help="Maximum allowed typo distance.")
    args = parser.parse_args()

    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", "your-project-id") 
    DATASET_ID = "sanctions_data"
    TABLE_ID = "sdn_entities"

    if PROJECT_ID == "your-project-id":
        print("Please set GOOGLE_CLOUD_PROJECT_ID env var or edit the script with your Project ID.")
    else:
        search_data(PROJECT_ID, DATASET_ID, TABLE_ID, args.search_term, args.threshold)
