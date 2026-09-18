# Validación de producción — Grandstream en Ceiba

Fecha de cierre: 2026-09-18

## Resultado

Quedó validado el flujo real de Endpoint Configuration en Ceiba para:

| Modelo | IP de prueba | Extensión | Resultado |
| --- | --- | --- | --- |
| GXP1625 | 10.3.40.29 | 4450 | PASS |
| GRP2601P | 10.3.40.42 | 4453 | PASS |
| GRP2602G | 10.3.40.43 | 4452 | PASS |

Los tres equipos fueron configurados desde la interfaz real de Endpoint
Configuration usando la contraseña administrativa actual del teléfono en
**Custom credentials** y conservaron/recuperaron su registro SIP.

## Runtime Grandstream final

Workflow:

`74 | Ceiba Production | GXP1625 Native V2 | Controlled Runtime Upgrade`

Run final:

`35363752488`

Resultado:

`success`

SHA de runtime V2:

`f145aa9bba942b9bcd5863bf591e7660e4f805c5a68bbb1b4f235444b99d5441`

Marcadores finales:

- `TEST74-START=ALREADY_V2`
- `GRANDSTREAM-PROD-CANARY-EXTENSION-GUARD-PASS`
- `GRANDSTREAM-PROD-VERIFY-PASS`
- `TEST74-GXP1625-V2-RUNTIME-PASS`
- `endpoint_discovery=DEFERRED_MANUAL_CONTROLLED`
- `phone_write=NO`

## Incidencias resueltas

### GRP26xx

El primer fallo del GRP2602G fue una credencial administrativa incorrecta. Al
definir en Custom credentials la contraseña que tenía realmente el teléfono, el
challenge login y la configuración terminaron correctamente.

### GXP1625

El runtime V1 usaba el contrato GXP140x antiguo y esperaba una respuesta JSON que
el firmware no entregaba con esa forma de sesión.

V2 porta el contrato nativo final validado en LAB:

- username + password;
- `Accept: */*`;
- Host/Referer;
- conservación de cookies;
- `session-identity=<sid>`;
- sin User-Agent curl forzado.

El GXP1625 pudo configurarse desde la UI después de instalar V2.

## Criterio de cierre

El bloque Grandstream se considera cerrado para los tres modelos anteriores.

No se considera parte de este cierre:

- discovery global automático;
- rotación automática de contraseñas;
- validación de otros modelos Grandstream;
- despliegue del vault global en una central nueva.

La siguiente validación será la instalación limpia de
`endpoint-configuration-v1.0.1-rc1` en la central de Tocoa.
