# Endpoint Configuration v1.0.1-rc4 — Ceiba Golden Image

RC4 no introduce funcionalidades nuevas. Su objetivo es dejar una central Issabel
con el mismo runtime auditado que actualmente funciona en Ceiba.

## Base requerida

RC4 exige:

`issabel-endpointconfig2-5.0.0-1.el8.noarch`

Es la misma base auditada en `cei-pbx02`.

## Referencia

Golden Reference:

- Workflow 76
- Run `35405907865`
- Fecha: 2026-09-18
- Resultado: success

RC4 instala y luego verifica por SHA-256 los mismos archivos observados en Ceiba:

- Grandstream.py V2
- Avaya.py
- Avaya_J129.tpl
- Avaya_global_SIP.tpl
- configuración HTTP J129
- /usr/bin/issabel-endpointconfig
- BaseEndpoint.py
- paloEndpointScanStatus.class.php
- paloSantoEndpoints.class.php
- EndpointManager_Standard.class.php
- index.php de Endpoint Configurator
- summary
- reporte_endpoints.tpl
- javascript.js
- EndpointCredentialVault.class.php

También instala el catálogo Grandstream/Avaya y la foundation de credenciales
administrativas usada en Ceiba.

## Seguridad

RC4 conserva el bootstrap DBA temporal de RC3. Si las tablas de credenciales no
existen, el instalador solicita usuario DBA y contraseña mediante entrada oculta.
La contraseña solo vive en un archivo temporal 0600 y se elimina al finalizar.

El instalador:

- NO ejecuta discovery;
- NO asigna extensiones;
- NO ejecuta Configure/Apply;
- NO reinicia teléfonos;
- NO escribe en teléfonos.

## Instalación

```bash
tar -xzf endpoint-configuration-v1.0.1-rc4.tar.gz
cd endpoint-configuration-v1.0.1-rc4

sudo bash install.sh preflight
sudo bash install.sh install
sudo bash install.sh verify
```

Una instalación correcta debe terminar con:

```text
CEIBA-GOLDEN-PAYLOAD-PASS
CEIBA-GOLDEN-RUNTIME-INSTALL-PASS
CEIBA-GOLDEN-SHA-PARITY-PASS
VERIFY-PASS
INSTALL-PASS
```

## Rollback

```bash
sudo bash install.sh rollback
```

RC4 crea un backup propio antes de reemplazar archivos.

## Importante

RC4 reproduce el **software/runtime de Ceiba**. No copia la base de datos de
Ceiba, sus endpoints, sus extensiones ni sus contraseñas. Esos datos pertenecen
a cada central.
