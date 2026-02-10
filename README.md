# Sanctions Checker CLI & Data Pipeline

This project implements a serverless, automated ETL pipeline to ingest OFAC SDN (Specially Designated Nationals) sanctions data, enrich it with ISO country codes, and load it into Google BigQuery for analysis.

## Project Overview

The system downloads the official OFAC SDN XML file, parses the complex XML structure, extracts entity details (names, addresses, programs), enriches address data with standardized ISO 3166-1 alpha-2 country codes, and stores the structured data in BigQuery.

### Key Features
*   **Serverless Ingestion:** Automated via Google Cloud Functions.
*   **Scalable Processing:** Uses Dataflow (Apache Beam) on Google Cloud Platform.
*   **Secure Environment:** Runs in a private VPC with Private Google Access; no public internet access for workers.
*   **Infrastructure as Code:** Fully provisioned using Terraform.
*   **Data Enrichment:** Automatically maps country names to ISO alpha-2 codes (e.g., "Cuba" -> "CU").

## Architecture

1.  **Trigger:** A Cloud Function (`download-sdn-xml`) is triggered (e.g., via HTTP or Cloud Scheduler).
2.  **Download:** The function downloads the `sdn_advanced.xml` file from OFAC and uploads it to a Google Cloud Storage (GCS) bucket.
3.  **Process:** The function triggers a Dataflow Flex Template job.
4.  **ETL Pipeline (Dataflow):**
    *   **Read:** Reads the XML file from GCS.
    *   **Parse:** Parses the XML using Python's `ElementTree`, extracting entities, aliases, and addresses.
    *   **Convert:** Maps textual country names to 2-letter ISO codes (e.g., "Russia" -> "RU") using the XML's internal reference data.
    *   **Write:** Loads the transformed data into the BigQuery table `sanctions_data.sdn_entities`.
5.  **Storage:** Data is stored in BigQuery with a nested schema (arrays for names and addresses).

## Infrastructure

The infrastructure is managed via Terraform in the `terraform/` directory:
*   **BigQuery:** Dataset `sanctions_data` and table `sdn_entities`.
*   **GCS:** Buckets for storing the raw XML, Dataflow templates, and staging files.
*   **Networking:** Custom VPC (`dataflow-network`) and Subnet (`dataflow-subnet`) with Private Google Access.
*   **IAM:** Service accounts for Cloud Build (`cf-build-sa`) and Runtime (`sdn-function-sa`) with least-privilege roles.
*   **Cloud Function:** Deploys the Python function to trigger the pipeline.

## Repository Structure

```
/
├── download_sdn/           # Cloud Function source code
│   ├── main.py             # Function logic (download & trigger)
│   └── requirements.txt    # Function dependencies
├── load_and_search/        # Dataflow Pipeline source code
│   ├── dataflow_pipeline.py# Main Beam pipeline logic
│   ├── normalization_logic.py # Name normalization utilities
│   ├── Dockerfile          # Flex Template container image definition
│   └── metadata.json       # Flex Template metadata
├── queries/                # BigQuery schemas and SQL queries
│   └── bq_schema.json      # JSON schema for sdn_entities table
├── terraform/              # Infrastructure definitions
│   ├── main.tf             # Provider config
│   ├── dataflow.tf         # Network, GCS, BigQuery resources
│   ├── ingestion.tf        # Cloud Function & IAM resources
│   └── variables.tf        # Variable definitions
└── tests/                  # Test scripts
    └── verify_loaded_data.py # Script to verify BQ data integrity
```

## Deployment

### Prerequisites
*   Google Cloud SDK (`gcloud`) installed and authenticated.
*   Terraform installed.
*   Python 3.11+.

### 1. Provision Infrastructure
```bash
cd terraform
terraform init
terraform apply
```

### 2. Build Dataflow Flex Template
The pipeline is containerized. Build and push the image to Artifact Registry:
```bash
gcloud builds submit --config cloudbuild.yaml --project <PROJECT_ID>
```
Update the Flex Template spec:
```bash
gcloud dataflow flex-template build gs://<BUCKET>/templates/flex-spec.json 
    --image "<REGION>-docker.pkg.dev/<PROJECT>/dataflow-templates/sanctions-pipeline:latest" 
    --sdk-language "PYTHON" 
    --metadata-file "load_and_search/metadata.json" 
    --project "<PROJECT_ID>"
```

### 3. Deploy Cloud Function
The Terraform step usually handles this, but you can manually redeploy if source changes:
```bash
cd download_sdn
gcloud functions deploy download-sdn-xml ...
```

## Usage

### Triggering the Pipeline
Invoke the Cloud Function to start the ingestion process:
```bash
curl -X GET "https://<REGION>-<PROJECT>.cloudfunctions.net/download-sdn-xml" 
    -H "Authorization: bearer $(gcloud auth print-identity-token)"
```

### Verifying Data
Run the verification script to check if data is loaded correctly:
```bash
python3 tests/verify_loaded_data.py
```

### Querying Data
You can query the data directly in BigQuery. Example: Find all entities related to "Putin":
```sql
SELECT
  t.entity_id,
  n.full_name,
  a.country,
  a.country_iso2
FROM
  `sanctions_data.sdn_entities` AS t,
  UNNEST(t.names) AS n,
  UNNEST(t.addresses) AS a
WHERE
  LOWER(n.full_name) LIKE '%putin%'
```

## Schema Details
The `sdn_entities` table uses a nested schema:
*   `entity_id`: Integer
*   `names`: Array of Records (full_name, normalized_name, type)
*   `addresses`: Array of Records (address_line, city, country, postal_code, **country_iso2**)
*   `programs`: Array of Strings (sanctions programs)
