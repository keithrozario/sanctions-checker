/*
  Query to list all unique countries associated with entities in the BigQuery table.
  It compares the raw SDN country with the Google Maps validated country code (ISO).
*/

SELECT DISTINCT 
    address.country AS sdn_country,
    JSON_VALUE(address.enriched_data, '$.result.address.postalAddress.regionCode') AS google_maps_country_code
FROM 
    `{{project_id}}.{{dataset_id}}.{{table_id}}`,
    UNNEST(addresses) AS address
WHERE
    address.country IS NOT NULL OR address.enriched_data IS NOT NULL
ORDER BY 
    sdn_country;
