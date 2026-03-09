-- Avaya model audit and safe normalization script
-- Purpose: review and correct model assignment for Avaya endpoints (J129, 1603-I, 1603SW-I)
-- Database: endpointconfig
-- NOTE: Review SELECT outputs before running UPDATE/INSERT/DELETE sections.

USE endpointconfig;

-- 1) Quick inventory of Avaya manufacturers/models
SELECT id, name, description
FROM manufacturer
WHERE name = 'Avaya';

SELECT m.id, m.id_manufacturer, m.name, m.description, m.max_accounts, m.static_prov_supported
FROM model m
JOIN manufacturer mf ON mf.id = m.id_manufacturer
WHERE mf.name = 'Avaya'
ORDER BY m.id;

-- 2) Current Avaya endpoints by MAC/model
SELECT e.id, e.mac_address, e.last_known_ipv4, mf.name AS manufacturer, mo.name AS model
FROM endpoint e
LEFT JOIN manufacturer mf ON mf.id = e.id_manufacturer
LEFT JOIN model mo ON mo.id = e.id_model
WHERE mf.name = 'Avaya'
ORDER BY e.id;

-- 3) Avaya endpoints without model (must be resolved manually or by rule)
SELECT e.id, e.mac_address, e.last_known_ipv4
FROM endpoint e
JOIN manufacturer mf ON mf.id = e.id_manufacturer
WHERE mf.name = 'Avaya' AND e.id_model IS NULL
ORDER BY e.id;

-- 4) Prefix map currently defined for Avaya (detect conflicts)
SELECT mp.id, mp.mac_prefix, mp.description
FROM mac_prefix mp
JOIN manufacturer mf ON mf.id = mp.id_manufacturer
WHERE mf.name = 'Avaya'
ORDER BY mp.mac_prefix, mp.id;

-- 5) Duplicate prefixes for Avaya (same OUI assigned multiple times)
SELECT mp.mac_prefix, COUNT(*) AS total
FROM mac_prefix mp
JOIN manufacturer mf ON mf.id = mp.id_manufacturer
WHERE mf.name = 'Avaya'
GROUP BY mp.mac_prefix
HAVING COUNT(*) > 1
ORDER BY total DESC, mp.mac_prefix;

-- 6) Accounts linked to Avaya endpoints (for provisioning validation)
SELECT e.id AS endpoint_id, e.mac_address, ea.tech, ea.account, ea.priority
FROM endpoint e
JOIN manufacturer mf ON mf.id = e.id_manufacturer
LEFT JOIN endpoint_account ea ON ea.id_endpoint = e.id
WHERE mf.name = 'Avaya'
ORDER BY e.id, ea.priority;

-- 7) Optional: model properties for Avaya (template, feature flags)
SELECT mo.name AS model, mp.property_key, mp.property_value
FROM model_properties mp
JOIN model mo ON mo.id = mp.id_model
JOIN manufacturer mf ON mf.id = mo.id_manufacturer
WHERE mf.name = 'Avaya'
ORDER BY mo.name, mp.property_key;

-- ------------------------------------------------------------------
-- Safe correction examples (UNCOMMENT ONLY AFTER REVIEW)
-- ------------------------------------------------------------------

-- Example A: Force known J129 batch by OUI (only if you are sure)
-- UPDATE endpoint
-- SET id_model = 147
-- WHERE id_manufacturer = (SELECT id FROM manufacturer WHERE name = 'Avaya')
--   AND mac_address LIKE 'C8:1F:EA:%';

-- Example B: Force known 1603-I phone by exact MAC
-- UPDATE endpoint
-- SET id_model = 148
-- WHERE id_manufacturer = (SELECT id FROM manufacturer WHERE name = 'Avaya')
--   AND mac_address = 'B4:A9:5A:AC:F6:55';

-- Example C: Force known 1603SW-I phones by exact MAC list
-- UPDATE endpoint
-- SET id_model = 149
-- WHERE id_manufacturer = (SELECT id FROM manufacturer WHERE name = 'Avaya')
--   AND mac_address IN ('00:1B:4F:4D:F2:4F', '00:1B:4F:4D:F5:AA', 'D4:EA:0E:91:A9:7B');

-- Example D: Remove duplicate Avaya OUI rows after deciding final mapping
-- DELETE FROM mac_prefix
-- WHERE id IN (/* duplicate IDs to remove after review */);

-- Final verification after any change
SELECT e.id, e.mac_address, e.last_known_ipv4, mo.name AS model
FROM endpoint e
JOIN manufacturer mf ON mf.id = e.id_manufacturer
LEFT JOIN model mo ON mo.id = e.id_model
WHERE mf.name = 'Avaya'
ORDER BY e.id;
