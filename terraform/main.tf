terraform {
  backend "gcs" {
    bucket = "tf-backends-krozario-gcloud"
    prefix = "terraform/state/sanctions-checker"
  }
  required_providers {
    google-beta = {
      source = "hashicorp/google-beta"
      version = "7.12.0"
    }
    google = {
      source = "hashicorp/google"
      version = "7.12.0"
    }
  }
}

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

  schema = file("../queries/bq_schema.json")
  
  deletion_protection = false # For ease of development/testing
}
