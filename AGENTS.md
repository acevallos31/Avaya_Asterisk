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

`13 | Issabel Lab | J129 Release Package | Smoke Test` quedó VERDE el 2026-09-02.

Run validado:

```text
run #5
run id: 33648748733
harness Audit: 5b7ab70b7d1eea7219fb084a75bc900639b0757f
release exacta: 74d3f4c
```

Evidencia del run:

```text
RELEASE-PY-SYNTAX-PASS
RELEASE-WORKSPACE-PYCACHE-CLEAN-PASS
[J129-PATCH 0.1.0] PREFLIGHT-PASS
RELEASE-FIRST-INSTALL-PASS
RELEASE-SECOND-INSTALL-IDEMPOTENT-PASS
[J129-PATCH 0.1.0] ROLLBACK-PASS
RELEASE-ROLLBACK-EXACT-PASS
J129-RELEASE-PACKAGE-V010-LAB-PASS
RUNNER-WORKSPACE-NO-ROOT-PYC-PASS
J129-RELEASE-PACKAGE-V010-SMOKE-PASS
```

Baseline DB antes del ciclo:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

El ciclo real probado sobre la rama exacta de release fue:

```text
preflight -> install -> verify -> install -> verify -> rollback
```

El segundo install fue idempotente y el rollback restauró exactamente archivos y valores DB comparados contra el baseline.

El antiguo bloqueo de `__pycache__/*.pyc` root-owned fue resuelto con limpieza puntual del residuo histórico y con prevención estructural: `PYTHONDONTWRITEBYTECODE=1`, `python3 -B` y validación por `ast.parse` en lugar de `py_compile` para el código leído desde el workspace. El run #5 terminó sin `.pyc` propiedad de root dentro del checkout.

Este PASS valida el paquete exacto v0.1.0 en el LAB. No equivale todavía a autorización ciega para producción: falta congelar/checksum del paquete y auditar la central destino.

## BUGS / deuda abierta

- `BUG-EC-001`: GUI `Registered at` puede quedar obsoleta; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta histórica incorrecta; v1 limitado a una cuenta.
- `BUG-J129-004`: retirar provisioning server-side no borra identidad SIP persistida localmente.
- consumo inmediato: Apply normal no fuerza polling; `check-sync` reinicia este firmware.
- menú local: parámetros probados no hicieron aparecer acceso visible.
- idioma: falta XML oficial Latin American Spanish.
- observabilidad HTTP del restart: detector debe usar lectura autorizada de logs.
- helpers LAB: reducir hardcodes/runtime patching histórico sin ampliar sudo.
- runner: mantener prevención de bytecode privilegiado dentro del workspace.

## Regla para DB Endpoint Configurator

La base real es MySQL/MariaDB `endpointconfig`, no SQLite. No asumir nombres de columnas. Reutilizar consultas validadas o auditar esquema read-only primero.

## Próximo paso obligatorio

1. congelar el paquete exacto v0.1.0 y registrar checksums SHA256;
2. auditar la central de producción antes de instalar;
3. rotar antes de producción cualquier credencial Web Admin previamente expuesta;
4. preparar runbook de producción con preflight, backup/snapshot, install, verify y rollback;
5. validar discovery, asignación de cuenta, Apply, provisioning HTTP y registro SIP en producción;
6. hacer rollback inmediato si falla cualquier criterio crítico.

No agregar nuevas funciones al J129 hasta cerrar este ciclo de release/producción de v0.1.0.

## Protocolo para agentes

Leer en orden:

1. `AGENTS.md`;
2. `CONTEXT.md`;
3. `docs/j129-lab-validation.md`;
4. `docs/j129-research-notes.md`;
5. `docs/agent-log.md`;
6. `release/j129-v0.1.0/README.md` cuando se trabaje en distribución;
7. runs y commits recientes de `Audit` y `release/j129-v0.1.0`.

No afirmar `PHYSICAL-J129-PASS` si solo pasó CI/LAB server-side. `RELEASE-PASS` para v0.1.0 queda respaldado por workflow 13 run #5 en LAB; producción sigue requiriendo auditoría y ejecución controlada separada.
