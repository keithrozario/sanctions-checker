from google.cloud import bigquery
import os

def load_data(project_id, dataset_id, table_id, source_file):
    client = bigquery.Client(project=project_id)
    
    table_ref = client.dataset(dataset_id).table(table_id)
    
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False, # We are using a defined schema in Terraform, so the table exists
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, # Overwrite for this setup
    )

    print(f"Starting load job for {source_file} into {dataset_id}.{table_id}...")
    
    with open(source_file, "rb") as source_file_obj:
        job = client.load_table_from_file(
            source_file_obj,
            table_ref,
            job_config=job_config
        )

    job.result()  # Waits for the job to complete.

    print(f"Loaded {job.output_rows} rows into {dataset_id}.{table_id}.")

if __name__ == "__main__":
    # These should ideally come from env vars or args, but for simplicity in this context:
    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID", "your-project-id") 
    DATASET_ID = "sanctions_data"
    TABLE_ID = "sdn_entities"
    SOURCE_FILE = "sdn_entities.jsonl"
    
    if PROJECT_ID == "your-project-id":
        print("Please set GOOGLE_CLOUD_PROJECT_ID env var or edit the script with your Project ID.")
    else:
        load_data(PROJECT_ID, DATASET_ID, TABLE_ID, SOURCE_FILE)
