/*
  Query to count the total number of unique entities in the BigQuery table.
*/

SELECT COUNT(DISTINCT entity_id) AS total_entities
FROM `{{project_id}}.{{dataset_id}}.{{table_id}}`;
