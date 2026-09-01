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

**Estado:** `LAB-INTEGRATION-PASS` como reproducción y `LAB-FIX-PASS` para la limpieza server-side.

Con la implementación anterior, retirar la última cuenta hacía fallar `updateLocalConfig()` y dejaba el archivo MAC con las credenciales anteriores. Se añadió un contrato automatizado y se cambió `Avaya.Endpoint.updateLocalConfig()` para reutilizar `BaseEndpoint.deleteContent()`, marcar el endpoint configurado y devolver éxito.

Commits:

```text
38ea0566a1fe6e2a46004b9d7aad4156fa568c35  test(j129): cubrir apply con cero cuentas
efaa562190ef4afbfd4c91379b13d4246ad39515  fix(j129): revocar provisioning al quedar sin cuentas
```

Después de desplegar la corrección, el Apply general terminó sin errores y `Issabel Lab J129 Provisioning Audit #9` mostró:

```text
CUENTAS ASIGNADAS (SIN SECRETOS)
<vacío>
/tftpboot/c81fea9b650d.txt AUSENTE
/tftpboot/46xxsettings.txt PRESENTE
/tftpboot/J100Supgrade.txt PRESENTE
J129-PROVISIONING-AUDIT-PASS
```

Esto cierra la limpieza server-side del archivo secreto por MAC, pero no implica por sí solo que el teléfono borre la identidad SIP que ya tenía almacenada localmente.

## BUG-J129-004 — El J129 conserva la identidad SIP local cuando desaparece el archivo MAC

**Estado:** `PHYSICAL-J129-PASS` como reproducción del comportamiento; revocación física pendiente.

### Preparación

Después de corregir `BUG-J129-003`, el servidor quedó con:

```text
endpoint J129 existente
0 cuentas asignadas
/tftpboot/c81fea9b650d.txt AUSENTE
46xxsettings.txt PRESENTE
J100Supgrade.txt PRESENTE
```

`Issabel Lab J129 State Audit` en `configured_no_accounts` terminó verde antes del reboot.

### Evidencia física después del reboot

El J129 fue reiniciado sin introducir ninguna cuenta ni credencial manualmente. Después del arranque, Asterisk mostró:

```text
200/200   (Unspecified)      UNKNOWN
201/201   192.168.1.171      OK
```

Por tanto, el teléfono volvió a registrar con `201` aunque:

- Endpoint Configurator tenía cero cuentas asignadas;
- el archivo específico por MAC ya no existía en el servidor;
- el Apply general anterior había terminado correctamente.

El State Audit `configured_no_accounts` también terminó verde después del reboot, lo que confirma una limitación de esa auditoría: valida estado de Endpoint Configurator/provisioning server-side, pero todavía no demuestra ausencia de una identidad SIP persistente en el teléfono.

### Conclusión

Eliminar el archivo por MAC revoca el secreto almacenado en el servidor, pero **no ordena al J129 borrar la configuración SIP que ya tenía persistida localmente**. La ausencia del archivo específico no equivale a una instrucción de limpieza del teléfono.

No se debe considerar cerrado el caso de cero cuentas hasta encontrar una forma documentada y segura de limpiar/deshabilitar la identidad SIP del J129 mediante provisioning.

### Pendiente

- Revisar documentación oficial Avaya J129/Open SIP para parámetros soportados que borren o deshabiliten una cuenta SIP previamente provisionada.
- No inventar valores vacíos ni repetir `FORCE_SIP_*` sin evidencia documental y tests.
- Diseñar un archivo MAC de estado `no_accounts` solo si existe una semántica oficial y segura para revocar la identidad local.
- Añadir una auditoría específica que, en `configured_no_accounts`, falle si Asterisk todavía ve una cuenta anterior `OK` desde la IP del J129.
- Repetir Apply + reboot y exigir que ninguna cuenta SIP anterior quede `OK`.

## Pruebas pendientes para cerrar J129 v1

- Resolver `BUG-J129-004` y repetir la prueba física con cero cuentas.
- Segunda validación completa de `Remove configuration`, incluyendo existencia/hash del archivo por MAC y estado real del teléfono.
- Rescan repetido sin endpoints duplicados.
- Bulk Apply sin impacto en otros vendors.
- Casos controlados: extensión inválida/no existente y teléfono offline durante Apply.
- Rollback/reinstall final del overlay.
- Retirar mecanismos temporales de privilegios/sincronización antes de producción.
- Resolver o limitar explícitamente el soporte multicuenta descrito en `BUG-J129-002`.
- Corregir o aislar `BUG-EC-001` después de cerrar las pruebas funcionales del vendor.

## Criterio de evidencia

Las capturas de GUI son evidencia complementaria. Para DB, archivos de provisioning y registro SIP se priorizan los workflows de auditoría y la salida directa de Asterisk, siempre sin exponer secretos.
