import functions_framework
import requests
from google.cloud import storage
import googleapiclient.discovery
import os
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)

@functions_framework.http
def download_sdn_list(request):
    """
    Downloads the OFAC SDN Advanced XML file, uploads to GCS, and triggers Dataflow.
    """
    # Configuration
    source_url = "https://sanctionslistservice.ofac.treas.gov/api/publicationpreview/exports/sdn_advanced.xml"
    bucket_name = os.environ.get("BUCKET_NAME")
    project_id = os.environ.get("PROJECT_ID")
    region = os.environ.get("REGION")
    
    destination_blob_name = "sdn_advanced.xml"

    if not all([bucket_name, project_id, region]):
        logging.error("Missing configuration environment variables.")
        return "Internal Server Error: Missing config", 500

    logging.info(f"Starting download from {source_url} to gs://{bucket_name}/{destination_blob_name}")

    try:
        # 1. Download and Upload
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        with requests.get(source_url, stream=True) as r:
            r.raise_for_status()
            
            tmp_file_path = "/tmp/sdn_advanced.xml"
            with open(tmp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logging.info("Download to local temp complete. Uploading to GCS...")
            blob.upload_from_filename(tmp_file_path)
            os.remove(tmp_file_path)
            logging.info("Upload complete.")

        # 2. Trigger Dataflow
        logging.info("Triggering Dataflow Flex Template...")
        launch_dataflow_job(project_id, region, bucket_name, destination_blob_name)

        return f"Successfully processed and triggered job.", 200

    except Exception as e:
        logging.exception("Failed to process SDN list.")
        return f"Error: {str(e)}", 500

def launch_dataflow_job(project_id, region, bucket_name, input_blob_name):
    # Construct paths
    input_gcs_path = f"gs://{bucket_name}/{input_blob_name}"
    output_table = f"{project_id}:sanctions_data.sdn_entities"
    template_spec = f"gs://{bucket_name}/templates/flex-spec.json"
    temp_location = f"gs://{bucket_name}/tmp"
    staging_location = f"gs://{bucket_name}/staging"
    subnetwork_url = f"https://www.googleapis.com/compute/v1/projects/{project_id}/regions/{region}/subnetworks/dataflow-subnet"
    
    job_name = f"sanctions-ingest-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Build Dataflow service
    dataflow = googleapiclient.discovery.build('dataflow', 'v1b3', cache_discovery=False)

    request_body = {
        "launchParameter": {
            "jobName": job_name,
            "parameters": {
                "input_file": input_gcs_path,
                "output_table": output_table
            },
            "environment": {
                "tempLocation": temp_location,
                "stagingLocation": staging_location,
                "subnetwork": subnetwork_url,
                "ipConfiguration": "WORKER_IP_PRIVATE"
            },
            "containerSpecGcsPath": template_spec
        }
    }

    request = dataflow.projects().locations().flexTemplates().launch(
        projectId=project_id,
        location=region,
        body=request_body
    )

    response = request.execute()
    logging.info(f"Dataflow job triggered: {response.get('job', {}).get('id')}")
    return response