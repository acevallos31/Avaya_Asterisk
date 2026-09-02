# Validación de laboratorio — Avaya J129

Este documento registra evidencia reproducible de las pruebas de integración y ciclo de vida del Avaya J129 sobre Issabel 5. Complementa `docs/agent-log.md` y el historial de Git.

> No almacenar secretos SIP ni credenciales Web Admin reales en este archivo.

## Entorno de prueba actual

- Rama: `Audit`
- PBX de laboratorio: Issabel 5 / Rocky Linux 8
- Asterisk: 18.19.0
- PBX / servidor de provisioning actual: `192.168.1.10`
- Teléfono: Avaya J129 físico
- Firmware: `3.0.0.0.20`
- MAC: `C8:1F:EA:9B:65:0D`
- IP actual del teléfono: `192.168.1.168`
- Endpoint actual: id `3`
- Cuenta SIP actual: `200`
- Provisioning: HTTP desde la PBX
- Flujo objetivo: Endpoint Configurator estándar de Issabel, sin UI Avaya paralela para usuario/contraseña SIP.
- `192.168.1.169` está ocupado por otro dispositivo y no debe usarse para la PBX.

## Estado validado

### Descubrimiento automático

**Estado:** `PHYSICAL-J129-PASS`

Endpoint Configurator detecta automáticamente fabricante `Avaya`, modelo `J129`, y permite configurar el teléfono usando el flujo estándar de Accounts de Issabel. La detección del modelo usa `probeModel()` / `_saveModel("J129")`.

La auditoría de discovery confirmó un único J129 físico y el prefijo Avaya `C8:1F:EA`.

### Provisioning HTTP físico

**Estado:** `PHYSICAL-J129-PASS`

Cadena actual observada durante el arranque:

```text
GET /J100Supgrade.txt 200
GET /46xxsettings.txt 200
GET /c81fea9b650d.txt 200
```

El `J100Supgrade.txt` del laboratorio es un bootstrap sin actualización de firmware.

### Registro SIP

**Estado:** `PHYSICAL-J129-PASS`

El J129 registra por `chan_sip`. Estado actual validado: cuenta `200`, IP `192.168.1.168`, User-Agent Avaya J129 `3.0.0.0.20`, peer `OK`. Las auditorías no consultan ni imprimen el secreto SIP.

### Rescan repetido

**Estado:** `LAB-INTEGRATION-PASS`

Workflow `07 | Issabel Lab | J129 Rescan Idempotency | Audit` validó dos rescans consecutivos. El endpoint permaneció único con id `3`, IP `192.168.1.168`, fabricante Avaya, modelo J129 y cuenta `[200]`.

No se crearon endpoints duplicados ni se perdió la asociación de Accounts.

### Contrato de una sola cuenta para J129 v1

**Estado:** `LAB-INTEGRATION-PASS`

Workflow `08 | Issabel Lab | J129 Single Account V1 | Apply & Audit` fijó en LAB:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
cuentas_asignadas=1 [200]
```

Esto limita explícitamente J129 v1 a una cuenta SIP mientras no exista evidencia de una sintaxis multicuenta correcta para este firmware.

> Deuda técnica: normalizar estos valores en la fuente permanente de instalación DB antes de producción; actualmente parte del helper histórico todavía espera valores `2`.

### Reinicio remoto + reprovisionamiento

**Estado:** `PHYSICAL-J129-PASS`

Workflow `09 | Issabel Lab | J129 Remote Provisioning Reload | Audit`, run `33599222299`, validó físicamente el comportamiento real del evento SIP `check-sync` sobre firmware `3.0.0.0.20`.

Baseline:

```text
Cuenta=200
IP=192.168.1.168
Status=OK (17 ms)
Useragent=Avaya J129 IP Phone 3.0.0.0.20
```

Se envió exactamente un NOTIFY `aastra-check-cfg` / `Event=>check-sync`.

A los 45 segundos se observó que el peer dejó de estar disponible/OK:

```text
RESTART_EVIDENCE=peer-down-or-not-ok t=45s
```

Después del arranque el teléfono volvió a descargar:

```text
GET /J100Supgrade.txt 200
GET /46xxsettings.txt 200
GET /c81fea9b650d.txt 200
```

Finalmente volvió a registrar:

```text
Addr->IP : 192.168.1.168
Status   : OK (41 ms)
Useragent: Avaya J129 IP Phone 3.0.0.0.20
SIP_REREGISTRATION=PASS
RESTART_DOWN_OBSERVED=1
J129-REMOTE-RESTART-PROVISIONING-PASS
```

### Conclusión del workflow 09

En este J129/firmware, `check-sync` **no debe documentarse como una recarga silenciosa**. La evidencia física demuestra un **reinicio remoto seguido de reprovisionamiento y nuevo registro SIP**.

Esto proporciona una ruta de recuperación remota validada antes de modificar parámetros de Web Admin o menú local.

## Línea base física de pantalla — 2026-09-02

Antes de las siguientes pruebas se observó físicamente:

- En reposo el J129 muestra la hora.
- La hora mostrada está desactualizada.
- Al pulsar flecha abajo aparece la extensión `200`.
- No se muestra el nombre `Briam` en la pantalla, aunque el provisioning actual contiene `DISPLAY_NAME "Briam"`.
- Las softkeys visibles son `Redial` y `Contacts`.

Estas observaciones son evidencia física y no deben confundirse con una afirmación sobre la semántica de parámetros Avaya todavía no investigados.

## Próxima investigación funcional

### Workflow 10 — Forced Provisioning sin reinicio

Objetivo: determinar si el J129 permite forzar una nueva lectura/aplicación del provisioning **sin reiniciar el teléfono**.

Criterio deseado:

```text
cambio controlado
-> Apply Issabel
-> archivo provisioning actualizado
-> trigger remoto distinto del check-sync que reinicia
-> nuevo GET de provisioning
-> SIP permanece OK / sin transición de caída
-> cambio aplicado físicamente
```

Se investigarán primero mecanismos oficiales soportados por J129/Open SIP. No se enviarán eventos SIP o parámetros inventados a producción.

Un candidato de prueba será un cambio visible y reversible relacionado con hora/NTP o etiqueta de pantalla, una vez confirmados los parámetros oficiales.

### Workflow 11 — Web Admin + menú local en pantalla

Objetivos:

1. Administrar Web Admin mediante provisioning sin exponer credenciales.
2. Investigar y habilitar de forma controlada las opciones administrativas necesarias en el menú físico del J129.
3. Determinar el parámetro correcto para nombre/label visible de la línea; `DISPLAY_NAME` por sí solo no ha producido el nombre visible esperado.
4. Corregir sincronización de hora mediante parámetros oficiales de NTP/SNTP, zona horaria y DST apropiados para el entorno.

No se habilitarán `PROCPSWD`, `PROCSTAT`, `PROVIDE_LOGOUT`, `FORCE_WEB_ADMIN_PASSWORD` u otros parámetros a ciegas. Primero se verificará su semántica oficial y compatibilidad con firmware `3.0.0.0.20`.

## BUG-EC-001 — `Registered at` puede mostrar un peer SIP obsoleto

**Estado:** reproducido.

Después de cambiar la extensión, Endpoint Configurator puede mostrar `Registered at` para una cuenta antigua aunque Asterisk muestre esa cuenta `UNREACHABLE` y la actual `OK`. Para auditorías la fuente autoritativa es Asterisk: cuenta esperada + IP esperada + estado.

## BUG-J129-002 — Multicuenta

**Estado:** reproducido; limitado explícitamente para v1.

Con dos cuentas, el template histórico repetía parámetros globales `FORCE_SIP_*`; físicamente solo una identidad terminó registrada. J129 v1 queda limitado a una cuenta mediante `max_accounts=1` y `max_sip_accounts=1` hasta investigar sintaxis oficial multicuenta.

## BUG-J129-003 — Apply con cero cuentas conserva provisioning SIP anterior

**Estado:** `LAB-FIX-PASS` para limpieza server-side.

`Avaya.Endpoint.updateLocalConfig()` fue corregido para reutilizar `BaseEndpoint.deleteContent()`, marcar el endpoint configurado y devolver éxito cuando no hay cuentas. El archivo específico por MAC se elimina del servidor.

Commits originales de la corrección:

```text
38ea0566a1fe6e2a46004b9d7aad4156fa568c35  test(j129): cubrir apply con cero cuentas
efaa562190ef4afbfd4c91379b13d4246ad39515  fix(j129): revocar provisioning al quedar sin cuentas
```

## BUG-J129-004 — Persistencia local de identidad SIP

**Estado:** comportamiento físico reproducido; pendiente una revocación remota documentada.

Eliminar el archivo por MAC revoca el secreto almacenado en el servidor, pero no obliga al J129 a borrar una identidad SIP que ya persistió localmente. La ausencia del archivo no equivale a una instrucción de limpieza del teléfono.

Un factory reset permitió establecer nuevamente una línea base limpia. No se debe ocultar esta limitación mediante parámetros vacíos o hacks sin documentación oficial.

## Seguridad

- Nunca almacenar secretos SIP reales en documentación, fixtures o logs.
- Nunca imprimir contraseña Web Admin, cookies, XToken, nonce o hashes de autenticación.
- La credencial Web Admin usada anteriormente debe considerarse expuesta y rotarse antes de producción.
- `J129_WEB_PASSWORD` debe mantenerse únicamente como GitHub Repository Secret cuando vuelva a utilizarse.
- Los workflows mantienen sudo restringido a los helpers autorizados; no conceder sudo amplio al runner.

## Pendientes para J129 v1 / hardening

- Workflow 10: investigar y validar forced provisioning sin reboot, o documentar formalmente que no es soportado en este firmware.
- Workflow 11: Web Admin, menú físico, hora/NTP y label visible.
- Añadir prueba negativa: Issabel debe impedir una segunda cuenta para J129 v1.
- Bulk Apply sin impacto en otros vendors.
- Casos controlados: extensión inválida/no existente y teléfono offline durante Apply.
- Rollback/reinstall final del overlay.
- Normalizar helper permanente: eliminar IPs históricas hardcodeadas y runtime patches.
- Normalizar instalación DB permanente a una cuenta para v1.
- Retirar mecanismos temporales de privilegios/sincronización antes de producción.
- Resolver `BUG-J129-004` o documentarlo explícitamente como limitación de v1.
- Corregir o aislar `BUG-EC-001` separadamente del vendor Avaya.

## Criterio de evidencia

Las observaciones físicas/capturas de GUI son evidencia complementaria. Para DB, archivos de provisioning, requests HTTP y registro SIP se priorizan workflows de auditoría y salida directa de Asterisk, siempre sin exponer secretos.
