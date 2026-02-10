from google.cloud import bigquery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_data(project_id, dataset_id, table_id):
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Test Cases
    test_cases = [
        {"name_part": "ARTEMIS GAS", "expected_found": True},
        {"name_part": "Viktorov", "expected_found": True},
        {"name_part": "Sobar", "expected_found": True},
        {"name_part": "NON_EXISTENT_NAME_XYZ_123", "expected_found": False}
    ]

    logging.info(f"Verifying data in {table_ref}...")

    # 1. Verify specific names exist
    for case in test_cases:
        query = f"""
            SELECT t.entity_id, n.full_name
            FROM `{table_ref}` AS t, UNNEST(t.names) AS n
            WHERE LOWER(n.full_name) LIKE @name_pattern
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("name_pattern", "STRING", f"%{case['name_part'].lower()}%")
            ]
        )
        
        results = list(client.query(query, job_config=job_config))
        found = len(results) > 0
        
        if found == case['expected_found']:
            status = "PASS"
            details = f"(Found: {results[0]['full_name']} ID: {results[0]['entity_id']})" if found else "(Correctly not found)"
        else:
            status = "FAIL"
            details = f"(Expected {case['expected_found']}, got {found})"
            
        logging.info(f"Search for '{case['name_part']}': {status} {details}")

    # 2. Verify country_iso2 population (e.g. for Russia)
    logging.info("Verifying country_iso2 population...")
    iso_query = f"""
        SELECT t.entity_id, a.country, a.country_iso2
        FROM `{table_ref}` AS t, UNNEST(t.addresses) AS a
        WHERE a.country_iso2 IS NOT NULL
        LIMIT 5
    """
    iso_results = list(client.query(iso_query))
    
    if iso_results:
        logging.info(f"Found {len(iso_results)} records with country_iso2 populated: PASS")
        for row in iso_results:
            logging.info(f"  - Entity {row['entity_id']}: {row['country']} -> {row['country_iso2']}")
    else:
        logging.error("No records found with country_iso2 populated: FAIL")

    # 3. Verify total count
    count_query = f"SELECT COUNT(*) as total FROM `{table_ref}`"
    count_result = list(client.query(count_query))[0]['total']
    logging.info(f"Total records in table: {count_result}")
    if count_result > 18000:
         logging.info("Total count seems reasonable (>18000): PASS")
    else:
         logging.warning(f"Total count seems low ({count_result}): WARNING")

if __name__ == "__main__":
    PROJECT_ID = "agentspace-krozario"
    DATASET_ID = "sanctions_data"
    TABLE_ID = "sdn_entities"
    
    verify_data(PROJECT_ID, DATASET_ID, TABLE_ID)
