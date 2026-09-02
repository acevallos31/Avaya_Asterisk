# Validación de laboratorio — Avaya J129

> Evidencia reproducible del J129 físico sobre Issabel 5. No almacenar secretos SIP ni credenciales Web Admin reales.

## Entorno actual — 2026-09-02

- Rama de pruebas: `Audit`
- Issabel 5 / Rocky Linux 8
- Asterisk 18.19.0
- Python 3.6.8
- PBX / provisioning: `192.168.1.10`
- J129: `192.168.1.168`
- MAC: `C8:1F:EA:9B:65:0D`
- Firmware: `3.0.0.0.20`
- Endpoint id: `3`
- Cuenta SIP: `200`
- Runner self-hosted: usuario `github-runner`
- `192.168.1.169` está ocupado por otro dispositivo y no debe asignarse a la PBX.

## Evidencia consolidada

### Discovery / Accounts / provisioning

`PHYSICAL-J129-PASS`:

```text
J100Supgrade.txt -> 46xxsettings.txt -> c81fea9b650d.txt
```

Endpoint Configurator identifica Avaya/J129 y usa Accounts estándar. No existe UI SIP paralela.

### SIP

`PHYSICAL-J129-PASS`: cuenta `200`, IP `192.168.1.168`, `chan_sip`, peer `OK`. Asterisk es la fuente autoritativa de registro.

### 07 — Rescan Idempotency

`LAB-INTEGRATION-PASS`: dos rescans conservaron exactamente un J129, endpoint id 3 y cuenta 200.

### 08 — Single Account V1

`LAB-INTEGRATION-PASS`:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

### 09 — Remote restart + reprovisioning

`PHYSICAL-J129-PASS` — run `33599222299`.

El evento SIP `check-sync` produjo caída del peer, reinicio físico, nueva descarga HTTP y re-registro SIP. En firmware `3.0.0.0.20` no debe llamarse “reload silencioso”.

### 10 — Forced Provisioning / NTP

`LAB-INTEGRATION-PASS` server-side — run `33602271998`.

Apply normal de Issabel cargó exactamente un endpoint y regeneró provisioning con:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

Durante 300 s SIP permaneció `OK`, no se envió NOTIFY/check-sync y el J129 no realizó un nuevo GET observado de `46xxsettings.txt`.

Más tarde, tras reiniciar el teléfono durante la validación del workflow 11, la hora quedó correcta. Esto confirma físicamente que la configuración de tiempo sí es funcional cuando el J129 la consume.

Deuda: después de reiniciar chronyd, el test debe esperar y afirmar recuperación del estado sincronizado antes de considerarlo listo para producción.

## Línea base física de pantalla

Antes del workflow 11:

- idle mostraba hora incorrecta/desactualizada;
- flecha abajo mostraba extensión `200`;
- `Briam` no aparecía en idle;
- softkeys en inglés: `Redial`, `Contacts`;
- no había acceso visible a softkey/menu Admin.

`DISPLAY_NAME "Briam"` no produjo el resultado visible esperado.

## 11 — Phone UX & Admin

### Baseline read-only — PASS

Run `33603387145`:

- SIP 200 OK;
- Web UI HTTP/HTTPS 200;
- parámetros NTP presentes;
- parámetros UX/idioma/Web Admin/ENTRYNAME ausentes;
- no existe XML J129 Spanish en PBX.

### Apply UX/Admin — PASS server-side

El Apply corregido generó:

```text
SET PROCSTAT 0
SET PROVIDE_OPTIONS_SCREEN 1
SET PROVIDE_NETWORKINFO_SCREEN 1
SET PROVIDE_LOGOUT 1
SET ENTRYNAME Briam
```

Además preservó NTP.

### Reinicio controlado / evidencia física

El teléfono cayó y volvió a registrar SIP, confirmando el ciclo de reinicio. El detector HTTP del workflow dio falsos negativos/observabilidad insuficiente y no debe usarse como prueba negativa del consumo.

Después del reinicio:

- la hora quedó correcta;
- el menú visible no apareció.

Conclusión: el tiempo quedó validado físicamente; los parámetros UX no deben incluirse en la release mínima v0.1.0 sin más evidencia.

## 12 — Production Patch | Install & Rollback Test

Estado: `LAB-INTEGRATION-PASS`.

Workflow:

```text
12 | Issabel Lab | J129 Production Patch | Install & Rollback Test
```

El candidato de parche mínimo completó en LAB:

```text
preflight
-> install
-> verify
-> segundo install
-> segundo verify
-> rollback
```

El segundo install valida idempotencia y el rollback deja el LAB en el estado previo esperado.

Este PASS valida el candidato de parche dentro de la estructura de Audit, pero no sustituye la prueba del paquete autocontenido exacto de la rama de release.

## 13 — Release Package | Smoke Test

Workflow:

```text
13 | Issabel Lab | J129 Release Package | Smoke Test
```

Objetivo: checkout de `release/j129-v0.1.0` y ejecutar el ciclo exacto del paquete distribuible.

Estado actual: `INFRA-BLOCKED`, no `RELEASE-FAIL`.

### Primer rojo

Una ejecución falló durante checkout/limpieza por residuos `.pyc` creados por root de pruebas anteriores.

### Rojo vigente

Error observado:

```text
Error: File was unable to be removed
Error: EACCES: permission denied, unlink
'/opt/actions-runner/_work/Avaya_Asterisk/Avaya_Asterisk/deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/__pycache__/Avaya.cpython-36.pyc'
```

### Causa

- El runner es self-hosted.
- `actions/checkout` corre como `github-runner`.
- Un proceso privilegiado anterior creó `__pycache__/Avaya.cpython-36.pyc` como `root` dentro del workspace.
- Checkout intenta limpiar el repositorio antes de ejecutar cualquier step posterior.
- `github-runner` no puede borrar ese archivo y el job muere antes de probar la release.

Por tanto, no existe evidencia todavía de que el paquete exacto v0.1.0 falle funcionalmente.

### Corrección requerida

Una limpieza puntual del residuo root-owned debe hacerse fuera del checkout que está fallando. Después, el harness debe impedir que root vuelva a generar bytecode dentro del workspace.

Controles requeridos:

```text
PYTHONDONTWRITEBYTECODE=1
python3 -B para Python privilegiado
no temporales root dentro de $GITHUB_WORKSPACE
usar /tmp o /var/lib para estado privilegiado
no chmod 777
no sudo amplio
```

Agregar comprobaciones de ownership y ausencia de `__pycache__` root-owned alrededor de acciones privilegiadas cuando sea posible.

## Release v0.1.0

Rama limpia:

```text
release/j129-v0.1.0
```

El paquete no debe incluir configuraciones estáticas históricas de teléfonos. `46xxsettings.txt` debe generarlo Issabel.

El archivo histórico `46xxsettings.txt funciona Choloma.txt` puede conservarse como referencia conocida funcional únicamente si se revisa por secretos y se mueve/renombra fuera del payload, por ejemplo:

```text
examples/j129-working-reference-choloma.txt
```

## Idioma español

Fuera de v0.1.0. Requiere XML oficial Avaya y validación física.

## BUGS / deuda técnica

### BUG-EC-001
`Registered at` en GUI puede quedar obsoleto. Usar Asterisk para registro real.

### BUG-J129-002
Multicuenta histórica incorrecta. Mitigado en v1 con una cuenta.

### BUG-J129-003
Apply con cero cuentas fue corregido server-side usando `BaseEndpoint.deleteContent()`.

### BUG-J129-004
La ausencia del archivo por MAC no borra identidad SIP ya persistida en el J129.

### TD-J129-005 — consumo inmediato
Apply normal no fuerza polling inmediato. `check-sync` reinicia físicamente este firmware.

### TD-J129-006 — menú local
No resuelto; no bloquear v0.1.0 mínima.

### TD-J129-007 — observabilidad HTTP
Corregir lectura autorizada de access logs.

### TD-J129-008 — idioma
Falta XML oficial Latin American Spanish.

### TD-J129-009 — helpers LAB
Eliminar hardcodes/runtime patching y normalizar comportamiento.

### TD-J129-010 — ownership del self-hosted runner
Procesos root no deben crear `__pycache__` ni otros artefactos dentro del checkout. Esta deuda bloquea actualmente workflow 13.

## Seguridad

- No registrar SIP secrets reales.
- No imprimir contraseña Web Admin, cookies, XToken, nonce ni hashes.
- Rotar credencial Web Admin expuesta antes de producción.
- No ampliar sudo del runner.
- No subir Phone Reports brutos.
- No usar permisos globales como `chmod -R 777` para resolver ownership.

## Criterio para primera distribución

La distribución debe conservar:

1. preflight de versión/archivos/DB;
2. backup de cada archivo tocado;
3. integración Avaya/J129 mínima;
4. DB idempotente;
5. una cuenta SIP;
6. sin firmware automático;
7. sin cambio automático de Web Admin password;
8. verify posterior;
9. rollback;
10. paquete exacto validado por workflow 13 antes de producción.

## Próximo paso

1. limpiar el residuo root-owned que bloquea checkout;
2. modificar la ejecución privilegiada para usar Python sin bytecode y no escribir dentro del workspace;
3. lanzar un run nuevo de workflow 13 en `Audit` con `TEST-RELEASE`;
4. revisar logs del ciclo real de release;
5. si queda verde, congelar v0.1.0 y generar checksums;
6. auditar la central de producción antes de instalar.
