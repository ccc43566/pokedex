-- PostgreSQL / Navicat. All statements below are read-only.
-- Entity IDs are original PokeAPI IDs. catalog_dictionary.id is a local FK;
-- catalog_dictionary.resource_id is the original dictionary ID.

-- 1. Resource counts.
SELECT 'move' AS resource, count(*) FROM move
UNION ALL SELECT 'item', count(*) FROM item
UNION ALL SELECT 'berry', count(*) FROM berry;

-- 2. Moves with Chinese -> English -> original-identifier name fallback.
SELECT m.id, coalesce(zh.name, en.name, m.name) AS name,
       t.name AS type, dc.name AS damage_class, m.power, m.accuracy, m.pp, m.priority
FROM move m
LEFT JOIN catalog_dictionary t ON t.id = m.type_id
LEFT JOIN catalog_dictionary dc ON dc.id = m.damage_class_id
LEFT JOIN LATERAL (SELECT name FROM localized_name WHERE entity_type='move'
  AND entity_id=m.id AND locale='zh-Hans' ORDER BY id LIMIT 1) zh ON true
LEFT JOIN LATERAL (SELECT name FROM localized_name WHERE entity_type='move'
  AND entity_id=m.id AND locale='en' ORDER BY id LIMIT 1) en ON true
ORDER BY m.id LIMIT 50;

-- 3. Pikachu's learning data: retained per Pokemon record and version group.
SELECT p.id AS pokemon_id, p.name AS pokemon, m.id AS move_id, m.name AS move,
       vg.resource_id AS source_version_group_id, vg.name AS version_group,
       lm.name AS learn_method, pm.level_learned_at, pm.learn_order, pm.raw_payload
FROM pokemon_move pm
JOIN pokemon p ON p.id=pm.pokemon_id
JOIN move m ON m.id=pm.move_id
JOIN catalog_dictionary vg ON vg.id=pm.version_group_id
JOIN catalog_dictionary lm ON lm.id=pm.learn_method_id
WHERE p.id=25
ORDER BY vg.resource_id, lm.resource_id, pm.level_learned_at, m.id;

-- 4. Held items and unmodified upstream rarity, per game version.
SELECT p.id, p.name AS pokemon, i.id AS item_id, i.name AS item,
       v.resource_id AS source_version_id, v.name AS version, h.rarity, h.raw_payload
FROM pokemon_held_item h
JOIN pokemon p ON p.id=h.pokemon_id
JOIN item i ON i.id=h.item_id
JOIN catalog_dictionary v ON v.id=h.version_id
WHERE p.id=25 ORDER BY v.resource_id, i.id;

-- 5. Official item category -> pocket hierarchy. No item-name heuristics.
SELECT pocket.resource_id AS pocket_id, pocket.name AS pocket,
       category.resource_id AS category_id, category.name AS category, count(*) AS items
FROM item i
JOIN catalog_dictionary category ON category.id=i.category_id
JOIN catalog_dictionary_link edge ON edge.dictionary_id=category.id AND edge.path='$.pocket'
JOIN catalog_dictionary pocket ON pocket.id=edge.target_id
GROUP BY 1,2,3,4 ORDER BY 1,3;

-- 6. Berries reuse their Item's localized name; no duplicate berry effect/name store.
SELECT b.id AS berry_id,b.name AS berry_identifier,b.item_id,
       coalesce(zh.name,en.name,i.name) AS name,firmness.name AS firmness,
       b.growth_time,b.max_harvest,b.size,b.smoothness,b.soil_dryness,
       b.natural_gift_power,t.name AS natural_gift_type
FROM berry b JOIN item i ON i.id=b.item_id
LEFT JOIN catalog_dictionary firmness ON firmness.id=b.firmness_id
LEFT JOIN catalog_dictionary t ON t.id=b.natural_gift_type_id
LEFT JOIN LATERAL (SELECT name FROM localized_name WHERE entity_type='item'
  AND entity_id=i.id AND locale='zh-Hans' ORDER BY id LIMIT 1) zh ON true
LEFT JOIN LATERAL (SELECT name FROM localized_name WHERE entity_type='item'
  AND entity_id=i.id AND locale='en' ORDER BY id LIMIT 1) en ON true
ORDER BY b.id;

-- 7. All language/version contexts remain available; not a single overwritten description.
SELECT entity_id,locale,text_kind,version,text FROM localized_text
WHERE entity_type='move' AND entity_id=33 ORDER BY text_kind,version,locale;
SELECT h.move_id,vg.name AS version_group,h.power,h.accuracy,h.pp,h.raw_payload
FROM move_past_value h LEFT JOIN catalog_dictionary vg ON vg.id=h.version_group_id
ORDER BY h.move_id,h.ordinal;

-- 8. Evolution item references retain JSON path (node and alternative method).
SELECT r.chain_id,r.path,r.role,r.item_id,i.name,r.raw_reference
FROM evolution_item_reference r JOIN item i ON i.id=r.item_id ORDER BY r.chain_id,r.path;

-- 9. Progress, failures and unresolved references.
SELECT id,status,started_at,finished_at,counts,error FROM sync_run
WHERE counts->>'scope'='reference-data' ORDER BY id DESC LIMIT 10;
SELECT resource_type,status,count(*) FROM catalog_sync_entry GROUP BY 1,2 ORDER BY 1,2;
SELECT * FROM catalog_sync_entry WHERE status <> 'success' ORDER BY resource_type,resource_id;
SELECT * FROM catalog_reference_issue WHERE NOT resolved ORDER BY owner_type,owner_id,path;

-- 10. Unabridged source JSON, URL, SHA-256 and acquisition timestamp; image URLs only.
SELECT s.resource_type,s.resource_id,s.source_url,s.source_hash,s.fetched_at,
       s.raw_payload->'sprites' AS image_source_metadata,s.raw_payload
FROM source_record s WHERE s.resource_type='item' AND s.resource_id=1;

-- 11. Current API prices are version/currency-specific; null and zero differ.
SELECT p.item_id,i.name,vg.name AS version_group,c.name AS currency,
       p.purchase_price,p.sell_price,p.raw_payload
FROM item_price p JOIN item i ON i.id=p.item_id
JOIN catalog_dictionary vg ON vg.id=p.version_group_id
JOIN catalog_dictionary c ON c.id=p.currency_id
WHERE p.item_id IN (1,2,3,4) ORDER BY p.item_id,vg.resource_id,c.resource_id;

-- 12. Distinct upstream IDs may share an English identifier; retain both.
SELECT name,array_agg(id ORDER BY id) ids FROM item GROUP BY name HAVING count(*)>1;
