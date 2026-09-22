START TRANSACTION;
SET @mf := (SELECT id FROM manufacturer WHERE name='Grandstream' LIMIT 1);
SET @source := (SELECT id FROM model WHERE id_manufacturer=@mf AND name='GXP1625' LIMIT 1);

INSERT INTO mac_prefix (id_manufacturer, mac_prefix, description)
SELECT @mf,'C0:74:AD','Grandstream GXP16xx' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM mac_prefix WHERE UPPER(mac_prefix)='C0:74:AD');
INSERT INTO mac_prefix (id_manufacturer, mac_prefix, description)
SELECT @mf,'EC:74:D7','Grandstream GRP26xx' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM mac_prefix WHERE UPPER(mac_prefix)='EC:74:D7');

INSERT INTO model (id_manufacturer,name,description,max_accounts,static_ip_supported,dynamic_ip_supported,static_prov_supported)
SELECT id_manufacturer,'GRP2601P','GRP2601P',2,static_ip_supported,dynamic_ip_supported,static_prov_supported
FROM model WHERE id=@source
AND NOT EXISTS (SELECT 1 FROM model WHERE id_manufacturer=@mf AND name='GRP2601P');
SET @grp2601p := (SELECT id FROM model WHERE id_manufacturer=@mf AND name='GRP2601P' LIMIT 1);
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @grp2601p,mp.property_key,CASE WHEN mp.property_key='max_sip_accounts' THEN '2' ELSE mp.property_value END
FROM model_properties mp WHERE mp.id_model=@source
AND NOT EXISTS (SELECT 1 FROM model_properties x WHERE x.id_model=@grp2601p AND x.property_key=mp.property_key);
UPDATE model SET max_accounts=2 WHERE id=@grp2601p;
UPDATE model_properties SET property_value='2' WHERE id_model=@grp2601p AND property_key='max_sip_accounts';

-- GRP2601 (non-P) reports itself literally as GRP2601 on current firmware.
-- Keep a distinct catalog row so stock probeModel() can persist the exact model
-- returned by /cgi-bin/api.values.get without any Asterisk-derived aliasing.
INSERT INTO model (id_manufacturer,name,description,max_accounts,static_ip_supported,dynamic_ip_supported,static_prov_supported)
SELECT id_manufacturer,'GRP2601','GRP2601',2,static_ip_supported,dynamic_ip_supported,static_prov_supported
FROM model WHERE id=@source
AND NOT EXISTS (SELECT 1 FROM model WHERE id_manufacturer=@mf AND name='GRP2601');
SET @grp2601 := (SELECT id FROM model WHERE id_manufacturer=@mf AND name='GRP2601' LIMIT 1);
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @grp2601,mp.property_key,CASE WHEN mp.property_key='max_sip_accounts' THEN '2' ELSE mp.property_value END
FROM model_properties mp WHERE mp.id_model=@source
AND NOT EXISTS (SELECT 1 FROM model_properties x WHERE x.id_model=@grp2601 AND x.property_key=mp.property_key);
UPDATE model SET max_accounts=2 WHERE id=@grp2601;
UPDATE model_properties SET property_value='2' WHERE id_model=@grp2601 AND property_key='max_sip_accounts';

INSERT INTO model (id_manufacturer,name,description,max_accounts,static_ip_supported,dynamic_ip_supported,static_prov_supported)
SELECT id_manufacturer,'GRP2602G','GRP2602G',4,static_ip_supported,dynamic_ip_supported,static_prov_supported
FROM model WHERE id=@source
AND NOT EXISTS (SELECT 1 FROM model WHERE id_manufacturer=@mf AND name='GRP2602G');
SET @grp2602g := (SELECT id FROM model WHERE id_manufacturer=@mf AND name='GRP2602G' LIMIT 1);
INSERT INTO model_properties (id_model,property_key,property_value)
SELECT @grp2602g,mp.property_key,CASE WHEN mp.property_key='max_sip_accounts' THEN '4' ELSE mp.property_value END
FROM model_properties mp WHERE mp.id_model=@source
AND NOT EXISTS (SELECT 1 FROM model_properties x WHERE x.id_model=@grp2602g AND x.property_key=mp.property_key);
UPDATE model SET max_accounts=4 WHERE id=@grp2602g;
UPDATE model_properties SET property_value='4' WHERE id_model=@grp2602g AND property_key='max_sip_accounts';
COMMIT;
