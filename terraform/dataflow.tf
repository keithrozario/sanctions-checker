variable "temp_bucket_name" {
  description = "The name of the GCS bucket for Dataflow temporary files"
  type        = string
  default     = "sanctions-dataflow-temp-bucket-krozario-v2" # Ensuring uniqueness
}

resource "google_storage_bucket" "dataflow_temp_bucket" {
  name          = var.temp_bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

resource "google_bigquery_table" "address_cache" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "address_cache"
  
  schema = <<EOF
[
  {
    "name": "address_hash",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "SHA256 hash of the normalized raw address"
  },
  {
    "name": "raw_address",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "enriched_data",
    "type": "JSON",
    "mode": "NULLABLE",
    "description": "JSON object from Address Validation API"
  },
  {
    "name": "updated_at",
    "type": "TIMESTAMP",
    "mode": "NULLABLE"
  }
]
EOF

  deletion_protection = false
}

# Retrieve project information to get the project number
data "google_project" "project" {
}

# Grant Dataflow Service Agent access to the temp bucket
resource "google_storage_bucket_iam_member" "dataflow_service_agent_bucket_access" {
  bucket = google_storage_bucket.dataflow_temp_bucket.name
  role   = "roles/storage.admin"
  member = "serviceAccount:service-${data.google_project.project.number}@dataflow-service-producer-prod.iam.gserviceaccount.com"
}

# -------------------------------------------------------------------------
# VPC Network for Dataflow
# -------------------------------------------------------------------------

resource "google_compute_network" "dataflow_network" {
  name                    = "dataflow-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "dataflow_subnet" {
  name                     = "dataflow-subnet"
  ip_cidr_range            = "10.0.0.0/24"
  region                   = var.region
  network                  = google_compute_network.dataflow_network.id
  private_ip_google_access = true
}

# Allow internal communication between Dataflow workers
resource "google_compute_firewall" "dataflow_internal" {
  name    = "dataflow-internal"
  network = google_compute_network.dataflow_network.name

  allow {
    protocol = "tcp"
    ports    = ["12345-12346"]
  }

  source_tags = ["dataflow"]
  target_tags = ["dataflow"]
}
