# Project: Sanctions Checker

## General Instructions:

- Use Python for any application level coding necessary
- Python code for parsing should be stored in a `parsing` directory
- Use BigQuery to store and retrieve the data
- use Dataflow to load data into BigQuery
- Use Terraform for creating infrastructure (BQ, GCS bucket, etc)
- Use a `parse` folder for the parsing logic, use `terraform` folder for the terraform scripts

## Coding Style:

- Use `black` for linting python code
- use `tf fmt` for Terraform modules

## Regarding Dependencies:

- use `uv add` to add additional python libraries
- assume you already in a virtual environment
- Always ask the user before running `uv add`
- Do not use `gcloud` commands, any infrastructure on GCP should be provisioned or modified via Terraform


