provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id                  = var.dataset_id
  friendly_name               = "Sanctions List Dataset"
  description                 = "Dataset containing parsed OFAC SDN entities"
  location                    = var.region
  default_table_expiration_ms = null
}

resource "google_bigquery_table" "table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = var.table_id

  schema = file("../bq_schema.json")
  
  deletion_protection = false # For ease of development/testing
}
