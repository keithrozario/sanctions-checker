# Sanctions Data Processing and Querying Plan

This document outlines the end-to-end workflow to process OFAC SDN Advanced XML data, provision BigQuery infrastructure using Terraform, and interact with the data via Python for loading and fuzzy searching.

## I. Data Preparation (Already Executed)

### 1. Data Parsing
**Objective:** Convert the complex, nested XML into a flat, newline-delimited JSON (JSONL) format suitable for BigQuery, while preserving multiple aliases per entity.

*   **Source File:** `docs/sdn_advanced.xml`
*   **Script:** `parse_to_jsonl.py`
*   **Key Logic:**
    *   Iteratively parses the XML to handle large file sizes (streaming).
    *   Extracts stable `FixedRef` as `entity_id`.
    *   Concatenates multiple `DocumentedNamePart` elements to form a complete `full_name` (e.g., "Last Name First Name").
    *   Captures all aliases (A.K.A, F.K.A, etc.) for each entity.
*   **Output:** `sdn_entities.jsonl`

### 2. BigQuery Schema Definition
**Objective:** Define a schema that supports nested repeated fields for aliases to avoid data duplication.

*   **File:** `bq_schema.json`
*   **Structure:**
    ```json
    [
      { "name": "entity_id", "type": "INTEGER", "mode": "REQUIRED" },
      {
        "name": "names",
        "type": "RECORD",
        "mode": "REPEATED",
        "fields": [
          { "name": "full_name", "type": "STRING", "mode": "REQUIRED" },
          { "name": "is_primary", "type": "BOOLEAN", "mode": "NULLABLE" },
          { "name": "type_id", "type": "STRING", "mode": "NULLABLE" }
        ]
      }
    ]
    ```

## II. Execution Plan

### 1. Prerequisites & Setup

*   **Google Cloud Project:** Ensure you have an active Google Cloud project.
*   **Permissions:** Your GCP user or service account needs permissions to create BigQuery datasets and tables, and to load/query data.
*   **Tools:**
    *   **Python 3.x:** Installed on your system.
    *   **Terraform CLI:** [Install Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli).
    *   **Google Cloud SDK (gcloud CLI):** [Install gcloud](https://cloud.cloud.google.com/sdk/docs/install).

### 2. Python Dependencies (Manual Installation)

Due to the `pyproject.toml` issue in the repository, please install the required libraries manually:

```bash
uv pip install google-cloud-bigquery db-dtypes
# OR if you prefer pip directly:
# pip install google-cloud-bigquery db-dtypes
```

### 3. Google Cloud Authentication

Before running Terraform or Python scripts, authenticate your `gcloud` CLI:

```bash
gcloud auth application-default login
```
This will open a browser for you to log in. Ensure you select the correct Google Cloud project.

### 4. Terraform: Create BigQuery Dataset and Table

I have created the necessary Terraform configuration files in the `terraform/` directory (`main.tf`, `variables.tf`) and your `bq_schema.json` is at the project root.

*   **Navigate to the Terraform directory:**
    ```bash
    cd terraform
    ```
*   **Initialize Terraform:** This prepares Terraform to build your infrastructure.
    ```bash
    terraform init
    ```
*   **Set your Google Cloud Project ID:**
    You must set the `TF_VAR_project_id` environment variable to your Google Cloud Project ID.
    ```bash
    export TF_VAR_project_id="YOUR_GOOGLE_CLOUD_PROJECT_ID"
    # Example: export TF_VAR_project_id="my-sanctions-project-12345"
    ```
    *(Optional: You can also specify other variables like `region`, `dataset_id`, `table_id` if you want to override the defaults set in `variables.tf`)*
    ```bash
    export TF_VAR_region="us-central1" # or your preferred region
    ```
*   **Review the plan:** This shows what Terraform will create/modify.
    ```bash
    terraform plan
    ```
*   **Apply the changes:** This creates the BigQuery dataset and table.
    ```bash
    terraform apply
    ```
    Type `yes` when prompted to confirm.
*   **Return to the project root:**
    ```bash
    cd ..
    ```

### 5. Python: Load Data into BigQuery

I have created `load_to_bq.py` which will upload your `sdn_entities.jsonl` data.

*   **Set your Google Cloud Project ID:**
    Ensure your `GOOGLE_CLOUD_PROJECT_ID` environment variable is set. This is used by the Python script to know which project to target.
    ```bash
    export GOOGLE_CLOUD_PROJECT_ID="YOUR_GOOGLE_CLOUD_PROJECT_ID"
    # Example: export GOOGLE_CLOUD_PROJECT_ID="my-sanctions-project-12345"
    ```
    *(Make sure this matches the `TF_VAR_project_id` you used for Terraform)*
*   **Run the data loading script:**
    ```bash
    python3 load_to_bq.py
    ```

### 6. Python: Query Data from BigQuery

I have created `search_bq.py` which allows you to perform fuzzy searches on the loaded data.

*   **Ensure `GOOGLE_CLOUD_PROJECT_ID` is still set** (from the previous step).
*   **Run the search script:**
    ```bash
    python3 search_bq.py "AEROCARIBAN" --threshold 2
    # You can change "AEROCARIBAN" to your desired search term and adjust the --threshold
    ```