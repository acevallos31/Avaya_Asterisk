# Agent Audit Log

Registro compartido de trabajo humano/IA en `Avaya_Asterisk`. Consultar primero `AGENTS.md` y `CONTEXT.md`. No almacenar secretos reales.

Estados usados: `STATIC-PASS`, `LAB-READ-PASS`, `LAB-INTEGRATION-PASS`, `LAB-FIX-PASS`, `PHYSICAL-J129-PASS`, `INFRA-BLOCKED`, `RELEASE-PASS`, `PRODUCTION-REFERENCE`, `NOT-TESTED`.

---

## 2026-08-31 — OpenAI-GPT-5.6-Sol

Se consolidó el contrato de arquitectura J129: core Issabel stock, Accounts estándar, Avaya consume `_accounts`, provisioning global -> `GET $MACADDR.txt` -> archivo por MAC, sin consultas directas de secretos desde vendor. Se añadieron contratos SOLID/golden y fixtures ficticios.

## 2026-09-01 — OpenAI-GPT-5.6-Sol

Se validó físicamente discovery, provisioning HTTP, registro SIP y lifecycle. Se registraron `BUG-EC-001`, `BUG-J129-002`, `BUG-J129-003` y `BUG-J129-004`. `BUG-J129-003` quedó corregido server-side usando `BaseEndpoint.deleteContent()` cuando no hay cuentas. `BUG-J129-004` sigue abierto.

## 2026-09-02 — OpenAI-GPT-5.6-Sol

### Entorno vigente

```text
PBX:       192.168.1.10
J129:      192.168.1.168
MAC:       C8:1F:EA:9B:65:0D
Firmware:  3.0.0.0.20
Endpoint:  id 3
SIP:       200 / chan_sip / OK
Runner:    github-runner / self-hosted
```

`192.168.1.169` está ocupado y no debe usarse para la PBX.

### 07 — Rescan Idempotency

`LAB-INTEGRATION-PASS`: dos rescans conservaron un único endpoint, Avaya/J129 y cuenta 200.

### 08 — Single Account V1

`LAB-INTEGRATION-PASS`: una cuenta SIP (`max_accounts=1`, `max_sip_accounts=1`, `max_iax2_accounts=0`).

### 09 — Remote provisioning lifecycle

`PHYSICAL-J129-PASS`, run `33599222299`.

`check-sync` produjo reinicio físico, peer down, nuevos GET de provisioning y re-registro SIP. No usar como reload silencioso.

### 10 — Forced Provisioning / NTP

Run `33602271998`: `LAB-INTEGRATION-PASS` server-side.

Provisioning generado:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

No hubo polling natural en 300 s. Después, durante reinicio asociado a workflow 11, la hora del teléfono quedó correcta: evidencia física de que la configuración NTP funciona cuando se consume.

### 11 — Phone UX & Admin

Baseline PASS. Apply server-side llegó a generar:

```text
SET PROCSTAT 0
SET PROVIDE_OPTIONS_SCREEN 1
SET PROVIDE_NETWORKINFO_SCREEN 1
SET PROVIDE_LOGOUT 1
SET ENTRYNAME Briam
```

Después del reinicio:

- hora correcta;
- menú visible todavía ausente.

Decisión: UX/menu no entra en v0.1.0 mínima.

### 12 — Production Patch

Workflow:

```text
12 | Issabel Lab | J129 Production Patch | Install & Rollback Test
```

Resultado: `LAB-INTEGRATION-PASS`.

Ciclo completado:

```text
preflight -> install -> verify -> install -> verify -> rollback
```

Se valida instalación, verify, idempotencia y rollback del candidato de parche dentro del LAB.

### Rama limpia de release

Se creó y usa:

```text
release/j129-v0.1.0
```

No se debe hacer merge completo desde `Audit`. La rama de release contiene únicamente el paquete necesario y documentación.

Alcance v0.1.0:

- integración J129 estándar;
- una cuenta SIP;
- provisioning y Apache;
- installer autocontenido;
- no firmware;
- no español;
- no menú experimental;
- no gestión automática de password Web Admin;
- no reboot automático durante instalación.

### Referencias 46xxsettings

Se confirmó que `46xxsettings.txt funciona Choloma.txt` es un archivo histórico de una configuración funcional. No es requerido por la release y no debe estar dentro del payload.

Si se conserva como evidencia, debe sanitizarse y renombrarse fuera del payload, por ejemplo:

```text
examples/j129-working-reference-choloma.txt
```

El `46xxsettings.txt` operativo debe ser generado por Issabel desde la plantilla.

### 13 — Release Package Smoke Test

Workflow:

```text
13 | Issabel Lab | J129 Release Package | Smoke Test
```

Objetivo: probar exactamente el paquete de `release/j129-v0.1.0`.

Estado actual: `INFRA-BLOCKED`.

Error vigente reportado:

```text
Error: File was unable to be removed
Error: EACCES: permission denied, unlink
'/opt/actions-runner/_work/Avaya_Asterisk/Avaya_Asterisk/deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/__pycache__/Avaya.cpython-36.pyc'
```

Diagnóstico:

1. `actions/checkout` corre como `github-runner`;
2. una ejecución privilegiada anterior creó `__pycache__/Avaya.cpython-36.pyc` como root dentro del workspace;
3. checkout intenta limpiar el repositorio antes de ejecutar steps;
4. `github-runner` no puede borrar el archivo root-owned;
5. el job termina antes de probar `install.sh`.

Clasificación correcta: `INFRA-BLOCKED`, no `RELEASE-FAIL`.

### Corrección requerida del runner

Primero hacer limpieza puntual del residuo root-owned fuera del checkout que falla. Después impedir recurrencia:

```text
PYTHONDONTWRITEBYTECODE=1
python3 -B para Python privilegiado
no escribir temporales root dentro de $GITHUB_WORKSPACE
usar /tmp o /var/lib para estado privilegiado
no chmod -R 777
no ampliar sudo
```

Un step posterior al checkout no puede reparar el archivo que hace fallar ese mismo checkout.

### Documentación actualizada

- `AGENTS.md`
- `CONTEXT.md` creado como handoff consolidado
- `docs/j129-lab-validation.md`
- `docs/j129-research-notes.md`
- `docs/agent-log.md`
- README de release debe mantenerse sincronizado con el estado real del paquete

### Próximo paso

1. limpiar una sola vez el `.pyc` root-owned que bloquea checkout;
2. endurecer ejecución privilegiada para que no genere bytecode en el workspace;
3. nuevo Run workflow 13 sobre `Audit` con `TEST-RELEASE`;
4. revisar si ahora sí entra al ciclo `preflight/install/verify/install/verify/rollback`;
5. si queda verde, marcar `RELEASE-PASS`, generar SHA256 y congelar v0.1.0;
6. luego auditar la central de producción antes de instalar.

---

## Handoff actual

Leer en orden:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `docs/j129-lab-validation.md`
4. `docs/j129-research-notes.md`
5. `docs/agent-log.md`
6. `release/j129-v0.1.0/README.md` para distribución
7. runs/commits recientes de `Audit` y `release/j129-v0.1.0`

No continuar investigación de UX como prioridad mientras workflow 13 esté bloqueado. La prioridad es cerrar la v0.1.0 mínima y reproducible.
