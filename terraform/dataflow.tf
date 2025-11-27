variable "temp_bucket_name" {
  description = "The name of the GCS bucket for Dataflow temporary files"
  type        = string
  default     = "sanctions-dataflow-temp-bucket-krozario" # Ensuring uniqueness
}

resource "google_storage_bucket" "dataflow_temp_bucket" {
  name          = var.temp_bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}
