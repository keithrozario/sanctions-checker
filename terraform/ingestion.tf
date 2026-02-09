# Enable necessary APIs
resource "google_project_service" "cloudfunctions" {
  service = "cloudfunctions.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  service = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run" {
  service = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudscheduler" {
  service = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

# Bucket for Cloud Function Source Code
resource "google_storage_bucket" "function_source_bucket" {
  name                        = "${var.project_id}-gcf-source"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# Zip the source code
data "archive_file" "download_sdn_zip" {
  type        = "zip"
  source_dir  = "../download_sdn"
  output_path = "/tmp/download_sdn.zip"
}

# Upload the zip to the source bucket
resource "google_storage_bucket_object" "download_sdn_zip" {
  name   = "download_sdn.${data.archive_file.download_sdn_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name
  source = data.archive_file.download_sdn_zip.output_path
}

# -------------------------------------------------------------------------
# Service Accounts
# -------------------------------------------------------------------------

# 1. Build Service Account (Existing)
resource "google_service_account" "cf_build_sa" {
  account_id   = "cf-build-sa"
  display_name = "Cloud Function Build Service Account"
}

# 2. Runtime Service Account (New - for running the function)
resource "google_service_account" "cf_runtime_sa" {
  account_id   = "sdn-function-sa"
  display_name = "SDN Download Function Runtime SA"
}

# -------------------------------------------------------------------------
# IAM for Build SA
# -------------------------------------------------------------------------
locals {
  build_sa_roles = [
    "roles/logging.logWriter",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.builder",
    "roles/storage.admin"
  ]
}

resource "google_project_iam_member" "build_sa_roles" {
  for_each = toset(local.build_sa_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.cf_build_sa.email}"
}

resource "google_storage_bucket_iam_member" "build_sa_source_bucket_access" {
  bucket = google_storage_bucket.function_source_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.cf_build_sa.email}"
}

# -------------------------------------------------------------------------
# IAM for Runtime SA (The Function Identity)
# -------------------------------------------------------------------------

# 1. Write access to the Data/Temp Bucket (to upload XML)
resource "google_storage_bucket_iam_member" "runtime_sa_data_bucket_access" {
  bucket = google_storage_bucket.dataflow_temp_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cf_runtime_sa.email}"
}

# 2. Dataflow Admin (to trigger jobs in future)
resource "google_project_iam_member" "runtime_sa_dataflow_admin" {
  project = var.project_id
  role    = "roles/dataflow.admin"
  member  = "serviceAccount:${google_service_account.cf_runtime_sa.email}"
}

# 3. Service Account User (required to assign workers to Dataflow jobs)
resource "google_service_account_iam_member" "runtime_sa_user_self" {
  service_account_id = google_service_account.cf_runtime_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cf_runtime_sa.email}"
}

# 4. Dataflow Worker (Compute) SA usage? 
# Usually Dataflow uses the Compute Engine Default SA or a user-managed worker SA.
# If using Compute Default, we need permission to act as it.
# For simplicity, we assume the job will launch with default worker SA.
resource "google_project_iam_member" "runtime_sa_act_as_compute" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cf_runtime_sa.email}"
}


# -------------------------------------------------------------------------
# Cloud Function Deployment
# -------------------------------------------------------------------------

resource "google_cloudfunctions2_function" "download_sdn_function" {
  name        = "download-sdn-xml"
  location    = var.region
  description = "Downloads OFAC SDN XML to GCS"

  build_config {
    runtime     = "python312"
    entry_point = "download_sdn_list"
    service_account = google_service_account.cf_build_sa.id # Build SA
    
    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.download_sdn_zip.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "512M"
    timeout_seconds    = 300
    
    # Use the new Dedicated Runtime SA
    service_account_email = google_service_account.cf_runtime_sa.email
    
    environment_variables = {
      BUCKET_NAME = google_storage_bucket.dataflow_temp_bucket.name
      PROJECT_ID  = var.project_id
      REGION      = var.region
    }
  }

  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.cloudbuild,
    google_project_iam_member.build_sa_roles,
    google_storage_bucket_iam_member.build_sa_source_bucket_access,
    google_storage_bucket_iam_member.runtime_sa_data_bucket_access
  ]
}

# -------------------------------------------------------------------------
# Cloud Scheduler
# -------------------------------------------------------------------------

resource "google_service_account" "scheduler_sa" {
  account_id   = "sdn-scheduler-sa"
  display_name = "Cloud Scheduler Service Account for SDN Download"
}

# Commented out scheduler job
# resource "google_cloud_scheduler_job" "download_job" { ... }