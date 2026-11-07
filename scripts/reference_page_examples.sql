-- Read-only Navicat examples. No credentials, no writes.

-- Explicit IDs stay independent even when identifier and image match.
SELECT i.id, i.name, m.status, m.checksum, m.local_path
FROM item i LEFT JOIN item_media m ON m.item_id=i.id
WHERE i.id IN (723,2279) ORDER BY i.id;

-- Version-group and currency original IDs differ from local dictionary PKs.
SELECT i.id,i.name,vg.resource_id version_group_id,vg.name version_group,
  c.resource_id currency_id,c.name currency,p.purchase_price,p.sell_price,
  p.raw_payload
FROM item_price p JOIN item i ON i.id=p.item_id
JOIN catalog_dictionary vg ON vg.id=p.version_group_id
JOIN catalog_dictionary c ON c.id=p.currency_id
WHERE i.id=1 ORDER BY p.ordinal;

-- Berry data follows item_id, never the item name.
SELECT b.id berry_id,b.name,b.item_id,i.name item_name,
  b.growth_time,b.max_harvest,b.natural_gift_power
FROM berry b JOIN item i ON i.id=b.item_id
WHERE i.id IN (126,723,2278,2279) ORDER BY b.id;

-- Real official category -> pocket relation, not name inference.
SELECT i.id,i.name,category.resource_id category_id,category.name category,
  pocket.resource_id pocket_id,pocket.name pocket
FROM item i LEFT JOIN catalog_dictionary category ON category.id=i.category_id
LEFT JOIN catalog_dictionary_link l ON l.dictionary_id=category.id AND l.path='$.pocket'
LEFT JOIN catalog_dictionary pocket ON pocket.id=l.target_id
WHERE i.id IN (1,126,723,2278,2279) ORDER BY i.id;

-- Preserve each independent Pokemon form and each learn method/version/level row.
SELECT pm.pokemon_id,p.name,pm.move_id,m.name move,
  vg.resource_id version_group_id,vg.name version_group,
  method.name learn_method,pm.level_learned_at,pm.learn_order
FROM pokemon_move pm JOIN pokemon p ON p.id=pm.pokemon_id
JOIN move m ON m.id=pm.move_id
JOIN catalog_dictionary vg ON vg.id=pm.version_group_id
JOIN catalog_dictionary method ON method.id=pm.learn_method_id
WHERE pm.move_id=85 AND vg.resource_id=20
ORDER BY pm.pokemon_id,pm.move_ordinal,pm.detail_ordinal LIMIT 100;

-- A machine's ID/item/move/version are a unit; same item may differ across games.
SELECT m.id machine_id,m.item_id,i.name item,m.move_id,mv.name move,
  vg.resource_id version_group_id,vg.name version_group
FROM catalog_machine m JOIN item i ON i.id=m.item_id
JOIN move mv ON mv.id=m.move_id JOIN catalog_dictionary vg ON vg.id=m.version_group_id
WHERE m.move_id=85 ORDER BY vg.resource_id,m.id;

-- Historical values keep version context and untouched raw payloads.
SELECT h.move_id,vg.resource_id version_group_id,vg.name,h.power,h.accuracy,h.pp,
  h.effect_chance,h.raw_payload
FROM move_past_value h LEFT JOIN catalog_dictionary vg ON vg.id=h.version_group_id
WHERE h.move_id=85 ORDER BY h.ordinal;

-- Existing multilingual descriptions retain individual version contexts.
SELECT entity_type,entity_id,text_kind,version,locale,text
FROM localized_text WHERE entity_type='move' AND entity_id=85
AND locale IN ('zh-Hans','en') ORDER BY version NULLS FIRST,text_kind,locale;

-- Multiple item IDs must share exactly one path for identical bytes.
SELECT checksum,count(*) item_records,count(DISTINCT local_path) paths
FROM item_media WHERE status='downloaded' GROUP BY checksum
HAVING count(*)>1 ORDER BY count(*) DESC LIMIT 20;
