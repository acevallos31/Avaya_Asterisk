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
| G10-19E4D | PASS diagnóstico | Traza runtime con Chromium/CDP | Login UI real crea `session-identity` y `session-role`; no se observó como Set-Cookie directo | Reproducir secuencia real del navegador |
| G10-19E4E | PASS temporal | Aplicar bootstrap dentro de sesión Chromium real | POST P212/P237 responde `success/right`; relectura inmediata confirma P212=0 y P237=PBX | La escritura runtime funciona, pero debe demostrarse persistencia |
| G10-19F2 | PASS | Reiniciar de forma controlada | Fallback autenticado aceptado con `SAVEREBOOT`; no hubo factory reset | Verificar persistencia después del boot |
| G10-19F3 | BLOQUEADO observabilidad | Capturar RRQ TFTP | Runner sin privilegio de `tcpdump`; `sudo -n tcpdump` tampoco autorizado | No interpretar falta de captura como falta de RRQ |
| G10-19F3B | BLOQUEADO observabilidad | Buscar RRQ en logs TFTP | Journal/messages no legibles para runner | Usar estado del teléfono o helper restringido como evidencia alternativa |
| G10-19G2-pre | PASS diagnóstico | Baseline Account 1 | Cuenta habilitada, PBX correcta, User/Auth ID=201 | 201 confirmado como rollback previo |
| G10-19E-post-reboot | FAIL funcional | Verificar persistencia P212/P237 después del reboot | Tras volver HTTP, P212 y P237 regresaron a vacío | `api.values.post` por sí solo cambia estado operativo pero no persiste en flash/config permanente |
| G10-19G2-post | PASS diagnóstico | Verificar Account 1 después del reboot | Teléfono vuelve accesible; User/Auth ID siguen en 201 | No hubo aplicación persistente de cfg hacia 202 |
| G10-19E4F | FAIL seguro | Usar página real Upgrade and Provisioning y pulsar Save and Apply | Página/labels/botón encontrados; Config Server Path se localizó; selector de Config Upgrade Via no fue mapeado, por lo que no se pulsó Save and Apply | No forzar UI a ciegas; inspeccionar forma real del control |
| G10-19E4F2 | PASS diagnóstico | Auditar forma DOM de controles de provisioning | Página tiene 4 `select`, 39 radios y 8 botones; búsqueda exacta del nodo de texto del label no lo localizó | GWT fragmenta/renderiza texto; siguiente prueba debe mapear controles por índice/valores visibles de forma read-only |

## Hallazgo actual

La sesión Chromium resuelve definitivamente el `session-expired`: G10-19E4E logró una escritura aceptada y verificable inmediatamente. Sin embargo, el reboot posterior demostró que P212/P237 vuelven a vacío. Por tanto, `api.values.post` no es suficiente para persistir estos parámetros en el GXP1625 1.0.7.70.

La ruta correcta ahora es reproducir el comportamiento de **Save and Apply** de la página real `Upgrade and Provisioning`. G10-19E4F evitó una escritura incompleta al no poder mapear con seguridad el control `Config Upgrade Via`; G10-19E4F2 confirmó que existen controles nativos suficientes, pero el DOM GWT no permite localizar el label mediante texto exacto simple.

No debe declararse éxito de provisioning de `202 Ashly` hasta que P212/P237 sobrevivan un reboot, el teléfono consuma el cfg y Account 1 muestre 202, seguido de registro SIP en Asterisk.

## Próximas pruebas

1. Mapear de forma read-only los cuatro `select` de Upgrade and Provisioning mediante sus opciones visibles, sin registrar valores sensibles.
2. Identificar inequívocamente cuál `select` contiene TFTP/HTTP/HTTPS y asociarlo a Config Upgrade Via.
3. Ejecutar Save and Apply con P212=0 y P237=PBX.
4. Reboot/verificación de persistencia.
5. Verificar Account 1: 201 -> 202.
6. Confirmar registro SIP 202 en Issabel.
7. Documentar la secuencia generalizable para GXP1630/GXP16xx.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

Los workflows deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
