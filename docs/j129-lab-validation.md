# Validación de laboratorio — Avaya J129

> Evidencia reproducible del J129 físico sobre Issabel 5. No almacenar secretos SIP ni credenciales Web Admin reales.

## Entorno actual — 2026-09-02

- Rama de pruebas: `Audit`
- Issabel 5 / Rocky Linux 8
- Asterisk 18.19.0
- PBX / provisioning: `192.168.1.10`
- J129: `192.168.1.168`
- MAC: `C8:1F:EA:9B:65:0D`
- Firmware: `3.0.0.0.20`
- Endpoint id: `3`
- Cuenta SIP: `200`
- Provisioning HTTP desde PBX
- `192.168.1.169` está ocupado por otro dispositivo y no debe asignarse a la PBX.

## Evidencia consolidada

### Discovery / Accounts / provisioning

`PHYSICAL-J129-PASS`:

```text
J100Supgrade.txt -> 46xxsettings.txt -> c81fea9b650d.txt
```

Endpoint Configurator identifica Avaya/J129 y usa Accounts estándar. No existe UI SIP paralela.

### SIP

`PHYSICAL-J129-PASS`: cuenta `200`, IP `192.168.1.168`, `chan_sip`, peer `OK`. Asterisk es la fuente autoritativa de registro.

### 07 — Rescan Idempotency

`LAB-INTEGRATION-PASS`: dos rescans conservaron exactamente un J129, endpoint id 3 y cuenta 200.

### 08 — Single Account V1

`LAB-INTEGRATION-PASS`:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

J129 v1 queda limitado a una cuenta mientras no exista una implementación multicuenta oficial validada.

### 09 — Remote restart + reprovisioning

`PHYSICAL-J129-PASS` — run `33599222299`.

El evento SIP `check-sync` produjo caída del peer, reinicio físico, nueva descarga HTTP y re-registro SIP. En firmware `3.0.0.0.20` no debe llamarse “reload silencioso”.

Secuencia observada:

```text
SIP OK
-> check-sync
-> peer down/not OK
-> GET J100Supgrade.txt
-> GET 46xxsettings.txt
-> GET c81fea9b650d.txt
-> SIP OK nuevamente
```

### 10 — Forced Provisioning / NTP

`LAB-INTEGRATION-PASS` server-side — run `33602271998`.

Apply normal de Issabel cargó exactamente un endpoint y regeneró provisioning con:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

Durante 300 s SIP permaneció `OK`, no se envió NOTIFY/check-sync y el J129 no realizó un nuevo GET observado de `46xxsettings.txt`. Quedó validada la generación server-side sin interrupción SIP; en ese run todavía no se había validado la aplicación física.

Chronyd quedó escuchando UDP/123 para LAN. Antes de producción, el test debe esperar y afirmar que chronyd vuelve a sincronizarse después de un restart; el run exitoso observó temporalmente `Stratum 0 / Not synchronised` inmediatamente tras reiniciarlo.

## Línea base física de pantalla

Antes del workflow 11:

- idle mostraba hora incorrecta/desactualizada;
- flecha abajo mostraba extensión `200`;
- `Briam` no aparecía en idle;
- softkeys en inglés: `Redial`, `Contacts`;
- no había acceso visible a softkey/menu Admin.

`DISPLAY_NAME "Briam"` no produjo el resultado visible esperado.

## 11 — Phone UX & Admin

### Baseline read-only — PASS

Run `33603387145`:

- `SIP_STATUS=OK account=200`.
- Web UI HTTP `200` y HTTPS `200`.
- `46xxsettings.txt` contenía los cuatro parámetros NTP del workflow 10.
- estaban ausentes los controles UX/Admin y lenguaje objeto de investigación.
- no existían en PBX `Mlf_J129_LatinAmericanSpanish.xml` ni `Mlf_J129_CastilianSpanish.xml`.

### Intentos Apply previos

- Run 2, `Audit`: falló antes del Apply por usar SQLite y buscar tabla `endpoint`; Endpoint Configurator usa MySQL/MariaDB `endpointconfig`.
- Run 3, `Audit`: falló antes del Apply por consultar columna inexistente `e.ip_address`.
- Run 4, `main`: abortó correctamente por el guard que exige `Audit`; no hubo mutación.

Estos fallos quedan como evidencia de que los workflows no deben asumir esquema DB no validado y deben conservar guards de entorno.

### Apply UX/Admin — PASS server-side

El Apply corregido utilizó el flujo normal de Endpoint Configurator y generó:

```text
SET PROCSTAT 0
SET PROVIDE_OPTIONS_SCREEN 1
SET PROVIDE_NETWORKINFO_SCREEN 1
SET PROVIDE_LOGOUT 1
SET ENTRYNAME Briam
```

Además preservó NTP:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

Durante la observación sin NOTIFY el teléfono no hizo un GET nuevo observado y SIP permaneció `OK`. Por tanto, Apply normal genera provisioning pero no fuerza consumo inmediato en este firmware.

### Reinicio manual controlado — run `33608941143`

El workflow se ejecutó en `Audit` con operación `OBSERVE-RESTART`. Antes del reinicio confirmó SIP `OK` y que el provisioning preparado contenía los parámetros UX/NTP.

Secuencia SIP observada:

```text
t=45s  SIP OK
t=60s  SIP NOT_OK
t=150s SIP NOT_OK
t=165s SIP OK
...
t=300s SIP OK
```

Resultado:

```text
RESTART_DOWN_OBSERVED=1
SIP_RETURN_OBSERVED=1
HTTP_J100SUPGRADE_FRESH=0
HTTP_46XXSETTINGS_FRESH=0
HTTP_MAC_FILE_FRESH=0
```

El run terminó rojo porque el detector HTTP exigía contadores de access log que quedaron en cero. Esto NO invalida el reinicio ni el re-registro SIP: ambos fueron observados. El detector HTTP debe corregirse para usar una ruta de lectura autorizada/fiable antes de convertir esos contadores en criterio de PASS.

### Evidencia física posterior al reinicio

- La hora del J129 quedó correcta después del reinicio. Esto constituye evidencia física de aplicación de la configuración de tiempo preparada previamente.
- El acceso visible al menú/Admin sigue sin aparecer.
- Por tanto, `PROCSTAT 0`, `PROVIDE_OPTIONS_SCREEN 1` y `PROVIDE_NETWORKINFO_SCREEN 1` no deben describirse como parámetros que crean por sí mismos una softkey de menú. Su semántica/limitación exacta en J129 3.0.0.0.20 queda pendiente de validación.
- Antes de v1 se permite una prueba adicional específica de menú, pero no debe bloquear el parche mínimo de producción si SIP/provisioning estándar ya están validados.

## Web Admin / capacidades observadas

La interfaz Web del firmware LAB expone, entre otras, administración de red, SIP, fecha/hora, Management, Password, Debugging, Certificates, Environment Settings, Background/Screen Saver, Calendar, Restart y Reset to Default. También se observaron Syslog, SNMP, packet capture, Phone Report y controles de dispositivo.

No se encontró un botón Web visible equivalente a `Update/Get Updates`; el teléfono sí dispone de esa función local cuando el menú administrativo es accesible.

La UI SIP observada presenta una sola cuenta. Junto con las pruebas físicas, esto respalda la decisión v1 de `max_accounts=1` y `max_sip_accounts=1`.

## Idioma español

Objetivo posterior: español latinoamericano para Honduras. El XML oficial no está instalado en PBX. No inventar el archivo; usar únicamente el recurso oficial Avaya. La validación requerirá recurso oficial, consumo por el teléfono y evidencia física de UI en español.

## BUGS / deuda técnica

### BUG-EC-001
`Registered at` en GUI puede quedar obsoleto. Usar Asterisk para registro real.

### BUG-J129-002
Multicuenta histórica incorrecta. Mitigado en v1 con límite de una cuenta. El helper permanente que todavía espere valor 2 debe normalizarse antes del parche de producción.

### BUG-J129-003
Apply con cero cuentas fue corregido server-side usando `BaseEndpoint.deleteContent()`; archivo por MAC se elimina.

### BUG-J129-004
La ausencia del archivo por MAC no borra una identidad SIP ya persistida en el J129. Factory reset restableció una línea base limpia. Falta un mecanismo oficial de revocación remota o una limitación explícita de v1.

### TD-J129-005 — consumo inmediato de provisioning
Apply normal no fuerza polling inmediato. `check-sync` reinicia físicamente este firmware. No existe botón Web Update observado. Documentar restart/resync como operación separada del Apply.

### TD-J129-006 — menú local
La configuración probada no hizo aparecer el acceso visible al menú/Admin. Investigar parámetro específico o limitación de firmware sin bloquear v1 mínima.

### TD-J129-007 — detector HTTP
El workflow 11 de reinicio leyó contadores HTTP como cero. Corregir la recolección de access log mediante helper restringido y no confundir fallo de observabilidad con fallo del teléfono.

### TD-J129-008 — idioma
Falta incorporar y validar el XML oficial Latin American Spanish.

### TD-J129-009 — helpers LAB
Eliminar hardcodes históricos de IP y runtime patching; consolidar comportamiento probado en código permanente antes de producción.

## Seguridad

- No registrar SIP secrets reales.
- No imprimir contraseña Web Admin, cookies, XToken, nonce ni hashes.
- La credencial Web Admin previamente expuesta debe rotarse antes de producción.
- `J129_WEB_PASSWORD` solo como Repository Secret.
- No ampliar sudo del self-hosted runner.
- Phone Reports/exportaciones pueden contener material sensible; no subir reportes brutos al repositorio.

## Criterio para primera distribución

La primera distribución debe ser un parche conservador para Issabel 5, orientado a habilitar J129 sin modificar core innecesariamente:

1. preflight de versión/archivos/DB;
2. backup de todo archivo que vaya a tocarse;
3. instalar únicamente integración Avaya/J129 y templates requeridos;
4. registrar fabricante/modelo/prefijo/propiedades de forma idempotente;
5. `max_accounts=1`, `max_sip_accounts=1`, `max_iax2_accounts=0`;
6. no desplegar firmware automáticamente;
7. no cambiar credenciales Web Admin automáticamente en v1;
8. validar sintaxis, DB, detección y provisioning después de instalar;
9. proporcionar rollback;
10. dejar menú local, español, revocación remota y actualización sin reboot como deuda técnica explícita si no están cerrados.

## Próximo paso

1. hacer una última prueba acotada del menú, pudiendo usar el mecanismo de reinicio remoto ya validado por PBX;
2. no seguir agregando parámetros experimentales al parche mínimo sin evidencia;
3. congelar una v1 candidata;
4. construir el primer instalador/parche de producción con preflight, backup, instalación idempotente, validación y rollback.
