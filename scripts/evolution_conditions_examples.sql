-- Read-only PostgreSQL / Navicat examples.

-- Original dictionaries remain separate from independently maintained project Chinese.
SELECT d.resource_type,d.resource_id,d.name,
       coalesce(zh.name,
         CASE WHEN d.resource_type='evolution-trigger' THEN p.raw_payload->'triggers'->>d.name
              ELSE p.raw_payload->'variables'->d.name->>'zh' END,
         en.name,d.name) AS chinese_or_fallback,
       CASE WHEN zh.name IS NOT NULL THEN 'upstream translation'
            WHEN d.resource_type='evolution-trigger' AND p.raw_payload->'triggers' ? d.name
              THEN 'project explanation'
            WHEN d.resource_type='evolution-variable' AND p.raw_payload->'variables' ? d.name
              THEN 'project explanation'
            ELSE 'English / identifier fallback' END AS explanation_origin,
       s.source_url,s.fetched_at,s.source_hash,s.raw_payload
FROM catalog_dictionary d JOIN source_record s ON s.id=d.source_record_id
JOIN source_record p ON p.resource_type='project-evolution-glossary' AND p.resource_id=1
LEFT JOIN LATERAL (SELECT name FROM localized_name WHERE entity_type=d.resource_type
  AND entity_id=d.resource_id AND locale='zh-Hans' ORDER BY id LIMIT 1) zh ON true
LEFT JOIN LATERAL (SELECT name FROM localized_name WHERE entity_type=d.resource_type
  AND entity_id=d.resource_id AND locale='en' ORDER BY id LIMIT 1) en ON true
WHERE d.resource_type IN ('evolution-trigger','evolution-variable')
ORDER BY d.resource_type,d.resource_id;

-- Spin direction and seconds definitions, including their introduction metadata.
SELECT resource_id,name,raw_payload->>'symbol' AS symbol,
       raw_payload->>'data_type' AS data_type,raw_payload->>'source' AS variable_source,
       raw_payload->'version_group' AS introduced_in,raw_payload->'descriptions' AS definitions,
       source_url,fetched_at,source_hash
FROM source_record WHERE resource_type='evolution-variable' ORDER BY resource_id;

-- Nincada: level-up and shed remain two distinct source relationships.
SELECT child->'species'->>'name' AS target,
       method->'trigger'->>'name' AS trigger,method->>'min_level' AS min_level,
       method->'version_group' AS introduced_in,method->'is_default' AS is_default,
       method AS complete_original_conditions
FROM evolution_chain c
CROSS JOIN LATERAL jsonb_array_elements(c.raw_payload->'chain'->'evolves_to') child
CROSS JOIN LATERAL jsonb_array_elements(child->'evolution_details') method
WHERE c.id=144;

-- Supplement is explicitly not an upstream field; its scope and sources are preserved.
SELECT resource_type,resource_id,source_url,fetched_at,source_hash,raw_payload
FROM source_record WHERE resource_type IN ('project-evolution-glossary','evolution-supplement')
ORDER BY resource_type,resource_id;

-- Dictionary-only discovery, progress and failures.
SELECT id,status,started_at,finished_at,counts,error FROM sync_run
WHERE counts->>'scope'='evolution-dictionaries' ORDER BY id DESC;
SELECT resource_type,resource_id,status,attempts,error FROM catalog_sync_entry
WHERE resource_type IN ('evolution-trigger','evolution-variable')
ORDER BY resource_type,resource_id;
