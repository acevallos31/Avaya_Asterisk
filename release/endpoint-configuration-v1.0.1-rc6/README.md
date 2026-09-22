# Endpoint Configuration v1.0.1-rc6 — Discovery Bootstrap

RC6 parte del runtime validado en Ceiba y del RC5 ya probado en Tocoa.

El cambio específico de RC6 corrige el flujo real de discovery:

- `detect_endpoints` intenta primero el probe stock del fabricante;
- si Grandstream queda sin modelo, consulta Asterisk en modo read-only;
- correlaciona IP -> peer SIP;
- lee `Useragent`;
- mapea:
  - GRP2601 / GRP2601P -> GRP2601P
  - GRP2602G -> GRP2602G
  - GXP1625 -> GXP1625
- guarda `id_model` únicamente si sigue NULL;
- al finalizar el scan, el reconciliador corregido asocia IP -> extensión ->
  `endpoint_account`.

RC6 NO ejecuta discovery automáticamente y NO escribe en teléfonos.

## Instalación sobre RC5

```bash
tar -xzf endpoint-configuration-v1.0.1-rc6.tar.gz
cd endpoint-configuration-v1.0.1-rc6
sudo bash install.sh preflight
sudo bash install.sh install
sudo bash install.sh verify
```

Después de instalar, los teléfonos que se quieran reconciliar deben estar
registrados en Asterisk. Luego se ejecuta manualmente la lupa de Endpoint
Configurator.

Marcadores esperados:

```text
RC6-DISCOVERY-BOOTSTRAP-PAYLOAD-PASS
CEIBA-GOLDEN-RUNTIME-INSTALL-PASS
RC6-DISCOVERY-BOOTSTRAP-PASS
discovery_useragent_model=YES
discovery_ip_extension_reconcile=YES
VERIFY-PASS
INSTALL-PASS
```

Rollback:

```bash
sudo bash install.sh rollback
```
