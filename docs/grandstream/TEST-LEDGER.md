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
| G10-19E4E | PASS | Aplicar bootstrap nativo dentro de sesión Chromium real | Login UI + SID en memoria + `session-identity`/`session-role`; POST P212/P237 responde `success/right`; relectura confirma P212=0 y P237=PBX | El bloqueo `session-expired` queda superado usando el contexto real de la webapp; avanzar a reboot y prueba de fetch |
| G10-19F2 | PASS | Reiniciar de forma controlada para disparar provisioning | Reboot de sesión simple rechazado; fallback autenticado aceptado con `SAVEREBOOT`; no hubo factory reset | Esperar boot completo y verificar persistencia/fetch antes de tocar cuenta SIP |
| G10-19F3 | BLOQUEADO observabilidad | Capturar RRQ TFTP del teléfono | `tcpdump` existe pero el runner no tiene privilegio de captura; incluso `sudo -n tcpdump` no está autorizado | No interpretar ausencia de captura como ausencia de RRQ; evitar más intentos ciegos de privilegios |
| G10-19F3B | BLOQUEADO observabilidad | Buscar evidencia TFTP en logs del servidor | `journalctl` y `/var/log/messages` no son legibles para el runner; resultado RRQ=UNKNOWN | Usar transición de estado del teléfono como evidencia alternativa o helper restringido si resulta necesario |
| G10-19G2 | PASS diagnóstico | Leer estado real de Account 1 antes del bootstrap exitoso | Login UI real y lectura HTTP 200; cuenta habilitada; SIP server apunta a la PBX; User ID/Auth ID siguen en `201` | Baseline confirmado: 202 aún no estaba aplicada antes de E4E |
| G10-19E-post-reboot | TRANSITORIO | Releer P212/P237 inmediatamente después de reboot | Dos lecturas dieron timeout/connection refused mientras el teléfono seguía reiniciando | No clasificar como regresión; repetir cuando HTTP vuelva a estar disponible |

## Hallazgo actual

El hallazgo decisivo es que el GXP1625 firmware 1.0.7.70 acepta la escritura de P-values cuando la petición se ejecuta dentro de una sesión Chromium que reproduce la webapp real. G10-19E4E confirmó P212=0 y P237 apuntando a la PBX antes del reboot.

G10-19F2 confirmó después un reboot controlado aceptado (`SAVEREBOOT`). La observabilidad directa del RRQ desde la PBX sigue bloqueada por permisos del runner, por lo que el siguiente criterio fuerte será verificar, una vez que el teléfono termine de arrancar, que P212/P237 persistieron y si Account 1 cambia de `201` a `202` después de consumir el cfg generado por Issabel.

No debe declararse éxito de provisioning de `202 Ashly` hasta que una lectura posterior muestre 202 en el teléfono y Asterisk confirme su registro.

## Próximas pruebas

1. Esperar disponibilidad HTTP del GXP1625 después de G10-19F2.
2. Releer P212/P237 y confirmar persistencia tras reboot.
3. Releer Account 1 y comparar contra baseline 201.
4. Si sigue 201, verificar que el `cfg<MAC>` vigente fue generado realmente para 202 antes de repetir provisioning.
5. Si aparece 202, comprobar registro SIP de 202 en Issabel.
6. Documentar arquitectura reutilizable para GXP1630 y otros GXP16xx.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable para conservar evidencia aun si una validación falla.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

El workflow general `Avaya Issabel Audit Tests` es un validador de contratos del repositorio, no una prueba física del teléfono. También publica resumen de unit tests para evitar runs aparentemente vacíos.

Los workflows de diagnóstico deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
