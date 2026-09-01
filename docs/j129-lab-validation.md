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

El Endpoint Configurator detecta automáticamente:

- fabricante `Avaya`;
- modelo `J129`;
- el teléfono puede configurarse usando el flujo estándar de Accounts de Issabel.

La detección del modelo se realiza mediante el contrato estándar del vendor (`probeModel()` / `_saveModel("J129")`).

### Provisioning HTTP físico

**Estado:** `PHYSICAL-J129-PASS`

Cadena observada en el access log de Apache durante el arranque del teléfono:

```text
GET /J100Supgrade.txt 200
GET /46xxsettings.txt 200
GET /<mac-normalizada>.txt 200
```

El archivo `J100Supgrade.txt` utilizado en laboratorio es un bootstrap sin actualización de firmware; no contiene `APPNAME` ni instrucciones de descarga de firmware.

### Registro SIP

**Estado:** `PHYSICAL-J129-PASS`

El J129 registra por `chan_sip`. La auditoría valida cuenta + IP del teléfono y no imprime secretos.

### Ciclo Remove -> Rescan -> Reassign -> Apply -> Reboot

**Estado:** `PHYSICAL-J129-PASS`

Se comprobó el siguiente ciclo completo:

1. `Remove configuration` desde Endpoint Configurator.
2. Rescan del teléfono.
3. El J129 vuelve a detectarse como Avaya/J129.
4. Se reasigna una cuenta SIP mediante `Configure -> Accounts`.
5. Se ejecuta `Apply configuration to all selected endpoints`.
6. Se reinicia el J129 sin introducir credenciales SIP manualmente.
7. El teléfono vuelve a descargar provisioning por HTTP.
8. El teléfono vuelve a registrar correctamente.
9. `Issabel Lab J129 State Audit` en estado `configured` termina verde.

Esto demuestra que el flujo estándar de Issabel puede reconstruir la configuración del J129 después de eliminar el tracking del endpoint.

### Cambio de extensión

**Estado:** `PHYSICAL-J129-PASS`

Se comprobó el cambio de la cuenta asignada desde Endpoint Configurator.

Secuencia observada:

1. Se cambia la cuenta asignada en `Configure -> Accounts`.
2. Antes del Apply principal, el State Audit queda rojo porque la DB espera la nueva cuenta mientras el teléfono conserva el registro anterior.
3. Se ejecuta el Apply principal para regenerar provisioning.
4. Sin reiniciar el teléfono, el audit SIP sigue rojo: el J129 todavía conserva la identidad SIP anterior en ejecución.
5. Se reinicia el teléfono sin modificar SIP manualmente.
6. El teléfono descarga nuevamente `J100Supgrade.txt`, `46xxsettings.txt` y su archivo por MAC.
7. El teléfono registra con la nueva extensión.
8. `Issabel Lab J129 State Audit` termina verde.

Conclusión: guardar Accounts modifica la asociación en Endpoint Configurator; el Apply principal regenera provisioning; el cambio de identidad SIP se vuelve efectivo en el J129 después de reprovisionar/reiniciar.

## BUG-EC-001 — `Registered at` muestra un peer SIP obsoleto

**Estado:** `LAB-INTEGRATION-PASS` como reproducción del defecto.

### Síntoma

Después de cambiar la extensión del J129, Endpoint Configurator muestra en la lista de cuentas no asignadas una cuenta antigua con:

```text
Registered at: 192.168.1.171
```

mientras la cuenta actualmente asignada no muestra ese indicador.

### Evidencia autoritativa de Asterisk

En el mismo instante, `sip show peers` mostró el patrón:

```text
cuenta-antigua   192.168.1.171   UNREACHABLE
cuenta-actual    192.168.1.171   OK
```

Por tanto, la cuenta activa del teléfono es la cuenta actual. La cuenta antigua conserva la IP como host/contacto histórico pero está `UNREACHABLE`.

### Conclusión

El indicador `Registered at` de Endpoint Configurator no representa correctamente el estado SIP efectivo en este escenario. Parece considerar la IP asociada al peer sin discriminar adecuadamente un estado `UNREACHABLE`.

Este comportamiento se considera, por ahora, un bug de visualización/detección de estado de Endpoint Configurator y **no un fallo del provisioning Avaya J129**.

### Regla para las auditorías

Para determinar qué cuenta está realmente registrada, la evidencia autoritativa será Asterisk y se exigirá coincidencia de:

- cuenta esperada;
- IP esperada del J129;
- estado SIP alcanzable/registrado.

No se utilizará únicamente el texto `Registered at` de la GUI como prueba de registro.

### Pendiente

- Localizar en el código de Endpoint Configurator el origen de `Registered at`.
- Identificar si la GUI usa solamente `Host`, registro en DB o salida incompleta de Asterisk.
- Añadir una prueba de regresión antes de corregirlo.
- Mantener la corrección separada del vendor Avaya si el defecto pertenece al core/web de Endpoint Configurator.

## Pruebas pendientes para cerrar J129 v1

- Dos cuentas SIP simultáneas y comportamiento real del J129 con `max_accounts=2`.
- Eliminar una de dos cuentas y verificar ausencia de residuos.
- Endpoint sin cuentas y Apply controlado.
- Segunda validación completa de `Remove configuration`, incluyendo existencia/hash del archivo por MAC.
- Rescan repetido sin endpoints duplicados.
- Bulk Apply sin impacto en otros vendors.
- Casos controlados: endpoint sin cuenta, extensión inválida/no existente y teléfono offline durante Apply.
- Rollback/reinstall final del overlay.
- Retirar mecanismos temporales de privilegios/sincronización antes de producción.

## Criterio de evidencia

Las capturas de GUI son evidencia complementaria. Para DB, archivos de provisioning y registro SIP se priorizan los workflows de auditoría y la salida directa de Asterisk, siempre sin exponer secretos.
