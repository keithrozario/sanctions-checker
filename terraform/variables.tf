variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
  default = "agentspace-krozario"
}

variable "region" {
  description = "The region for BigQuery resources"
  type        = string
  default     = "asia-southeast1"
}

variable "dataset_id" {
  description = "The ID of the BigQuery dataset"
  type        = string
  default     = "sanctions_data"
}

variable "table_id" {
  description = "The ID of the BigQuery table"
  type        = string
  default     = "sdn_entities"
}
