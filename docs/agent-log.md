# Agent Audit Log

Registro compartido de trabajo humano/IA en `Avaya_Asterisk`. Consultar primero `AGENTS.md`. No almacenar secretos reales.

Estados usados: `STATIC-PASS`, `LAB-READ-PASS`, `LAB-INTEGRATION-PASS`, `LAB-FIX-PASS`, `PHYSICAL-J129-PASS`, `PRODUCTION-REFERENCE`, `NOT-TESTED`.

---

## 2026-08-31 — OpenAI-GPT-5.6-Sol

Se consolidó el contrato de arquitectura J129: core Issabel stock, Accounts estándar, Avaya consume `_accounts`, provisioning global -> `GET $MACADDR.txt` -> archivo por MAC, sin consultas directas de secretos desde vendor. Se añadieron contratos SOLID/golden y fixtures ficticios.

## 2026-09-01 — OpenAI-GPT-5.6-Sol

Se validó físicamente discovery, provisioning HTTP, registro SIP y lifecycle. Se registraron `BUG-EC-001`, `BUG-J129-002`, `BUG-J129-003` y `BUG-J129-004`. `BUG-J129-003` quedó corregido server-side usando `BaseEndpoint.deleteContent()` cuando no hay cuentas. `BUG-J129-004` sigue abierto: eliminar el archivo por MAC no borra una identidad SIP persistida localmente en el J129.

## 2026-09-02 — OpenAI-GPT-5.6-Sol

**Objetivo:** cerrar evidencia 07–10 y avanzar workflow 11 de UX/Admin sin perder trazabilidad ni aplicar cambios inseguros.

### Entorno vigente

```text
PBX:       192.168.1.10
J129:      192.168.1.168
MAC:       C8:1F:EA:9B:65:0D
Firmware:  3.0.0.0.20
Endpoint:  id 3
SIP:       200 / chan_sip / OK
```

`192.168.1.169` está ocupado y no debe usarse para la PBX.

### 07 — Rescan Idempotency

`LAB-INTEGRATION-PASS`: dos rescans conservaron un único endpoint, Avaya/J129 y cuenta 200.

### 08 — Single Account V1

`LAB-INTEGRATION-PASS`: LAB fijado a una cuenta SIP (`max_accounts=1`, `max_sip_accounts=1`). Deuda: normalizar installer/helper permanente antes de producción.

### 09 — Remote provisioning lifecycle

`PHYSICAL-J129-PASS`, run `33599222299`.

`check-sync` produjo reinicio físico, peer down, nuevos GET de provisioning y re-registro SIP. Decisión: no usar `check-sync` como “reload silencioso” ni en pruebas no-reboot.

### 10 — Forced Provisioning / NTP

Run exitoso `33602271998`.

`LAB-INTEGRATION-PASS` server-side: Apply estándar de Issabel regeneró provisioning con:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

SIP permaneció OK durante 300 s. No hubo nuevo GET de `46xxsettings.txt`, por lo que no afirmar aplicación física del cambio.

Riesgo detectado: tras restart de chronyd el sample inmediato mostró temporalmente Stratum 0 / Not synchronised. Antes de producción el workflow debe esperar y afirmar recuperación de sync.

### 11 — Phone UX & Admin baseline

Run `33603387145`: `LAB-READ-PASS`.

- SIP 200 OK.
- Web UI HTTP/HTTPS 200.
- NTP del workflow 10 presente en `46xxsettings.txt`.
- parámetros UX/idioma/Web Admin/ENTRYNAME ausentes.
- no existe XML J129 Spanish en PBX.

### 11 — intentos Apply fallidos

**Run 2 / Audit:** falló antes de Apply por usar SQLite (`no such table: endpoint`). No hubo Apply.

**Run 3 / Audit:** falló antes de Apply por asumir columna `endpoint.ip_address`. No hubo Apply.

**Run 4 / main:** usuario lanzó el workflow sobre `main`; el guard `GITHUB_REF_NAME=Audit` falló en el paso de entorno. Baseline/Apply quedaron skipped. No hubo mutación. El rojo confirma que la protección funcionó.

### Corrección de diseño descubierta

La preparación inicial del 11 proponía `PROCSTAT 1` para habilitar menú. Esto contradice la investigación vigente:

```text
PROCSTAT 0 -> Admin menu permitido
PROCSTAT 1 -> Admin menu restringido/no permitido
```

Antes de cualquier nuevo Apply debe cambiarse a `PROCSTAT 0`.

### Regla DB añadida

Endpoint Configurator del LAB usa MySQL/MariaDB `endpointconfig`, no SQLite. No asumir columnas. Reutilizar `make_db_defaults_file`, `mysql_scalar` y consultas ya validadas del workflow 10, o auditar esquema read-only antes de añadir joins/campos.

### Documentación actualizada

- `AGENTS.md`
- `docs/j129-lab-validation.md`
- `docs/j129-research-notes.md`
- `docs/agent-log.md`

### Próximo paso

1. corregir workflow/helper 11 a `PROCSTAT 0`;
2. revisar que la selección DB use únicamente consultas ya probadas;
3. ejecutar tests estáticos;
4. nuevo `Run workflow` sobre `Audit`, input `APPLY-UX`;
5. no usar rerun de SHA anterior;
6. no enviar check-sync durante observación no-reboot;
7. si server-side queda verde, pedir verificación física de menú, nombre y hora;
8. español se prueba después con XML oficial Avaya.

---

## Handoff actual

Leer en orden:

1. `AGENTS.md`
2. `docs/j129-lab-validation.md`
3. `docs/j129-research-notes.md`
4. `docs/agent-log.md`
5. runs/commits recientes de `Audit`

No continuar desde el helper del workflow 11 sin corregir `PROCSTAT` y sin reutilizar el contrato MySQL ya validado del workflow 10.
