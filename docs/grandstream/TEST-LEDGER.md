# Grandstream Endpoint Configurator Test Ledger

Documento vivo para registrar pruebas de integración Grandstream en Issabel Endpoint Configurator. No contiene contraseñas SIP, SID, cookies, tokens ni contenido binario de archivos cfg.

## Objetivo final

Endpoint Configurator debe descubrir el teléfono, asignar la extensión, generar la configuración, lograr que el teléfono la descargue automáticamente y verificar el registro SIP sin configuración manual permanente en la GUI del teléfono.

## Entorno de referencia

- Issabel 5 / Asterisk 18.19.0
- Endpoint Configurator `issabel-endpointconfig2-5.0.0-1.el8.noarch`
- PBX laboratorio: `192.168.1.10`
- Runner PBX: `issabel-lab-casa`
- Runner endpoint externo: `endpoint-lab-debian`
- Teléfono principal: Grandstream GXP1625
- IP laboratorio del teléfono: `192.168.1.167`
- Firmware GXP1625: `1.0.7.70`
- MAC usada en laboratorio: `C0:74:AD:E8:66:09`
- OUI adicional validado: `C0:74:AD`
- Extensión rollback manual: `201`
- Extensión objetivo Endpoint Configurator: `202 Ashly`

## Registro de pruebas

| ID | Estado | Propósito | Resultado / evidencia | Decisión |
|---|---|---|---|---|
| G10-19A | PASS | Inventariar provisioning nativo Issabel | Issabel genera `cfg<MAC>` binario; `Grandstream.py` contiene P212/P237/P6767; cfg presente en `/tftpboot` | Mantener generador existente mientras sea viable |
| G10-19B | PASS | Mapear P-values de provisioning | P212=Config Upgrade Via; P237=Config Server Path; P234/P235 prefijo/sufijo; P240 auth config; P1359/P1360/P1361 auth XML/HTTP | Base común para GXP1625/GXP1630 |
| G10-19C | PASS | Diagnosticar TFTP | `tftp-server` e `in.tftpd` presentes; xinetd activo; listener no evidente con `ss` | Probar RRQ real en vez de confiar solo en `ss` |
| G10-19D | PASS | Probar TFTP real | RRQ local y desde `endpoint-lab-debian` exitosos; tamaño y SHA del cfg coinciden | TFTP de Issabel queda validado; firewall no es bloqueo |
| G10-19E | PASS | Leer estado provisioning del GXP1625 | Login y lectura P-values exitosos; P212/P237 sin bootstrap útil | Se requiere bootstrap del teléfono |
| G10-19E2 | FAIL controlado | Escribir P212/P237 por API web | Login/read OK; `api.values.post` devuelve `session-expired`; valores no cambian | No asumir problema de credenciales |
| G10-19E3 | FAIL controlado | Repetir write en una sola sesión HTTP/2 | Login/read/sesión persistente OK; write sigue `session-expired` | Se descarta que HTTP/2/keepalive sea la causa |
| G10-19E4 | FAIL controlado | Reproducir request tipo navegador | Chrome real sí escribe; cliente directo no. Se identifica diferencia de cookies/sesión | Investigar `session-identity` |
| G10-19E4B | FAIL controlado | Parsear cookies legacy del firmware | Cliente obtiene `session-role`, no `session-identity`; write sigue `session-expired` | `session-identity` no viene del login HTTP directo observado |
| G10-19E4C | PASS diagnóstico | Buscar origen estático de `session-identity` | `webapp.nocache.js` no contiene literal relevante | Pasar a traza runtime con navegador real |
| G10-19E4D | PASS diagnóstico | Traza runtime con Chromium/CDP | Login UI real crea `session-identity` y `session-role`; no se observó como Set-Cookie directo; 38 eventos de red | Reproducir secuencia real del navegador, no inventar valor de cookie |
| G10-19G2 | PASS diagnóstico | Leer estado real de Account 1 después de las pruebas de provisioning | Login UI real y lectura HTTP 200; cuenta habilitada; SIP server apunta a la PBX; User ID/Auth ID siguen en `201`; nombre de cuenta no corresponde a 202 | El teléfono todavía conserva la cuenta rollback 201; 202 aún no está aplicada en Account 1 |

## Hallazgo actual

La diferencia crítica entre el cliente automatizado directo y Chrome es que el flujo real del navegador termina con una cookie `session-identity`. El login HTTP directo solo produce de forma útil `session-role`. La escritura de `api.values.post` funciona desde Chrome y falla con `session-expired` fuera de ese flujo.

La prueba G10-19E4D confirmó que `session-identity` aparece durante el flujo real de la webapp ejecutada en Chromium, pero no se detectó como un `Set-Cookie` HTTP convencional. Esto sugiere que la identidad de sesión se establece o transforma dentro del flujo de la aplicación web.

El checkpoint G10-19G2 confirma que Account 1 sigue funcionando con la extensión rollback `201` y que el SIP server ya apunta a la PBX. Por tanto, no debe declararse éxito de provisioning de `202 Ashly` hasta que una lectura posterior muestre 202 en el teléfono y Asterisk confirme su registro.

## Próximas pruebas

Las pruebas posteriores deben conservar la secuencia de evidencia y no saltarse la verificación de estado real del teléfono:

1. probar/aplicar el mecanismo de provisioning sin exponer secretos,
2. confirmar solicitud/descarga del `cfg<MAC>`,
3. releer Account 1,
4. exigir `202` como User ID/Auth ID antes de marcar provisioning exitoso,
5. comprobar registro SIP de 202 en Issabel,
6. mantener 201 documentado como rollback hasta cerrar la validación.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable para conservar evidencia aun si una validación falla.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

El workflow general `Avaya Issabel Audit Tests` es un validador de contratos del repositorio, no una prueba física del teléfono. A partir de este punto también debe publicar un resumen visible de sus unit tests para evitar runs aparentemente vacíos.

Los workflows de diagnóstico deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
