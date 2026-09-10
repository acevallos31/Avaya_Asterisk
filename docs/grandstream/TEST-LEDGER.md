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
| G10-19C | PASS | Diagnosticar TFTP | `tftp-server` e `in.tftpd` presentes; xinetd activo | Probar RRQ real |
| G10-19D | PASS | Probar TFTP real | RRQ local y desde `endpoint-lab-debian` exitosos; tamaño y SHA del cfg coinciden | TFTP de Issabel validado |
| G10-19E | PASS | Leer estado provisioning del GXP1625 | Login/read exitosos; P212/P237 inicialmente vacíos | Se requiere bootstrap |
| G10-19E2 | FAIL controlado | Escribir P212/P237 por cliente directo | `api.values.post` devuelve `session-expired` | No concluir todavía que sea problema de credenciales |
| G10-19E3 | FAIL controlado | Repetir write HTTP/2/keepalive | Sigue `session-expired` | Transporte no era suficiente |
| G10-19E4D | PASS diagnóstico | Trazar sesión Chromium real | Webapp crea `session-identity`/`session-role` | Usar navegador real para caracterizar sesión |
| G10-19E4E | PASS temporal | Escribir P212/P237 dentro de Chromium | `success/right`; relectura inmediata confirma P212=0 y P237=PBX | Escritura runtime funciona |
| G10-19F2 | PASS | Reboot controlado | Fallback autenticado aceptado con `SAVEREBOOT`; sin factory reset | Verificar estado post-boot |
| G10-19F3 | BLOQUEADO observabilidad | Capturar RRQ TFTP | Runner sin privilegio de captura | No inferir ausencia de RRQ |
| G10-19F3B | BLOQUEADO observabilidad | Buscar RRQ en logs | Journal/messages no legibles | Usar evidencia alternativa |
| G10-19G2-pre | PASS diagnóstico | Baseline Account 1 | Cuenta habilitada, PBX correcta, User/Auth=201 | 201 queda rollback |
| G10-19E-post-reboot | FAIL funcional | Persistencia P212/P237 | Tras reboot vuelven a vacío | Write runtime no persiste |
| G10-19E4F | FAIL seguro | Save and Apply por UI | Página/campos/botón encontrados; no se mapeó P212 con seguridad | No pulsar a ciegas |
| G10-19E4F2 | PASS diagnóstico | Auditar DOM | 4 selects, 39 radios, 8 botones | Mapear radios |
| G10-19E4F3 | PASS diagnóstico | Mapear selects | Ningún select corresponde a P212 | P212 no es select |
| G10-19E4F3B | PASS diagnóstico | Mapear radios P212 | `name=P212`: value 0=TFTP, 1=HTTP, 2=HTTPS, 3=FTP, 4=FTPS | Control identificado inequívocamente |
| G10-19E4F4 | PASS temporal | Save and Apply real con P212/P237 | Radio TFTP, P237 y botón encontrados; click ejecutado; API inmediata confirma objetivo | Probar persistencia post-reboot |
| G10-19F4 | TRANSITORIO | Reboot + persistencia | Reboot aceptado; ventana de 90 s insuficiente para HTTP | Repetir con espera larga |
| G10-19F4B | PASS diagnóstico | Leer después del boot | P212/P237 vuelven a vacío; Account 1 sigue 201 | Save and Apply tampoco deja esos P-values persistentes |
| G10-19F5 | PASS diagnóstico | Control sin posibilidad de fetch | Se usó temporalmente destino reservado no enrutable; tras reboot P212/P237 también vuelven a vacío | Se descarta que el cfg de Issabel sea quien esté borrando P212/P237 |
| G10-19F6 | INCONCLUSO | Set PBX + disparar operación PROV en proceso separado | Bootstrap previo OK; segundo Chromium arrancó mientras teléfono estaba ocupado y terminó en timeout antes del trigger | No clasificar soporte PROV con esta corrida |
| G10-19F6B-a1 | TRANSITORIO | Bootstrap runtime + PROV en una sola sesión | Primer intento arrancó durante estado transitorio y no obtuvo sesión web | Repetir con teléfono estable |
| G10-19F6B-a2 | PASS diagnóstico | Bootstrap runtime + PROV en la misma sesión estable | Login real OK; P212/P237 `success/right`; verificación READY; `PROV` con fallback autenticado devuelve `success`; teléfono vuelve accesible | Firmware sí acepta operación nativa PROV |
| G10-19G2-after-PROV | PASS diagnóstico | Leer Account 1 después de PROV aceptado | Cuenta habilitada; SIP server PBX; User/Auth siguen `201` | PROV no llevó Account 1 a 202; inspeccionar cfg/assignment |
| G10-19G3 | PASS parcial | Auditar assignment/cfg | `cfgc074ade86609` presente; DB audit directo bloqueado por permisos de amportal | Usar helper privilegiado para DB si hace falta |
| G10-19G4 | PASS | Verificar marcadores seguros del cfg | Binario contiene 202, Ashly y PBX; no contiene 201/Fabi | El cfg generado por Issabel sí apunta a 202 |
| G10-19H1 | PASS diagnóstico | Probar consumo de provisioning por HTTP mirror | El teléfono solicitó `cfgc074ade86609` y `cfgc074ade86609.xml`; PROV aceptado; Account 1 seguía 201 | El teléfono sí ejecuta provisioning y pide ambos formatos |
| G10-19H2 | PASS | Generar XML equivalente desde cfg binario de Issabel | XML creado con 38 parámetros; P35/P36=202, P34 presente, P47=PBX, P270=Ashly | Probar XML nativo por TFTP |
| G10-19H3 | PASS FUNCIONAL | Aplicar XML por TFTP desde Issabel | Tras provisioning nativo, el teléfono físico cambió en pantalla de Fabi a Ashly | Éxito funcional del provisioning hacia 202 |
| G10-19H4 | PASS | Verificar persistencia después de reboot real | Tras reinicio: Account 1 habilitada, Account Name=202/Ashly, SIP server=PBX, User ID=202 y Auth ID=202 | 202 Ashly persiste |
| G10-19H5-a1 | FAIL infraestructura | Primer intento de auditoría SIP Asterisk | Acción nueva del helper de llamadas no estaba autorizada por sudoers; no se ejecutó ninguna consulta Asterisk | Reusar helper privilegiado ya autorizado |
| G10-19H5-a2 | PASS | Confirmar registro real en Asterisk | Extensión 202 registrada `OK` desde `192.168.1.167`; extensión 201 ya no usa esa IP | Provisioning 202 validado extremo a extremo |
| G10-19H6 | PASS dry-run | Integrar generación XML en `Grandstream.py` conservando binario legacy | `py_compile` PASS; escritura binaria preservada; XML agregado desde el mismo `vars`; MAC ligada al XML; solo P-values | Código candidato listo para despliegue controlado en LAB |
| G10-19H8F | PASS generación / FAIL activación nativa | Ejecutar `applyconfig` real con un solo GXP1625 seleccionado | `applyconfig_rc=0`; binario + XML se regeneran automáticamente con 202/Ashly/PBX, pero `grandstream_failed_seen=YES` | La generación integrada está resuelta; aislar login/activación HTTP nativa |
| G10-19H8G-a1 | FAIL observabilidad | E2E integrado + evidencia TFTP | Generación y teléfono pasaron; la prueba final falló por lectura TFTP sin privilegios | Corregir solo el mecanismo de evidencia |
| G10-19H8G-a2 | PASS E2E | Endpoint Configurator → cfg/XML → bootstrap/PROV → TFTP → teléfono → Asterisk | Los 3 jobs pasan; teléfono queda 202/Ashly, TFTP observado y 202 registrada desde `192.168.1.167`; 201 liberada | Flujo funcional completo probado; Chromium todavía actúa como bootstrap |
| G10-19H8H1 | PASS diagnóstico | Comparar `session-identity` del navegador con SID de login sin exponer valores | `session-identity` existe, no llega por Set-Cookie y coincide con SID de `/dologin` | El cliente nativo puede sintetizar `session-identity=<SID>` |
| G10-19H8H2 | FAIL controlado | Añadir `session-identity=<SID>` al cliente nativo | Parche instala/compila, pero `applyconfig` sigue fallando; rollback automático PASS | La falla ocurre antes o falta otra diferencia de login |
| G10-19H8H2B | PASS diagnóstico parcial | Clasificar respuesta del POST nativo | Tras corregir el anchor, el clasificador se instala, pero `h8h2b_response_class_seen=NO`; rollback H8H2B/H8H2 PASS | El flujo no llega al parser de `api.values.post`; mirar etapa de login |
| G10-19H8H2C | PASS diagnóstico | Trazar etapas del login nativo sin valores sensibles | Llega a `ENTER`, `LOGIN_RESPONSE`, `LOGIN_JSON_PARSED`; nunca llega a `SID_READY` ni `POST_BEGIN` | `/dologin` devuelve JSON, pero sin SID utilizable para el código actual |
| G10-19H8H2D | PASS diagnóstico | Añadir temporalmente `Accept: */*` al `applyconfig` nativo | Con el password efectivo actual de Issabel sigue sin llegar a `SID_READY`; rollback completo PASS | Este resultado no aísla Accept porque después se demostró mismatch de credencial |
| G10-19H8H2E | PASS diagnóstico | Clasificar forma del JSON de `/dologin` usado por Issabel | `response_success=NO`, `body_dict=NO`, `sid_present=NO` | El login nativo de Issabel está siendo rechazado |
| G10-19H8H2F | PASS diagnóstico | Comparar password HTTP efectivo de Endpoint Configurator con el secreto de laboratorio conocido como válido | Fuente efectiva=`MODEL_DEFAULT`; `endpoint_override_count=0`; `effective_http_password_matches_lab_secret=NO` | Hay un bloqueo de credencial: falta override por endpoint o equivalente seguro |
| G10-19H8H2G | PASS diagnóstico | Repetir `/dologin` con Python `http.client` y el password conocido como válido | HTTP 200/JSON, pero `response_success=NO`, `body_dict=NO`, `sid_present=NO` | Además del password, existe diferencia de fidelidad en la petición Python |
| G10-19H8H2H | PASS diagnóstico | Probar Python `http.client` con password válido + `Accept: */*` + `User-Agent: curl/8.14.1` | HTTP 200/JSON, `response_success=YES`, `body_dict=YES`, `sid_present=YES` | La fidelidad de headers queda resuelta usando el par Accept + User-Agent; siguiente bloqueo es alinear la credencial efectiva de Issabel |

## Hallazgo actual

El GXP1625 1.0.7.70 está funcionalmente aprovisionado extremo a extremo como `202 Ashly`: sobrevivió un reinicio real y Asterisk confirma `202` registrada desde `192.168.1.167`, mientras `201` ya no usa esa IP.

La generación integrada de Endpoint Configurator también está resuelta: `Grandstream.py` live conserva el `cfg<MAC>` binario y genera automáticamente `cfg<MAC>.xml` desde el mismo mapa de P-values. El flujo H8G confirmó la cadena completa cuando Chromium realiza el bootstrap de provisioning.

Para eliminar Chromium se aislaron **dos requisitos distintos** del login HTTP nativo. Primero, Issabel está tomando `http_password` del `MODEL_DEFAULT`, no existe override para este endpoint y ese valor no coincide con la contraseña real conocida del teléfono. Segundo, aun usando la contraseña correcta, el `http.client` actual es rechazado hasta reproducir mejor la petición aceptada: H8H2H confirma login `success` con SID cuando se añaden `Accept: */*` y `User-Agent: curl/8.14.1` junto con Host/Referer/Content-Type.

No se ha escrito todavía ninguna contraseña en `endpoint_properties`. Esa modificación de base de datos queda deliberadamente pendiente de autorización explícita. Tampoco quedan activos los parches diagnósticos temporales H8H2/H8H2B/H8H2C/H8H2D/H8H2E; sus rollbacks fueron validados.

## Próximas pruebas

1. Con autorización de escritura DB, configurar `http_password` como propiedad específica del endpoint GXP1625, sin mostrar ni registrar el valor y conservando rollback.
2. Incorporar en el cliente GXP140x los headers de login validados y la síntesis `session-identity=<SID>`.
3. Ejecutar `applyconfig` sin Chromium y comprobar que llegue a `api.values.post` y complete activación estática.
4. Repetir el E2E nativo: Endpoint Configurator → binario/XML → teléfono → TFTP → 202/Ashly → Asterisk.
5. Convertir el mecanismo final en arquitectura reusable y matriz GXP1625/GXP1630/GXP16xx.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

Los workflows deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
