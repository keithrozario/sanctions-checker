# Sanctions Data ETL Pipeline & Search Architecture

This document outlines the architecture and workflow for the Sanctions Data Processing system. The system is designed to parse large XML sanctions lists (OFAC SDN), load them into BigQuery, and provide a robust, typo-tolerant search interface.

## 1. Architecture Overview

The solution leverages Google Cloud Platform (GCP) services for scalability and performance.

### Key Components:
*   **Source Data:** OFAC SDN Advanced XML file (`sdn_advanced.xml`).
*   **Processing Engine:** 
    *   **Python (Local/Direct):** Initial parsing scripts for development and smaller loads.
    *   **Google Cloud Dataflow (Apache Beam):** Scalable ETL pipeline for processing large XML files in a distributed manner.
*   **Storage:** Google BigQuery. Data is stored in a structured, denormalized format optimized for search.
*   **Infrastructure:** Terraform is used to provision all GCP resources (BigQuery datasets, tables, GCS buckets).
*   **Search Interface:** A Python-based CLI tool (`search_bq.py`) that executes sophisticated SQL queries for fuzzy matching and normalization.

## 2. ETL Pipeline (Extract, Transform, Load)

We support two methods for loading data: a lightweight local script and a scalable Dataflow pipeline.

### Method A: Scalable Dataflow Pipeline (Recommended)
**Script:** `dataflow_pipeline.py`

1.  **Extract (Read):** 
    *   Reads the XML file from Google Cloud Storage (or local file system for testing).
    *   Currently reads the file as a single blob (suitable for ~100MB files). For significantly larger files, a custom `SplittableDoFn` or XML source would be implemented.
2.  **Transform (Parse):**
    *   Uses `xml.etree.ElementTree` within a custom Beam `DoFn` (`ParseSanctionsXmlDoFn`).
    *   **Logic:**
        *   Parses distinct entities (`DistinctParty`).
        *   Extracts and consolidates all aliases/names.
        *   Resolves references (Countries, Locations, Sanctions Programs).
        *   Constructs a rich JSON object for each entity containing: `entity_id`, `names` (list), `type`, `programs`, `addresses`, and `remarks`.
3.  **Load (Write):**
    *   Writes the processed JSON objects directly to a BigQuery table (e.g., `sanctions_data.sdn_entities_dataflow`) using `WriteToBigQuery`.
    *   Automatically handles schema validation against `bq_schema.json`.

### Method B: Local Python Loader (Development)
**Scripts:** `load_and_search/parse_to_jsonl.py` -> `load_and_search/load_to_bq.py`

1.  **Parse:** Streams the XML file locally, extracts entities, and writes them to a newline-delimited JSON file (`sdn_entities.jsonl`).
2.  **Load:** Uses the BigQuery Python Client to upload the JSONL file to BigQuery via a Load Job.

## 3. BigQuery Schema

The BigQuery table uses a nested and repeated schema to efficiently store the complex entity data without excessive duplication.

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
  },
  { "name": "type", "type": "STRING", "mode": "NULLABLE" },
  { "name": "programs", "type": "STRING", "mode": "REPEATED" },
  { "name": "addresses", "type": "RECORD", "mode": "REPEATED", ... },
  { "name": "remarks", "type": "STRING", "mode": "NULLABLE" }
]
```

## 4. Search Logic & Normalization

The core value of this solution is its ability to find entities despite typos, variations, and abbreviations. This logic is embedded in the SQL query constructed by `search_bq.py`.

### Search Features:
1.  **Fuzzy Matching:** Uses `EDIT_DISTANCE()` (Levenshtein distance) to find names that are character-wise similar (e.g., "ZAYDAN" vs "ZAIDAN").
2.  **Substring/Word Matching:** Uses `REGEXP_CONTAINS()` with word boundaries (`\b`) to find search terms that appear as distinct words within longer names (e.g., searching "Ali" finds "Muhammad Ali").
3.  **Intelligent Normalization:** A custom SQL User-Defined Function (UDF) `NormalizeEntityName` standardizes names on-the-fly before comparison.
    *   **Removes Punctuation:** "Co." -> "CO"
    *   **Standardizes Suffixes:**
        *   `LIMITED` -> `LTD`
        *   `PRIVATE` -> `PVT`
        *   `CORPORATION` -> `CORP`
        *   `INCORPORATED` -> `INC`
        *   `COMPANY` -> `CO`
    *   **Result:** Searching for **"Ascent General Insurance Co"** successfully matches **"Ascent General Insurance Company"** in the database.

### Ranking Strategy
Results are returned in a unified list, sorted by relevance:
1.  **Exact Word Matches** (Highest Priority)
2.  **Normalized Matches** (e.g., Abbreviations)
3.  **Fuzzy Matches** (Lowest Priority, sorted by edit distance)

## 5. Deployment & Operations

*   **Infrastructure as Code:** Terraform manages the BigQuery Dataset, Table, and the GCS Bucket used for Dataflow staging.
*   **CI/CD Ready:** Integration tests (`tests/`) verify both the parsing logic and the search accuracy against the live BigQuery instance.
