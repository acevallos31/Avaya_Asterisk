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

Durante 300 s:

- SIP permaneció `OK`.
- no se envió NOTIFY/check-sync.
- el J129 no realizó un nuevo GET de `46xxsettings.txt`.

Conclusión: quedó validada la generación server-side sin interrupción SIP, pero NO la aplicación de esos parámetros por el teléfono.

Chronyd quedó escuchando UDP/123 para LAN. Antes de producción, el test debe esperar y afirmar que chronyd vuelve a sincronizarse después de un restart; el run exitoso observó temporalmente `Stratum 0 / Not synchronised` inmediatamente tras reiniciarlo.

## Línea base física de pantalla

Antes del workflow 11:

- idle muestra hora, pero estaba incorrecta/desactualizada;
- flecha abajo muestra extensión `200`;
- `Briam` no aparece en idle;
- softkeys en inglés: `Redial`, `Contacts`.

`DISPLAY_NAME "Briam"` no produjo el resultado visible esperado.

## 11 — Phone UX & Admin

### Baseline read-only — PASS

Run `33603387145`:

- `SIP_STATUS=OK account=200`.
- Web UI HTTP `200`.
- Web UI HTTPS `200`.
- `46xxsettings.txt` ya contiene los cuatro parámetros NTP del workflow 10.
- ausentes: `SYSTEM_LANGUAGE`, `LANGUAGES`, `LANG0STAT`, `PROCSTAT`, `PROCPSWD`, `PROVIDE_OPTIONS_SCREEN`, `PROVIDE_NETWORKINFO_SCREEN`, `PROVIDE_LOGOUT`, controles Web gestionados, `ENTRYNAME` y `DISPLAY_NAME` global.
- no existen en PBX `Mlf_J129_LatinAmericanSpanish.xml` ni `Mlf_J129_CastilianSpanish.xml`.

### Intentos Apply 11 — todavía NO validados

Run 2, branch `Audit`: falló antes del Apply por usar SQLite y buscar tabla `endpoint`. Endpoint Configurator usa MySQL/MariaDB `endpointconfig`.

Run 3, branch `Audit`: falló antes del Apply por consultar columna inexistente `e.ip_address`.

Run 4, branch `main`: el workflow abortó en el guard `GITHUB_REF_NAME=Audit`. No hubo baseline, Apply ni mutación. Este rojo fue una protección correcta, no un fallo funcional del J129.

### Corrección necesaria antes del siguiente Apply

La investigación vigente del proyecto indica:

```text
PROCSTAT 0 -> Admin menu permitido
PROCSTAT 1 -> Admin menu restringido/no permitido para configuración
```

El intento preparado con `PROCSTAT 1` contradice el objetivo de habilitar el menú. Debe corregirse a `PROCSTAT 0` antes de ejecutar nuevamente.

## Idioma español

Objetivo: español latinoamericano para Honduras.

El XML oficial no está instalado en PBX. No inventar el archivo; usar únicamente el recurso oficial Avaya. La validación requerirá HTTP GET y evidencia física de UI en español.

## BUGS

### BUG-EC-001

`Registered at` en GUI puede quedar obsoleto. Usar Asterisk para registro real.

### BUG-J129-002

Multicuenta histórica incorrecta. Mitigado en v1 con límite de una cuenta.

### BUG-J129-003

Apply con cero cuentas fue corregido server-side usando `BaseEndpoint.deleteContent()`; archivo por MAC se elimina.

### BUG-J129-004

La ausencia del archivo por MAC no borra una identidad SIP ya persistida en el J129. Factory reset restableció una línea base limpia. Falta un mecanismo oficial de revocación remota o una limitación explícita de v1.

## Seguridad

- No registrar SIP secrets reales.
- No imprimir contraseña Web Admin, cookies, XToken, nonce ni hashes.
- La credencial Web Admin previamente expuesta debe rotarse antes de producción.
- `J129_WEB_PASSWORD` solo como Repository Secret.
- No ampliar sudo del self-hosted runner.

## Próximo paso

1. corregir workflow 11 a `PROCSTAT 0`;
2. reutilizar el flujo MySQL probado en workflow 10, sin asumir columnas nuevas;
3. ejecutar nuevo workflow 11 en branch `Audit` con `APPLY-UX`;
4. no usar `check-sync` durante la prueba no-reboot;
5. después de un Apply verde, verificar físicamente menú, `ENTRYNAME` y hora;
6. idioma español se prueba en una fase posterior del mismo 11 cuando exista el XML oficial.
