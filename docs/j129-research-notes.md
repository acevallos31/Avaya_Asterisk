# Investigación técnica — Avaya J129 / Open SIP

Actualizado: 2026-09-02

Este documento separa documentación oficial, evidencia propia del LAB e hipótesis pendientes. No contiene secretos reales.

## Firmware LAB

- J129 físico: `3.0.0.0.20`.
- Firmware oficial más reciente investigado: J100 SIP `4.1.11.0`, mayo de 2026.
- Binario J129 documentado: `FW_S_J129_R4_1_11_0_10.bin`.

No realizar upgrade todavía. Primero identificar hardware/comcode, revisar ruta de upgrade/downgrade, preparar recovery y validar paquete oficial completo.

Fuente principal: Avaya J100 Series SIP Release 4.1.11.0 Readme.

## Open SIP / Asterisk

Avaya documenta Open SIP con plataformas que incluyen Asterisk R16. El LAB utiliza Asterisk 18.19.0 y su funcionamiento es evidencia propia de este proyecto, no una certificación explícita de Avaya para R18.

Valores Open SIP a evaluar/conservar:

```text
SET ENABLE_AVAYA_ENVIRONMENT 0
SET DISCOVER_AVAYA_ENVIRONMENT 0
SET ENABLE_IPOFFICE 0
```

## Provisioning y firmware

La PBX puede actuar como file/provisioning server HTTP/HTTPS para:

```text
J100Supgrade.txt
46xxsettings.txt
<mac>.txt
FW_S_J129_*.bin
Mlf_J129_*.xml
```

Provisioning normal y firmware upgrade deben permanecer como responsabilidades separadas. El Apply estándar nunca debe activar accidentalmente un firmware nuevo.

## check-sync / actualización remota

La documentación de J100/Open SIP describe eventos de resync/reset, pero la evidencia física del proyecto manda para este firmware.

Workflow 09 demostró en `3.0.0.0.20`:

```text
check-sync -> reinicio físico -> nueva descarga de provisioning -> nuevo registro SIP
```

Por tanto, no usar `check-sync` para pruebas cuyo requisito sea “sin reboot”.

## NTP / hora

Para firmware anterior a ramas modernas de J100 se seleccionó la ruta compatible basada en:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

`SNTP_SYNC_INTERVAL` es intervalo de sincronización de hora, no polling de provisioning.

Workflow 10 probó que Issabel puede generar estos valores sin caída SIP. No probó que el teléfono los consumiera durante la ventana de 300 s, porque no hubo nuevo GET de `46xxsettings.txt`.

La PBX quedó configurada para servir NTP a `192.168.1.0/24`. Antes de producción debe agregarse una aserción que espere el regreso de chronyd a estado sincronizado después de restart.

## Idioma español

Avaya distribuye recursos específicos J129, incluyendo:

```text
Mlf_J129_CastilianSpanish.xml
Mlf_J129_LatinAmericanSpanish.xml
```

Para Honduras, candidato inicial: Latin American Spanish.

El baseline del workflow 11 comprobó que ninguno de esos XML existe actualmente en la PBX LAB. No reconstruir, inventar ni copiar archivos de idioma de fuentes no oficiales.

La prueba de idioma debe requerir:

1. XML oficial Avaya;
2. publicación HTTP controlada;
3. parámetros de idioma exactos para el firmware;
4. GET observado en access log;
5. cambio visible en el J129 físico.

## Admin menu — corrección importante

La investigación oficial registrada para J129 establece:

```text
PROCSTAT 0 -> Admin menu permitido
PROCSTAT 1 -> Admin menu no permitido/restringido para configuración
```

Fuente: Installing and Administering Avaya J129 IP Phone, sección de parámetros de Admin menu.

Esto corrige una decisión errónea introducida durante la preparación inicial del workflow 11: si el objetivo es habilitar el menú local, no debe aplicarse `PROCSTAT 1`; el candidato correcto de laboratorio es `PROCSTAT 0`.

`PROCPSWD`/`ADMIN_PASSWORD` corresponde al acceso del menú físico y no debe confundirse con la contraseña de Web UI.

Antes de producción debe existir recovery/factory-reset documentado si se centraliza la política del menú.

## Otros parámetros UX en investigación

Candidatos del workflow 11:

```text
PROVIDE_OPTIONS_SCREEN
PROVIDE_NETWORKINFO_SCREEN
PROVIDE_LOGOUT
ENTRYNAME
```

No afirmar efecto físico hasta probarlo en el J129.

`DISPLAY_NAME` no consiguió mostrar `Briam` en idle en la línea base física; `ENTRYNAME` queda como candidato de prueba, no como solución confirmada.

## Web Admin

Baseline workflow 11:

```text
HTTP  -> 200
HTTPS -> 200
```

La Web UI ya es alcanzable. Aún no se ha gestionado su password mediante provisioning en esta fase.

La credencial usada anteriormente debe considerarse comprometida/expuesta. Nunca imprimir ni almacenar la contraseña en repo. Cuando se pruebe administración central, usar Repository Secret y valores redactados en logs.

## BUG-J129-004 — identidad SIP persistente

Evidencia física:

- Endpoint Configurator queda con 0 cuentas.
- archivo `<mac>.txt` eliminado server-side.
- después de reboot el teléfono puede volver a registrar una identidad SIP persistida localmente.

Eliminar provisioning no equivale a logout del teléfono. No usar valores vacíos ni comandos inventados. La solución o limitación debe basarse en semántica oficial Avaya.

## Esquema Endpoint Configurator — regla de investigación

El LAB usa MySQL/MariaDB `endpointconfig`. Durante workflow 11 se cometieron dos errores por asumir infraestructura/esquema:

- usar SQLite: `no such table: endpoint`;
- asumir columna `endpoint.ip_address`: `Unknown column`.

Regla: antes de escribir consultas nuevas, reutilizar consultas ya validadas del workflow 10 o ejecutar primero un audit read-only de `SHOW COLUMNS`/joins reales. No adivinar esquema.

## Estado del workflow 11

Baseline read-only: PASS.

Apply aún no validado. Los fallos hasta ahora ocurrieron antes de `issabel-endpointconfig --applyconfig`. El run más reciente además fue lanzado en `main` y abortó correctamente por el guard que exige `Audit`.

## Fuentes oficiales principales

- Avaya J100 Series SIP Release 4.1.11.0 Readme — https://support.avaya.com/css/en/public/documents/101095479
- Installing and Administering Avaya J100 Series SIP IP Phones in Open SIP — https://support.avaya.com/css/public/documents/101053965
- Installing and Administering Avaya J129 IP Phone in third-party call control setup — https://support.avaya.com/css/public/documents/101037009
- Installing and Administering Avaya J129 IP Phone — https://support.avaya.com/css/public/documents/101033171
- IP Office SIP Telephone Installation Notes — https://support.avaya.com/css/public/documents/101091571

## Próxima investigación

1. corregir `PROCSTAT` del workflow 11 a `0`;
2. validar Apply UX server-side usando consultas MySQL ya probadas;
3. comprobar menú/nombre/hora físicamente;
4. conseguir paquete oficial con XML Latin American Spanish;
5. probar idioma como fase separada y reversible;
6. luego estudiar Web Admin password central y `BUG-J129-004`;
7. firmware upgrade queda separado y posterior.
