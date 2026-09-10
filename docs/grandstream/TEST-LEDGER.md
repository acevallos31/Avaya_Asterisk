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
| G10-19H3 | PASS FUNCIONAL | Aplicar XML por TFTP desde Issabel | Tras provisioning nativo, el teléfono físico cambió en pantalla de Fabi a Ashly | Éxito funcional del provisioning hacia 202 |
| G10-19H4 | PASS | Verificar persistencia después de reboot real | Tras reinicio: Account 1 habilitada, Account Name=202/Ashly, SIP server=PBX, User ID=202 y Auth ID=202 | 202 Ashly persiste |
| G10-19H5-a1 | FAIL infraestructura | Primer intento de auditoría SIP Asterisk | Acción nueva del helper de llamadas no estaba autorizada por sudoers; no se ejecutó ninguna consulta Asterisk | Reusar helper privilegiado ya autorizado |
| G10-19H5-a2 | PASS | Confirmar registro real en Asterisk | Extensión 202 registrada `OK` desde `192.168.1.167`; extensión 201 ya no usa esa IP | Provisioning 202 validado extremo a extremo |
| G10-19H6 | PASS dry-run | Integrar generación XML en `Grandstream.py` conservando binario legacy | `py_compile` PASS; escritura binaria preservada; XML agregado desde el mismo `vars`; MAC ligada al XML; solo P-values; sin write al PBX live ni al teléfono | Código candidato listo para despliegue controlado en LAB |

## Hallazgo actual

El GXP1625 1.0.7.70 quedó aprovisionado extremo a extremo desde Issabel. La configuración 202 Ashly sobrevivió un reinicio real y Asterisk confirma que la extensión `202` está registrada `OK` desde `192.168.1.167`. La antigua extensión `201` ya no está registrada desde esa IP.

La documentación oficial de Grandstream indica que **Config Server Path (P237)** es la ruta del servidor de configuración y puede expresarse como IP/FQDN o URL válida según familia/firmware. Para TFTP, `P212=0` selecciona el transporte y `P237=192.168.1.10` es válido en este laboratorio. La prueba H1 demostró además que el teléfono solicita tanto `cfg<MAC>` como `cfg<MAC>.xml` desde ese root de provisioning.

G10-19H6 validó en dry-run la modificación candidata de `Grandstream.py`: el flujo conserva `cfg<MAC>` binario y añade `cfg<MAC>.xml` usando exactamente el mismo mapa `vars`. El cambio todavía no se ha instalado sobre la clase live de Issabel; el siguiente paso cruza la frontera de modificación de código live del PBX.

## Próximas pruebas

1. Desplegar de forma controlada y reversible la modificación H6 sobre `Grandstream.py` live del LAB.
2. Ejecutar Configure desde Endpoint Configurator y comprobar que regenere automáticamente binario + XML sin el conversor H2.
3. Reaprovisionar 202 usando únicamente el flujo integrado y verificar teléfono + Asterisk.
4. Documentar arquitectura final y matriz GXP1625/GXP1630/GXP16xx.
5. Repetir el flujo con GXP1630 sin asumir diferencias de firmware.

## Regla de documentación

Cada prueba operativa Grandstream debe dejar tres evidencias:

1. `GITHUB_STEP_SUMMARY` legible dentro del run específico de la prueba.
2. Artifact sanitizado, usando `if: always()` cuando sea viable.
3. Entrada persistente en este ledger con hipótesis, resultado, decisión y siguiente actividad.

Los workflows deben evitar matrices ciegas. Cada prueba necesita hipótesis, criterio de éxito y condición de parada.
