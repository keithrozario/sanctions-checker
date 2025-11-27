# Queries and Schema Definitions

This directory contains SQL queries and schema definitions for the Sanctions Data project.

## Files

*   **`bq_schema.json`**: The Single Source of Truth for the BigQuery table schema.
    *   Used by **Terraform** to provision the table with the correct columns and types.
    *   Used by **Dataflow** (`dataflow_pipeline.py`) to ensure data is loaded correctly.
    *   Defines the nested and repeated structure for entities, including the `names` record (with `normalized_name`) and `addresses`.

*   **`fuzzy_search.sql`**: A reference SQL query demonstrating the project's advanced search logic.
    *   Shows how to use `EDIT_DISTANCE` for fuzzy matching.
    *   Shows how to use `REGEXP_CONTAINS` for word-boundary matching.
    *   Serve as a template for the dynamic queries constructed in `search_bq.py`.
