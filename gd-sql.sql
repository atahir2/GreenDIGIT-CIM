-- Select *
-- from metric_keywords

SELECT
  md.unified_key,
  st.code AS standard_code,
  msm.confidence
FROM metric_definitions md
LEFT JOIN metric_standard_map msm ON msm.metric_definition_id = md.id
LEFT JOIN standards st ON st.id = msm.standard_id
ORDER BY md.unified_key, st.code NULLS LAST;