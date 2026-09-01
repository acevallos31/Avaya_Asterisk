# Validación de laboratorio — Avaya J129

Este documento registra evidencia reproducible de las pruebas de integración y ciclo de vida del Avaya J129 sobre Issabel 5. Complementa `docs/agent-log.md` y el historial de Git.

> No almacenar secretos SIP reales en este archivo.

## Entorno de prueba

- Rama: `Audit`
- PBX de laboratorio: Issabel 5 / Rocky Linux 8
- Asterisk: 18.19.0
- Teléfono: Avaya J129 físico
- IP del teléfono en laboratorio: `192.168.1.171`
- Provisioning: HTTP desde la PBX
- Flujo objetivo: Endpoint Configurator estándar de Issabel, sin UI Avaya paralela para usuario/contraseña SIP.

## Estado validado

### Descubrimiento automático

**Estado:** `PHYSICAL-J129-PASS`

El Endpoint Configurator detecta automáticamente fabricante `Avaya`, modelo `J129`, y permite configurar el teléfono usando el flujo estándar de Accounts de Issabel. La detección del modelo usa `probeModel()` / `_saveModel("J129")`.

### Provisioning HTTP físico

**Estado:** `PHYSICAL-J129-PASS`

Cadena observada durante el arranque:

```text
GET /J100Supgrade.txt 200
GET /46xxsettings.txt 200
GET /<mac-normalizada>.txt 200
```

El `J100Supgrade.txt` del laboratorio es un bootstrap sin actualización de firmware.

### Registro SIP

**Estado:** `PHYSICAL-J129-PASS`

El J129 registra por `chan_sip`. La auditoría valida cuenta + IP del teléfono sin imprimir secretos.

### Ciclo Remove -> Rescan -> Reassign -> Apply -> Reboot

**Estado:** `PHYSICAL-J129-PASS`

Se comprobó el ciclo completo de Remove, rescan, reasignación, Apply principal, reboot, reprovisioning HTTP y registro SIP correcto. `Issabel Lab J129 State Audit` en `configured` termina verde.

### Cambio de extensión

**Estado:** `PHYSICAL-J129-PASS`

Se comprobó que guardar Accounts modifica la asociación de Endpoint Configurator; el Apply principal regenera provisioning; y el cambio de identidad SIP se vuelve efectivo después de reprovisionar/reiniciar el J129.

### Eliminación de una de dos cuentas

**Estado:** `PHYSICAL-J129-PASS`

Partiendo de prioridad 1 = `201` y prioridad 2 = `200`, se eliminó `200`, se ejecutó Apply principal y se reinició. El teléfono terminó en `201`; Asterisk mostró `201/201` `OK` y `200/200` `UNREACHABLE`. El State Audit `configured` terminó verde.

### Endpoint existente con cero cuentas antes del Apply general

**Estado:** `LAB-INTEGRATION-PASS`

Se eliminó la última cuenta `201` desde `Configure -> Accounts` y se guardó sin ejecutar todavía el Apply general ni reiniciar el teléfono. El State Audit fue ampliado con `configured_no_accounts`.

Resultado: el endpoint continúa existiendo, tiene 0 filas en `endpoint_account`, no está `removed`, y `configured_no_accounts` termina verde.

## BUG-EC-001 — `Registered at` muestra un peer SIP obsoleto

**Estado:** `LAB-INTEGRATION-PASS` como reproducción del defecto.

Después de cambiar la extensión, Endpoint Configurator puede mostrar `Registered at` para la cuenta antigua aunque Asterisk muestre esa cuenta `UNREACHABLE` y la cuenta actual `OK`. La fuente autoritativa para auditorías será Asterisk: cuenta esperada + IP esperada + estado alcanzable/registrado.

Pendiente: localizar el origen de `Registered at`, añadir prueba de regresión y corregirlo separadamente del vendor Avaya si pertenece al core/web.

## BUG-J129-002 — Dos cuentas asignadas no producen dos registros SIP independientes

**Estado:** `PHYSICAL-J129-PASS` como reproducción del defecto; soporte multicuenta funcionalmente pendiente.

Endpoint Configurator aceptó prioridad 1 = `201` y prioridad 2 = `200`, con `max_accounts=2`. El archivo por MAC repitió parámetros `FORCE_SIP_*`, pero después del reboot Asterisk mostró `200` `OK` y `201` `UNREACHABLE`: la segunda identidad sustituyó a la primera.

Pendiente: investigar sintaxis oficial multicuenta J129/Open SIP y corregir template/metadata según evidencia; no repetir parámetros a ciegas.

## BUG-J129-003 — Apply con cero cuentas conserva provisioning SIP anterior

**Estado:** `LAB-INTEGRATION-PASS` como reproducción y `LAB-FIX-PASS` para la corrección server-side; validación física después del reboot pendiente.

### Reproducción

El J129 permanecía detectado en Endpoint Configurator pero se eliminó su última cuenta `201`. La DB quedó con cero asociaciones en `endpoint_account` y el State Audit `configured_no_accounts` terminó verde antes del Apply general.

Con la implementación anterior, el Apply general terminaba con:

```text
ERROR: (Avaya) Endpoint Avaya@192.168.1.171 no tiene cuentas para configurar
WARNING: (issabel-endpointconfig) ... failed configuration for endpoint Avaya@192.168.1.171
```

`Issabel Lab J129 Provisioning Audit` demostró que el archivo por MAC antiguo permanecía y todavía contenía identidad y material de autenticación de `201`, mientras los archivos globales sí habían sido regenerados.

### Corrección

Se añadió un contrato automatizado para `_accounts=[]` y se modificó `Avaya.Endpoint.updateLocalConfig()` para reutilizar `BaseEndpoint.deleteContent()`, marcar el endpoint configurado y devolver éxito en lugar de abortar dejando provisioning obsoleto.

Commits de la corrección:

```text
38ea0566a1fe6e2a46004b9d7aad4156fa568c35  test(j129): cubrir apply con cero cuentas
efaa562190ef4afbfd4c91379b13d4246ad39515  fix(j129): revocar provisioning al quedar sin cuentas
```

### Validación server-side después de la corrección

El overlay corregido fue desplegado en el PBX LAB desde `Audit` y el Apply general se repitió con cero cuentas.

Resultado del log de Endpoint Configurator:

```text
BEGIN ENDPOINT CONFIGURATION
Loading endpoint information from database...
Loaded 1 endpoints
(1/3) global configuration update for Avaya...
(2/3) starting configuration for endpoint Avaya@192.168.1.171 (2)...
(3/3) finished configuration for endpoint Avaya@192.168.1.171 (2)...
END ENDPOINT CONFIGURATION
```

No aparece el error `no tiene cuentas para configurar` ni `failed configuration for endpoint`.

La GUI conserva el endpoint Avaya/J129 con `Assigned accounts (0)`, lo cual confirma que cero cuentas no se confunde con `Remove configuration`.

`Issabel Lab J129 Provisioning Audit #9` terminó verde y mostró:

```text
CUENTAS ASIGNADAS (SIN SECRETOS)
<vacío>
/tftpboot/c81fea9b650d.txt AUSENTE
/tftpboot/46xxsettings.txt PRESENTE
/tftpboot/J100Supgrade.txt PRESENTE
J129-PROVISIONING-AUDIT-PASS
```

Los archivos globales fueron regenerados con el mismo timestamp del Apply exitoso, mientras el archivo específico por MAC dejó de existir.

### Conclusión server-side

La corrección revoca correctamente el provisioning específico cuando el endpoint queda con cero cuentas. Ya no permanece en `/tftpboot` el archivo que contenía `FORCE_SIP_USERNAME`, `FORCE_SIP_PASSWORD`, `FORCE_SIP_EXTENSION`, display name o datos de la cuenta anterior.

El endpoint sigue detectado y administrable en Endpoint Configurator, pero sin cuentas asignadas. Esto cierra la parte server-side de `BUG-J129-003`.

### Pendiente físico

- Reiniciar el J129 sin cuentas.
- Confirmar mediante HTTP audit que solicita los artefactos globales y que el archivo MAC ya no puede descargarse.
- Confirmar mediante Asterisk que `201` deja de estar registrado/alcanzable después del reboot.
- Confirmar el comportamiento visible del teléfono sin introducir credenciales manualmente.
- Ejecutar `configured_no_accounts` después del reboot y registrar el resultado.

## Pruebas pendientes para cerrar J129 v1

- Completar la validación física post-reboot de `BUG-J129-003` con cero cuentas.
- Segunda validación completa de `Remove configuration`, incluyendo existencia/hash del archivo por MAC.
- Rescan repetido sin endpoints duplicados.
- Bulk Apply sin impacto en otros vendors.
- Casos controlados: extensión inválida/no existente y teléfono offline durante Apply.
- Rollback/reinstall final del overlay.
- Retirar mecanismos temporales de privilegios/sincronización antes de producción.
- Resolver o limitar explícitamente el soporte multicuenta descrito en `BUG-J129-002`.
- Corregir o aislar `BUG-EC-001` después de cerrar las pruebas funcionales del vendor.

## Criterio de evidencia

Las capturas de GUI son evidencia complementaria. Para DB, archivos de provisioning y registro SIP se priorizan los workflows de auditoría y la salida directa de Asterisk, siempre sin exponer secretos.
