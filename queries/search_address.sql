/*
  Query to search for entities by address components (raw or enriched).
  
  Parameters:
  - @search_term: The address component to search for (e.g., 'Tehran', 'Street', 'Zweierstrasse')
  - @threshold: Levenshtein distance threshold for fuzzy matching on address lines.
*/

DECLARE search_term STRING DEFAULT 'Zweierstrasse';
DECLARE threshold INT64 DEFAULT 1;

-- Optionally, normalize the search term in SQL if needed for address components,
-- but for exact matching it's usually enough to UPPER() it.

SELECT DISTINCT
    t.entity_id,
    n.full_name,
    a.address_line,
    a.city,
    a.state,
    a.postal_code,
    a.country,
    JSON_VALUE(a.enriched_data, '$.result.address.formattedAddress') AS google_maps_formatted_address,
    JSON_VALUE(a.enriched_data, '$.result.address.postalAddress.regionCode') AS google_maps_country_code
FROM
    `{{project_id}}.{{dataset_id}}.{{table_id}}` AS t,
    UNNEST(t.names) AS n,
    UNNEST(t.addresses) AS a
WHERE
    -- Search in original address line (fuzzy)
    (a.address_line IS NOT NULL AND EDIT_DISTANCE(UPPER(a.address_line), UPPER(search_term)) <= threshold)
    -- Search in original city (fuzzy)
    OR (a.city IS NOT NULL AND EDIT_DISTANCE(UPPER(a.city), UPPER(search_term)) <= threshold)
    -- Search in original country (fuzzy)
    OR (a.country IS NOT NULL AND EDIT_DISTANCE(UPPER(a.country), UPPER(search_term)) <= threshold)
    -- Search in Google Maps formatted address (fuzzy)
    OR (JSON_VALUE(a.enriched_data, '$.result.address.formattedAddress') IS NOT NULL AND EDIT_DISTANCE(UPPER(JSON_VALUE(a.enriched_data, '$.result.address.formattedAddress')), UPPER(search_term)) <= threshold)
    -- Search in Google Maps locality (city) (fuzzy)
    OR (JSON_VALUE(a.enriched_data, '$.result.address.locality') IS NOT NULL AND EDIT_DISTANCE(UPPER(JSON_VALUE(a.enriched_data, '$.result.address.locality')), UPPER(search_term)) <= threshold)
    -- Search in Google Maps postal code (exact, no fuzzy)
    OR (JSON_VALUE(a.enriched_data, '$.result.address.postalAddress.postalCode') IS NOT NULL AND UPPER(JSON_VALUE(a.enriched_data, '$.result.address.postalAddress.postalCode')) = UPPER(search_term))
ORDER BY 
    t.entity_id,
    n.is_primary DESC
LIMIT 10;
