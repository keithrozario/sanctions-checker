/*
  Fuzzy Search using Levenshtein Distance (EDIT_DISTANCE).
  
  Parameters:
  - @search_term: The name you are looking for (e.g., 'Aerocaribean')
  - @threshold: Maximum allowed typos (e.g., 2)
*/

DECLARE search_term STRING DEFAULT 'AEROCARIBBEAN';
DECLARE threshold INT64 DEFAULT 2;

SELECT 
  entity_id, 
  n.full_name AS matched_name, 
  n.is_primary,
  EDIT_DISTANCE(UPPER(n.full_name), UPPER(search_term)) AS typo_distance
FROM 
  `your_dataset.sdn_entities`,
  UNNEST(names) AS n
WHERE 
  -- Optimization: Don't compute distance for strings with significantly different lengths
  ABS(LENGTH(n.full_name) - LENGTH(search_term)) <= threshold
  -- Actual Fuzzy Match
  AND EDIT_DISTANCE(UPPER(n.full_name), UPPER(search_term)) <= threshold
ORDER BY 
  typo_distance ASC, 
  is_primary DESC
LIMIT 10;
