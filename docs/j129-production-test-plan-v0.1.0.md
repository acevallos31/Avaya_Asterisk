# Plan completo de pruebas de producción — Avaya J129 / Issabel v0.1.0

Estado: AUTOMATIZACIÓN SERVIDOR PREPARADA; PRUEBAS FÍSICAS PENDIENTES.

Central piloto: `cei-pbx02`
Release congelada: `74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3`
Runner: `cei-pbx02-j129-production`
Labels: `j129-production`, `cei-pbx02`

## Objetivo

Repetir en producción, con evidencia de GitHub Actions, todas las validaciones técnicas posibles desde la release congelada hasta el provisioning servidor. Las pruebas que requieren interacción física con un J129 quedan separadas y se ejecutarán después con un teléfono localizado y autorizado.

## Evidencia histórica ya obtenida manualmente

La instalación inicial de v0.1.0 en `cei-pbx02` ya ocurrió antes de crear el runner de producción. Por tanto, no se debe hacer rollback únicamente para recrear artificialmente una instalación desde estado virgen.

Evidencia manual existente:

- auditoría inicial: PASS;
- preflight: PASS;
- instalación: `INSTALL-PASS`;
- verify independiente: `VERIFY-PASS`;
- Apache: `Syntax OK`;
- DB: Avaya/J129/OUI y límites de cuenta correctos;
- discovery local 10.3.40.0/24: PASS;
- limitación inter-VLAN 10.3.32.0/24 confirmada por ausencia de MAC en nmap;
- generación `J100Supgrade.txt`, `46xxsettings.txt` y archivo por MAC: PASS;
- HTTP local de los tres archivos: 200 OK.

La automatización nueva debe validar el estado actual y la idempotencia sin destruir esa evidencia.

## Workflow 15

Archivo:

`.github/workflows/prod-j129-v010-server-validation.yml`

Runner obligatorio:

`[self-hosted, Linux, X64, j129-production, cei-pbx02]`

Modos:

### audit

Confirmación: `VALIDATE-PROD`

Valida:

- usuario y hostname del runner;
- branch `Audit`;
- checkout exacto del SHA congelado;
- SHA256 de los seis archivos de release;
- sintaxis de `install.sh`;
- OS, Asterisk, Python y Apache;
- Endpoint Configurator presente;
- estado de instalación v0.1.0 presente;
- contrato DB: Avaya=1, J129=1, OUI=1, max_accounts=1, max_sip_accounts=1, max_iax2_accounts=0, multicuenta=0;
- Apache Syntax OK;
- HTTP de `J100Supgrade.txt` y `46xxsettings.txt`;
- opcionalmente archivo por MAC y HTTP por MAC, sin imprimir contenido.

### preflight

Confirmación: `VALIDATE-PROD`

Ejecuta el `preflight` oficial del `install.sh` congelado y exige:

`[J129-PATCH 0.1.0] PREFLIGHT-PASS`

### verify

Confirmación: `VALIDATE-PROD`

Ejecuta el `verify` oficial del `install.sh` congelado y exige:

`[J129-PATCH 0.1.0] VERIFY-PASS`

### install-idempotency

Confirmación: `INSTALL-PROD-V010`

Secuencia:

1. verify previo;
2. install del paquete congelado;
3. verify posterior;
4. segundo install del mismo paquete;
5. auditoría final completa.

Criterio final:

`J129-PROD-INSTALL-IDEMPOTENCY-PASS`

Este modo modifica el servidor de forma controlada al repetir la misma instalación ya instalada y recargar Apache. No reinicia teléfonos ni ejecuta rollback.

## Helper privilegiado restringido

Fuente:

`deploy/j129/avaya-j129-prod-validation`

Destino esperado:

`/usr/local/sbin/avaya-j129-prod-validation`

Características:

- solo acepta llamadas vía sudo desde `github-runner-prod`;
- solo acepta hostname `cei-pbx02`;
- solo opera sobre el checkout de release esperado dentro del workspace del runner de producción;
- exige commit exacto `74d3f4...`;
- rechaza symlinks en el paquete;
- verifica SHA256 antes de ejecutar cualquier acción del instalador;
- no imprime AMPDBPASS ni credenciales SIP;
- no implementa rollback;
- `install` requiere la frase `INSTALL-PROD-V010`.

## Sudoers mínimo

El runner NO debe recibir `NOPASSWD: ALL`.

Se autoriza únicamente:

`/usr/local/sbin/avaya-j129-prod-validation`

## Evidencia

Cada corrida genera artifact sanitizado por 90 días:

`j129-production-v010-<mode>-<run_id>`

## Pruebas físicas posteriores

Con un J129 localizado y autorizado:

1. factory reset si procede;
2. discovery local por Endpoint Configurator;
3. fabricante Avaya / modelo J129;
4. asignación de una sola cuenta estándar;
5. Apply;
6. generación de archivos;
7. observar GET reales desde IP/MAC del teléfono en access_log;
8. registro SIP en Asterisk;
9. llamada entrante;
10. llamada saliente;
11. eliminación de cuenta y revocación del archivo por MAC;
12. documentar cualquier comportamiento de reboot/check-sync.

No declarar producción completa hasta que registro SIP y llamadas sean PASS.

## Rollback

No forma parte de la ejecución automática de producción. El rollback ya fue validado con el paquete exacto en LAB. En producción solo se ejecutará ante una necesidad real, con revisión del estado de endpoints y del backup previo.

## Próxima versión

La limitación de discovery inter-VLAN queda fuera de v0.1.0 y está planificada para Sprint 1 de v0.2.0.
