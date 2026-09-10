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
- Extensión rollback inicial: `201`
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
| G10-19E4D | PASS diagnóstico | Trazar sesión Chromium real | Webapp crea `session-identity`/`session-role` | Caracterizar contrato real de sesión |
| G10-19E4E | PASS temporal | Escribir P212/P237 dentro de Chromium | `success/right`; relectura inmediata confirma P212=0 y P237=PBX | Escritura runtime funciona |
| G10-19F2 | PASS | Reboot controlado | Fallback autenticado aceptado con `SAVEREBOOT`; sin factory reset | Verificar estado post-boot |
| G10-19F3 | BLOQUEADO observabilidad | Capturar RRQ TFTP | Runner sin privilegio de captura | No inferir ausencia de RRQ |
| G10-19F3B | BLOQUEADO observabilidad | Buscar RRQ en logs | Journal/messages no legibles | Usar evidencia alternativa |
| G10-19G2-pre | PASS diagnóstico | Baseline Account 1 | Cuenta habilitada, PBX correcta, User/Auth=201 | 201 queda rollback inicial |
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
| G10-19F6B-a2 | PASS diagnóstico | Bootstrap runtime + PROV en la misma sesión estable | Login real OK; P212/P237 `success/right`; verificación READY; `PROV` devuelve `success`; teléfono vuelve accesible | Firmware sí acepta operación nativa PROV |
| G10-19G2-after-PROV | PASS diagnóstico | Leer Account 1 después de PROV aceptado | Cuenta habilitada; SIP server PBX; User/Auth siguen `201` | PROV no llevó Account 1 a 202; inspeccionar cfg/assignment |
| G10-19G3 | PASS parcial | Auditar assignment/cfg | `cfgc074ade86609` presente; DB audit directo bloqueado por permisos de amportal | Usar helper privilegiado para DB si hace falta |
| G10-19G4 | PASS | Verificar marcadores seguros del cfg | Binario contiene 202, Ashly y PBX; no contiene 201/Fabi | El cfg generado por Issabel sí apunta a 202 |
| G10-19H1 | PASS diagnóstico | Probar consumo de provisioning por HTTP mirror | El teléfono solicitó `cfgc074ade86609` y `cfgc074ade86609.xml`; PROV aceptado; Account 1 seguía 201 | El teléfono sí ejecuta provisioning y pide ambos formatos |
| G10-19H2 | PASS | Generar XML equivalente desde cfg binario de Issabel | XML creado con 38 parámetros; P35/P36=202, P34 presente, P47=PBX, P270=Ashly | Probar XML nativo por TFTP |
| G10-19H3 | PASS FUNCIONAL | Aplicar XML por TFTP desde Issabel | Tras provisioning nativo, el teléfono físico cambió en pantalla de Fabi a Ashly | Éxito funcional del provisioning hacia 202 |
| G10-19H4 | PASS | Verificar persistencia después de reboot real | Tras reinicio: Account 1 habilitada, Account Name=202/Ashly, SIP server=PBX, User ID=202 y Auth ID=202 | 202 Ashly persiste |
| G10-19H5-a1 | FAIL infraestructura | Primer intento de auditoría SIP Asterisk | Acción nueva del helper de llamadas no estaba autorizada por sudoers; no se ejecutó ninguna consulta Asterisk | Reusar helper privilegiado ya autorizado |
| G10-19H5-a2 | PASS | Confirmar registro real en Asterisk | Extensión 202 registrada `OK` desde `192.168.1.167`; extensión 201 ya no usa esa IP | Provisioning 202 validado extremo a extremo |
| G10-19H6 | PASS dry-run | Integrar generación XML en `Grandstream.py` conservando binario legacy | `py_compile` PASS; escritura binaria preservada; XML agregado desde el mismo `vars`; MAC ligada al XML; solo P-values | Código candidato listo para despliegue controlado |
| G10-19H8F | PASS generación / FAIL activación nativa | Ejecutar `applyconfig` real con un solo GXP1625 seleccionado | `applyconfig_rc=0`; binario + XML se regeneran con 202/Ashly/PBX, pero `grandstream_failed_seen=YES` | La generación integrada está resuelta; aislar login/activación HTTP nativa |
| G10-19H8G-a1 | FAIL observabilidad | E2E integrado + evidencia TFTP | Generación y teléfono pasaron; la prueba final falló por lectura TFTP sin privilegios | Corregir solo mecanismo de evidencia |
| G10-19H8G-a2 | PASS E2E | Endpoint Configurator → cfg/XML → bootstrap/PROV → TFTP → teléfono → Asterisk | Los 3 jobs pasan; teléfono queda 202/Ashly, TFTP observado y 202 registrada desde `192.168.1.167`; 201 liberada | Flujo funcional completo probado; Chromium todavía actuaba como bootstrap |
| G10-19H8H1 | PASS diagnóstico | Comparar `session-identity` del navegador con SID de login sin exponer valores | `session-identity` existe, no llega por Set-Cookie y coincide con SID de `/dologin` | El cliente nativo puede sintetizar `session-identity=<SID>` |
| G10-19H8H2 | FAIL controlado | Añadir `session-identity=<SID>` al cliente nativo | Parche instala/compila, pero `applyconfig` sigue fallando; rollback automático PASS | La falla ocurre antes o falta otra diferencia de login |
| G10-19H8H2B | PASS diagnóstico parcial | Clasificar respuesta del POST nativo | Tras corregir el anchor, el clasificador se instala, pero `h8h2b_response_class_seen=NO`; rollback H8H2B/H8H2 PASS | El flujo no llega al parser de `api.values.post`; mirar etapa de login |
| G10-19H8H2C | PASS diagnóstico | Trazar etapas del login nativo sin valores sensibles | Llega a `ENTER`, `LOGIN_RESPONSE`, `LOGIN_JSON_PARSED`; nunca llega a `SID_READY` ni `POST_BEGIN` | `/dologin` devuelve JSON, pero sin SID utilizable para el código actual |
| G10-19H8H2D | PASS diagnóstico | Añadir temporalmente `Accept: */*` al `applyconfig` nativo | Con el password efectivo de Issabel sigue sin llegar a `SID_READY`; rollback completo PASS | Resultado no aísla Accept porque había mismatch de credencial |
| G10-19H8H2E | PASS diagnóstico | Clasificar forma del JSON de `/dologin` usado por Issabel | `response_success=NO`, `body_dict=NO`, `sid_present=NO` | El login nativo de Issabel está siendo rechazado |
| G10-19H8H2F | PASS diagnóstico | Comparar password HTTP efectivo con secreto conocido como válido | Fuente=`MODEL_DEFAULT`; no había override; no coincidía | Se requiere credencial por endpoint o mecanismo equivalente |
| G10-19H8H2G | PASS diagnóstico | Repetir `/dologin` con Python `http.client` y password válido | HTTP 200/JSON, pero sin `success` ni SID | Existe también diferencia de fidelidad HTTP |
| G10-19H8H2H | PASS diagnóstico | Probar Python con password válido + `Accept: */*` + `User-Agent: curl/8.14.1` | HTTP 200/JSON, `response_success=YES`, `body_dict=YES`, `sid_present=YES` | Headers validados para login nativo |
| G10-19H8I | PASS NATIVO SIN CHROMIUM | Alinear credencial por endpoint y ejecutar `applyconfig` con headers + sesión validados | Override exacto creado para el GXP1625; `SID_READY`, `POST_BEGIN`, `POST_RESPONSE`, `POST_JSON_PARSED`; `grandstream_finished_seen=YES`, `grandstream_failed_seen=NO`; XML 202/Ashly regenerado; Asterisk 202 `OK` en `192.168.1.167`; 201 no usa esa IP | Contrato nativo completo demostrado; se retiene solo el override de credencial y se revierten parches diagnósticos |
| G10-19H8J-a1 | FAIL precondición de prueba | Validar parche final persistente sin instrumentación | Credencial correcta y parche candidato aplicado, pero `endpoint.selected=0`; no se ejecutó la ruta real; rollback del parche PASS | Automatización debe reproducir la selección que hace la GUI |
| G10-19H8J-a2 | PASS E2E FINAL | Repetir con selección exacta y retener integración nativa | `selected=1` solo para GXP1625/202; `applyconfig_rc=0`; `grandstream_finished_seen=YES`; `grandstream_failed_seen=NO`; XML 202/Ashly; SIP 202 `OK`; `selected_after_applyconfig=0`; parche H8J retenido | GXP1625 queda integrado nativamente sin Chromium |
| G10-19H8K-a1/a2 | FAIL transitorio reproducible | Repetir inmediatamente el flujo ya persistido sin modificar código | Prerrequisitos H8J y credencial correctos; dos intentos inmediatos regeneran XML pero la activación devuelve `grandstream_failed_seen=YES`; selección vuelve a 0 | No revertir H8J: aislar etapa antes de atribuir causa |
| G10-19H8K2 | PASS diagnóstico | Instrumentar temporalmente la repetición H8K sin cambiar el contrato H8J | Recorre `ENTER→LOGIN_RESPONSE→LOGIN_JSON_PARSED→SID_READY→POST_BEGIN→POST_RESPONSE→POST_JSON_PARSED`; POST clasifica `response=success status=right`; `grandstream_finished_seen=YES`; trace revertido | H8J persiste correcto; los dos fallos H8K se clasifican como condición transitoria/no determinista aún no atribuida |
| G10-19H8L | PASS READ-ONLY | Minimizar el requisito de User-Agent del login nativo | Run `34506170492`: sin User-Agent explícito y con `Issabel-EndpointConfig/5.0` ambos obtienen HTTP 200, JSON success y SID; sin escrituras | Eliminar el User-Agent fijo `curl/8.14.1` del contrato final |
| G10-19H8M-a1 | FAIL SEGURO | Probar dos Configure nativos sin User-Agent separados 60 s | Run `34506766259`: ciclo 1 PASS completo; ciclo 2 regeneró XML pero activación falló; rollback del cambio H8M PASS | 60 s no es una ventana segura de repetición; H8J fue restaurado automáticamente |
| G10-19H8M-a2 | PASS E2E REPETIBLE | Repetir dos ciclos sin User-Agent con recuperación conservadora | Run `34507118291`: ambos ciclos separados 300 s terminaron `grandstream_finished_seen=YES`, XML 202/Ashly correcto, SIP 202 `OK`, 201 liberada; parche mínimo retenido | Contrato mínimo cerrado; aplicar guardrail operativo inicial de 5 minutos entre Configure del mismo teléfono |

## Hallazgo actual

El GXP1625 1.0.7.70 está funcionalmente aprovisionado extremo a extremo como `202 Ashly`. La configuración sobrevivió un reinicio real y Asterisk confirmó `202` registrada desde `192.168.1.167`, mientras `201` dejó de usar esa IP.

La integración nativa **ya funciona sin Chromium**. Endpoint Configurator usa un `http_password` específico del endpoint (el valor no se registra en este documento), genera `cfg<MAC>` y `cfg<MAC>.xml`, autentica por HTTP con los headers validados, construye `session-identity` desde el SID de `/dologin` y completa `api.values.post` con `success/right`. H8J-a2 validó el flujo limpio y retuvo el parche final en la clase live del LAB.

El `Config Server Path` validado para este laboratorio es `192.168.1.10` con TFTP seleccionado mediante P212. H1 demostró experimentalmente que el teléfono solicita tanto `cfg<MAC>` como `cfg<MAC>.xml` desde el provisioning root.

H8K mostró dos fallos al repetir inmediatamente Configure pese a tener la credencial y H8J correctos. H8K2, ejecutado después con trazado temporal, completó login y POST con `response=success status=right`. H8M confirmó que 60 segundos todavía pueden reproducir el fallo, mientras dos ciclos separados 300 segundos pasan extremo a extremo. Esto establece un guardrail operativo conservador, pero no atribuye la causa interna a timeout, sesión, caché o rate limit.

H8L y H8M demostraron además que el `User-Agent: curl/8.14.1` no es requerido. El contrato mínimo retenido usa `Accept: */*`, Host/Referer, credencial por endpoint y `session-identity=<SID>`, sin User-Agent explícito.

## Estado persistente autorizado en LAB

- OUI adicional Grandstream `C0:74:AD` en Endpoint Configurator.
- Generación dual `cfg<MAC>` + `cfg<MAC>.xml` en la clase live Grandstream.
- Override `http_password` específico del endpoint GXP1625; el valor no se expone.
- Parche final H8J/H8M de request/session fidelity activo en `Grandstream.py` live, sin User-Agent fijo.
- Teléfono provisionado como `202 Ashly`.
- `endpoint.selected` vuelve a `0` después de cada `applyconfig`.

## Próximas pruebas

1. Convertir H6+H8J/H8M en un paquete reproducible con preflight, backup, install, verify y rollback.
2. Ejecutar el ciclo exacto del paquete en LAB y congelar checksums.
3. Ejecutar preflight read-only en la PBX de producción seleccionada.
4. Desplegar primero en un único GXP1625 canario, respetando 300 s entre Configure del mismo teléfono.
5. Probar GXP1630 físicamente antes de marcarlo como soportado.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

Los workflows deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
