# Enable Artifact Registry API
resource "google_project_service" "artifactregistry" {
  service = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Create Artifact Registry Repository for Flex Templates
resource "google_artifact_registry_repository" "dataflow_repo" {
  location      = var.region
  repository_id = "dataflow-templates"
  description   = "Docker repository for Dataflow Flex Templates"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}

# Retrieve project info to construct email
data "google_project" "current_project" {}

# -------------------------------------------------------------------------
# IAM for Cloud Build (Global Service Account)
# -------------------------------------------------------------------------
# We need to ensure the default Cloud Build Service Account has permissions
# to push images to Artifact Registry and write to GCS.

locals {
  cloudbuild_email = "${data.google_project.current_project.number}@cloudbuild.gserviceaccount.com"
}

# Grant Artifact Registry Writer
resource "google_project_iam_member" "cloudbuild_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${local.cloudbuild_email}"
}

# Grant Storage Admin (for staging bucket and template spec)
resource "google_project_iam_member" "cloudbuild_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${local.cloudbuild_email}"
}

# -------------------------------------------------------------------------
# IAM for Compute Engine Default SA (Dataflow Worker SA)
# -------------------------------------------------------------------------
# This SA is used by Dataflow workers by default if not specified.

# Grant Artifact Registry Reader (to pull the Flex Template image)
resource "google_project_iam_member" "compute_sa_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${data.google_project.current_project.number}-compute@developer.gserviceaccount.com"
}

# Grant Storage Admin on the Dataflow temp bucket (for staging/temp files)
resource "google_storage_bucket_iam_member" "compute_sa_dataflow_bucket_admin" {
  bucket = google_storage_bucket.dataflow_temp_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_project.current_project.number}-compute@developer.gserviceaccount.com"
}

# Grant BigQuery Data Editor on the dataset
resource "google_bigquery_dataset_iam_member" "compute_sa_bq_dataeditor" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${data.google_project.current_project.number}-compute@developer.gserviceaccount.com"
}

# Grant Service Usage Consumer (for Maps API and other services)
resource "google_project_iam_member" "compute_sa_service_consumer" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${data.google_project.current_project.number}-compute@developer.gserviceaccount.com"
}
