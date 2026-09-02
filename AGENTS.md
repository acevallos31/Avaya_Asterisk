# AGENTS.md — Avaya Asterisk / Issabel Endpoint Configurator

> Contexto operativo obligatorio para humanos y agentes de IA. Leer completo antes de modificar código, workflows, helpers o el paquete de release.

## Objetivo

Integrar Avaya J129 al Endpoint Configurator estándar de Issabel 5 sin UI paralela para credenciales SIP y sin modificar el core de Issabel.

Flujo esperado:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Ramas

- `main`: referencia/histórico y workflows visibles en Actions. No usar para pruebas mutantes LAB.
- `Audit`: rama de trabajo, auditoría, harness y validación del LAB.
- `release/j129-v0.1.0`: rama limpia de distribución. Solo debe contener material necesario para el paquete v0.1.0 y documentación asociada.
- No hacer merge completo de `Audit` a `main` ni a la rama de release: `Audit` contiene evidencia, fixtures, workflows y deuda de laboratorio que no pertenece al paquete de producción.
- Todo workflow mutante LAB debe abortar si `GITHUB_REF_NAME != Audit`.

## LAB actual — 2026-09-02

- Issabel 5 / Rocky Linux 8.
- Asterisk 18.19.0.
- Python del sistema: 3.6.8.
- PBX/provisioning: `192.168.1.10`.
- J129: `192.168.1.168`.
- MAC: `C8:1F:EA:9B:65:0D`.
- Firmware: `3.0.0.0.20`.
- Endpoint id: `3`.
- Cuenta SIP actual: `200`.
- Runner: self-hosted, usuario `github-runner`, ruta de workspace bajo `/opt/actions-runner/_work/Avaya_Asterisk/Avaya_Asterisk`.
- `192.168.1.169` está ocupado por otro dispositivo; no usarlo para la PBX.

## Arquitectura obligatoria

El vendor Avaya debe consumir `_accounts` entregadas por Issabel. No reconsultar secretos SIP desde DB.

No modificar salvo evidencia extraordinaria:

```text
/usr/bin/issabel-endpointconfig
BaseEndpoint.py
Extension.py
EndpointManager_Standard.class.php
```

Overlay validado:

```text
deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
```

El paquete de release usa copia autocontenida equivalente bajo:

```text
release/j129-v0.1.0/payload/
```

## Seguridad

Nunca almacenar ni imprimir secretos SIP reales, contraseña Web Admin, cookies, XToken, nonce, hashes de autenticación, tokens o claves privadas.

La credencial Web Admin usada anteriormente debe considerarse expuesta y rotarse antes de producción. `J129_WEB_PASSWORD` permanece solo como GitHub Repository Secret.

No ampliar sudo del runner. Mantener helpers restringidos y acciones explícitas.

Phone Reports y exports pueden incluir información sensible. No subir reportes brutos a la release.

## J129 v1 — una sola cuenta

Validado en LAB:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

Multicuenta queda fuera de v0.1.0.

## Evidencia validada 07–11

### 07 — Rescan Idempotency

PASS: dos rescans no duplican endpoint ni pierden la cuenta `200`.

### 08 — Single Account V1

PASS: J129 v1 limitado a una cuenta SIP.

### 09 — Remote provisioning / comportamiento real

`PHYSICAL-J129-PASS`: `check-sync` provoca reinicio físico, nueva descarga de provisioning y re-registro SIP. No describirlo como reload silencioso.

### 10 — NTP / Forced Provisioning

Apply normal de Issabel generó:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

No hubo polling natural de provisioning en 300 s. Tras un reinicio posterior, la hora del teléfono quedó correcta, confirmando consumo físico de la configuración de tiempo.

Deuda: cuando chronyd sea reiniciado, esperar y afirmar que vuelve a estado sincronizado antes de considerar el test completo.

### 11 — Phone UX & Admin

Server-side Apply llegó a generar:

```text
SET PROCSTAT 0
SET PROVIDE_OPTIONS_SCREEN 1
SET PROVIDE_NETWORKINFO_SCREEN 1
SET PROVIDE_LOGOUT 1
SET ENTRYNAME Briam
```

Tras reinicio del teléfono, la hora se corrigió pero el menú visible no apareció. No afirmar que esos parámetros crean una softkey/menu en J129 3.0.0.0.20. Idioma español sigue pendiente de XML oficial Avaya.

## Workflow 12 — Production Patch

`12 | Issabel Lab | J129 Production Patch | Install & Rollback Test` quedó VERDE.

Validó el candidato mínimo con el ciclo:

```text
preflight -> install -> verify -> install -> verify -> rollback
```

Esto valida instalación, verificación, idempotencia y rollback en el LAB para el candidato previo a empaquetado.

No confundir este PASS con autorización automática para producción: todavía falta validar el paquete exacto de release y auditar la central destino.

## Release v0.1.0

Rama: `release/j129-v0.1.0`.

Alcance intencionalmente mínimo:

- integración J129 en Endpoint Configurator estándar;
- una sola cuenta SIP;
- provisioning Avaya;
- configuración Apache necesaria;
- instalador autocontenido con preflight/install/verify/rollback;
- sin firmware automático;
- sin idioma español;
- sin menú UX experimental;
- sin cambios automáticos de Web Admin password;
- sin reinicio automático del teléfono durante instalación.

No incluir `46xxsettings.txt` estáticos ni configuraciones históricas de teléfonos dentro del payload de producción. `46xxsettings.txt` debe generarlo Issabel desde la plantilla.

El archivo histórico `46xxsettings.txt funciona Choloma.txt` es evidencia de referencia de un teléfono que funcionó. Si se conserva, debe moverse/renombrarse como ejemplo claramente no instalable, después de revisar que no contenga secretos.

## Workflow 13 — Release Package Smoke Test

`13 | Issabel Lab | J129 Release Package | Smoke Test` todavía NO está verde.

Los rojos recientes no han demostrado un fallo funcional del instalador de release. El fallo actual ocurre antes de probar el paquete porque `actions/checkout` intenta limpiar el workspace y encuentra archivos `.pyc` creados previamente por `root`.

Error observado:

```text
EACCES: permission denied, unlink
.../deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/__pycache__/Avaya.cpython-36.pyc
```

Causa confirmada:

1. self-hosted runner usa `github-runner`;
2. una ejecución anterior con privilegios generó `__pycache__/*.pyc` propiedad de `root` dentro del checkout;
3. el siguiente `actions/checkout` intenta limpiar antes de que cualquier step del workflow tenga oportunidad de ejecutar un helper;
4. `github-runner` no puede borrar el archivo de `root` y el job falla en checkout.

Regla: no afirmar que el workflow 13 probó o invalidó el paquete mientras muera en el checkout inicial.

## Problema de ownership del runner — prioridad inmediata

El workspace de GitHub Actions no debe quedar contaminado con archivos generados por root.

Antes de repetir workflow 13 debe limpiarse/corregirse ownership de los residuos root-owned ya existentes en el workspace. Después, evitar que los helpers root ejecuten Python de manera que escriba `__pycache__` dentro del checkout.

Mitigaciones de diseño obligatorias:

- mantener `PYTHONDONTWRITEBYTECODE=1` para Python ejecutado en workflows;
- preferir `python3 -B` en comandos privilegiados que lean código desde el checkout;
- helpers root no deben generar artefactos dentro del repositorio/workspace;
- si un helper necesita temporales, usar `/tmp` o un directorio de estado controlado fuera del checkout;
- añadir auditoría de ownership/residuos antes y después de los ciclos que usan sudo;
- no resolver con `sudo chmod -R 777` ni sudo amplio.

Importante: un step posterior a `actions/checkout` no puede arreglar un archivo que hace fallar ese mismo checkout. La limpieza inicial debe hacerse fuera de ese checkout problemático o una sola vez desde la consola del LAB/runner con alcance exacto.

## BUGS / deuda abierta

- `BUG-EC-001`: GUI `Registered at` puede quedar obsoleta; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta histórica incorrecta; v1 limitado a una cuenta.
- `BUG-J129-004`: retirar provisioning server-side no borra identidad SIP persistida localmente.
- consumo inmediato: Apply normal no fuerza polling; `check-sync` reinicia este firmware.
- menú local: parámetros probados no hicieron aparecer acceso visible.
- idioma: falta XML oficial Latin American Spanish.
- observabilidad HTTP del restart: detector debe usar lectura autorizada de logs.
- helpers LAB: eliminar hardcodes/runtime patching y prevenir residuos root-owned.
- release: workflow 13 debe quedar verde sobre el paquete exacto antes de producción.

## Regla para DB Endpoint Configurator

La base real es MySQL/MariaDB `endpointconfig`, no SQLite. No asumir nombres de columnas. Reutilizar consultas validadas o auditar esquema read-only primero.

## Próximo paso obligatorio

1. reparar una sola vez el ownership/residuo `.pyc` que bloquea el checkout del self-hosted runner;
2. ajustar el harness para que ningún proceso root vuelva a escribir `__pycache__` dentro del workspace;
3. lanzar un NUEVO workflow 13 en `Audit` con `TEST-RELEASE`;
4. solo si llega al ciclo real del instalador, evaluar preflight/install/verify/idempotencia/rollback;
5. si queda verde, congelar el paquete exacto v0.1.0 con checksums;
6. auditar la central de producción antes de instalar;
7. preparar runbook de producción con preflight, backup, install, verify y rollback.

## Protocolo para agentes

Leer en orden:

1. `AGENTS.md`;
2. `CONTEXT.md`;
3. `docs/j129-lab-validation.md`;
4. `docs/j129-research-notes.md`;
5. `docs/agent-log.md`;
6. `release/j129-v0.1.0/README.md` cuando se trabaje en distribución;
7. runs y commits recientes de `Audit` y `release/j129-v0.1.0`.

No afirmar `PHYSICAL-J129-PASS` si solo pasó CI/LAB server-side. No afirmar `RELEASE-PASS` hasta que workflow 13 complete el ciclo real del paquete exacto.
