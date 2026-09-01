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

**Estado:** `LAB-INTEGRATION-PASS` como reproducción del defecto; prueba física posterior pendiente.

### Preparación

El J129 permanecía detectado en Endpoint Configurator pero se eliminó su última cuenta `201`. La DB quedó con cero asociaciones en `endpoint_account` y el State Audit `configured_no_accounts` terminó verde antes del Apply general.

### Apply general

Al ejecutar `Apply configuration to all selected endpoints`, Endpoint Configurator cargó normalmente el endpoint y ejecutó la configuración global Avaya, pero la configuración local terminó con:

```text
ERROR: (Avaya) Endpoint Avaya@192.168.1.171 no tiene cuentas para configurar
WARNING: (issabel-endpointconfig) ... failed configuration for endpoint Avaya@192.168.1.171
```

La causa está en `Avaya.Endpoint.updateLocalConfig()`: cuando `len(self._accounts) <= 0`, el vendor retorna `False`. Por tanto, el error no es una restricción demostrada del core de Endpoint Configurator; es comportamiento de la implementación Avaya actual.

### Evidencia de provisioning después del fallo

`Issabel Lab J129 Provisioning Audit` terminó verde como workflow de inspección, pero su contenido demostró el defecto:

- Endpoint Avaya/J129 sigue presente.
- `CUENTAS ASIGNADAS` está vacío.
- `/tftpboot/c81fea9b650d.txt` sigue presente.
- El archivo por MAC conserva `DISPLAY_NAME` de la cuenta anterior.
- Conserva `FORCE_SIP_USERNAME`.
- Conserva `FORCE_SIP_EXTENSION "201"`.
- Conserva `FORCE_SIP_PASSWORD` (existencia confirmada, valor oculto).
- El `mtime` del archivo por MAC permanece anterior al Apply fallido.
- `46xxsettings.txt` y `J100Supgrade.txt` sí fueron regenerados durante el Apply general.

Esto demuestra que el Apply global actualiza los artefactos globales, pero `updateLocalConfig()` aborta antes de limpiar/regenerar el archivo específico por MAC. El provisioning antiguo y material de autenticación permanecen disponibles.

### Implicación

Este comportamiento es un defecto de ciclo de vida y de seguridad: retirar la última cuenta en Endpoint Configurator no revoca por sí mismo el provisioning SIP anterior del J129. No se debe reiniciar el teléfono durante esta reproducción hasta definir y probar el comportamiento correcto para cero cuentas.

### Pendiente

- Añadir una prueba automatizada que reproduzca `_accounts=[]` con un archivo MAC preexistente.
- Definir el comportamiento correcto siguiendo el contrato de Issabel: limpiar/eliminar de forma segura el provisioning específico sin convertir el caso en un error engañoso.
- Confirmar cómo debe marcarse el endpoint (`configured`/sin cuenta) sin modificar el core innecesariamente.
- Repetir Apply con cero cuentas después de la corrección y exigir ausencia de `FORCE_SIP_USERNAME`, `FORCE_SIP_PASSWORD`, `FORCE_SIP_EXTENSION` y datos de la cuenta anterior.
- Solo después reiniciar el J129 y verificar físicamente que no conserva el registro SIP anterior.

## Pruebas pendientes para cerrar J129 v1

- Corregir y repetir `BUG-J129-003` con cero cuentas.
- Reiniciar el J129 sin cuentas después de demostrar que el provisioning anterior fue revocado.
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
