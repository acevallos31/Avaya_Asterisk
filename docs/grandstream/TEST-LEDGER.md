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
| G10-19E2 | FAIL controlado | Escribir P212/P237 por cliente directo | `api.values.post` devuelve `session-expired` | No es problema de credenciales |
| G10-19E3 | FAIL controlado | Repetir write HTTP/2/keepalive | Sigue `session-expired` | Transporte no era la causa |
| G10-19E4D | PASS diagnóstico | Trazar sesión Chromium real | Webapp crea `session-identity`/`session-role` | Usar navegador real para writes |
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
| G10-19H3 | PASS FUNCIONAL | Aplicar XML por TFTP desde Issabel | Tras provisioning nativo, el teléfono físico cambió en pantalla de Fabi a Ashly | Éxito funcional del provisioning hacia 202; falta confirmar registro SIP y endurecer integración automática |

## Hallazgo actual

El GXP1625 1.0.7.70 ya quedó aprovisionado funcionalmente desde Issabel: el teléfono pasó de **201 Fabi** a **202 Ashly** usando provisioning nativo y un `cfg<MAC>.xml` servido por TFTP desde `192.168.1.10`.

La documentación oficial de Grandstream indica que **Config Server Path (P237)** es la ruta del servidor de configuración y puede expresarse como IP/FQDN o URL válida según familia/firmware. Para TFTP, `P212=0` selecciona el transporte y `P237=192.168.1.10` es válido en este laboratorio. La prueba H1 además demostró que el teléfono solicita desde el servidor configurado tanto `cfg<MAC>` como `cfg<MAC>.xml`, confirmando que el path usado resuelve correctamente al root de provisioning.

No debe considerarse el cierre total hasta verificar que la extensión 202 está registrada en Asterisk y hasta integrar la generación XML al flujo de Endpoint Configurator para que no dependa de una conversión manual/post-proceso.

## Próximas pruebas

1. Verificar en Issabel/Asterisk que 202 está realmente registrada desde `192.168.1.167`.
2. Confirmar que 201 dejó de estar registrada desde ese teléfono.
3. Reiniciar el GXP1625 y comprobar persistencia de 202 Ashly.
4. Integrar generación de `cfg<MAC>.xml` en la clase Grandstream/Endpoint Configurator de forma reutilizable.
5. Validar que al reasignar otra extensión, Endpoint Configurator regenere binario + XML automáticamente.
6. Generalizar la ruta a GXP1630/GXP16xx y documentar diferencias por firmware/modelo.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

Los workflows deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
