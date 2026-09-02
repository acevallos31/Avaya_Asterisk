# AGENTS.md — Avaya Asterisk / Issabel Endpoint Configurator

> Contexto operativo obligatorio para humanos y agentes de IA. Leer antes de modificar código.

## Objetivo

Integrar Avaya J129 al Endpoint Configurator estándar de Issabel 5 sin crear una UI paralela para credenciales SIP y evitando cambios al core de Issabel.

Flujo esperado:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Ramas

- `main`: referencia/histórico y workflows visibles en Actions; no usar para pruebas mutantes LAB.
- `Audit`: rama de trabajo, pruebas y validación LAB.
- Todo workflow mutante LAB debe abortar si `GITHUB_REF_NAME != Audit`.

## LAB actual — 2026-09-02

- Issabel 5 / Rocky Linux 8.
- Asterisk 18.19.0.
- PBX/provisioning: `192.168.1.10`.
- J129: `192.168.1.168`.
- MAC: `C8:1F:EA:9B:65:0D`.
- Firmware: `3.0.0.0.20`.
- Endpoint id: `3`.
- Cuenta SIP actual: `200`.
- `192.168.1.169` está ocupado por otro dispositivo; no usarlo para la PBX.

## Arquitectura obligatoria

El vendor Avaya debe consumir `_accounts` entregadas por Issabel. No reconsultar secretos SIP desde DB.

No modificar salvo evidencia extraordinaria:

```text
/usr/bin/issabel-endpointconfig
BaseEndpoint.py
Extension.py
EndpointManager_Standard.class.php
```

Personalización prevista:

```text
deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
```

## Seguridad

Nunca almacenar ni imprimir secretos SIP reales, contraseña Web Admin, cookies, XToken, nonce, hashes de autenticación, tokens o claves privadas.

La credencial Web Admin usada anteriormente debe considerarse expuesta y rotarse antes de producción. `J129_WEB_PASSWORD` permanece solo como GitHub Repository Secret.

No ampliar sudo del runner. Mantener helpers restringidos.

## J129 v1 — una sola cuenta

Workflow 08 validó en LAB:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

Multicuenta sigue fuera de alcance hasta contar con sintaxis oficial probada.

## Workflows validados

### 07 — Rescan Idempotency

`LAB-INTEGRATION-PASS`: dos rescans no duplican endpoint ni pierden cuenta 200.

### 08 — Single Account V1

`LAB-INTEGRATION-PASS`: J129 v1 queda limitado a una cuenta.

### 09 — Remote Provisioning / comportamiento real

`PHYSICAL-J129-PASS`: `check-sync` provoca reinicio físico, nueva descarga de provisioning y re-registro SIP. No documentarlo como reload silencioso.

### 10 — Forced Provisioning / NTP

`LAB-INTEGRATION-PASS` server-side:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

Apply normal de Issabel regeneró `46xxsettings.txt` sin caída SIP. El J129 NO hizo un GET nuevo de `46xxsettings.txt` durante 300 s, por lo que no afirmar que aplicó los parámetros en el teléfono.

Chronyd quedó habilitado para `192.168.1.0/24`, pero antes de producción el test debe esperar/asegurar que chronyd vuelva a estado sincronizado después de restart.

### 11 — Phone UX & Admin

Baseline read-only verde:

- SIP 200 `OK`.
- HTTP y HTTPS del J129 responden 200.
- no existen archivos `Mlf_J129_LatinAmericanSpanish.xml` ni `Mlf_J129_CastilianSpanish.xml` en PBX.
- ausentes en provisioning: idioma, menú UX, Web Admin gestionado y `ENTRYNAME`.
- parámetros NTP del workflow 10 presentes.

Intentos Apply del 11:

1. falló por usar SQLite incorrectamente (`no such table: endpoint`); no llegó a Apply.
2. falló por consultar columna inexistente `endpoint.ip_address`; no llegó a Apply.
3. el run más reciente fue lanzado por error sobre `main`; el guard de entorno falló antes de cualquier mutación.

No usar Copilot para adivinar el esquema DB. Reutilizar las consultas MySQL ya probadas en workflow 10.

## Corrección crítica sobre PROCSTAT

Documentación/investigación actual del proyecto indica:

```text
PROCSTAT 0 -> Admin menu permitido
PROCSTAT 1 -> Admin menu restringido/no permitido para configuración
```

Por lo tanto, el workflow 11 NO debe aplicar `PROCSTAT 1` si el objetivo es habilitar el menú físico. Antes del próximo Apply, corregir a `PROCSTAT 0` y mantener recuperación documentada.

## Idioma

El objetivo es español latinoamericano para Honduras. El LAB no tiene todavía el XML oficial. No inventar ni reconstruir el XML. Incorporarlo solo desde paquete oficial Avaya y validar descarga HTTP + cambio físico.

## Nombre visible

`DISPLAY_NAME` no produjo `Briam` visible en idle. `ENTRYNAME` es candidato de investigación/prueba, pero no afirmar resultado hasta evidencia física.

## BUGS abiertos

- `BUG-EC-001`: GUI `Registered at` puede quedar obsoleta; Asterisk es fuente autoritativa.
- `BUG-J129-002`: multicuenta histórica incorrecta; v1 limitado a una cuenta.
- `BUG-J129-004`: eliminar provisioning server-side no borra identidad SIP persistida localmente; factory reset produjo línea base limpia. Resolver/documentar con mecanismo oficial.

## Deuda técnica antes de producción

- normalizar helper permanente; hoy varios workflows usan runtime prepare/patch.
- remover IPs históricas hardcodeadas.
- normalizar DB installer a una cuenta.
- incorporar parámetros NTP/UX validados a fuente overlay, no solo copia desplegada LAB.
- fortalecer post-restart de chronyd.
- revisar rollback de workflows mutantes.
- rotar credencial Web Admin comprometida.

## Regla para DB Endpoint Configurator

La base real es MySQL/MariaDB `endpointconfig`, no SQLite. No asumir nombres de columnas. Antes de escribir una nueva consulta, reutilizar una consulta ya validada o añadir primero una auditoría read-only de esquema.

## Próximo paso obligatorio

Antes del siguiente Apply 11:

1. corregir `PROCSTAT` a `0`;
2. revisar el helper contra el flujo MySQL validado del workflow 10;
3. ejecutar tests estáticos;
4. lanzar NUEVO workflow 11 en branch `Audit`, nunca rerun de SHA viejo y nunca `main`;
5. confirmar `APPLY-UX`;
6. verificar server-side y SIP antes de cualquier trigger al teléfono;
7. no enviar `check-sync` durante la prueba no-reboot;
8. después pedir observación física del menú, nombre y hora.

## Protocolo para agentes

Leer en orden:

1. `AGENTS.md`;
2. `docs/j129-lab-validation.md`;
3. `docs/j129-research-notes.md`;
4. `docs/agent-log.md`;
5. commits y runs recientes de `Audit`.

No afirmar `PHYSICAL-J129-PASS` si solo pasó CI/LAB server-side.
