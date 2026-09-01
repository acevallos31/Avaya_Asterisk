# Agent Audit Log

Registro compartido de trabajo realizado por humanos y agentes de IA en Avaya_Asterisk.

Este archivo complementa el historial de Git. No reemplaza commits ni Pull Requests: explica **intención, evidencia, decisiones y pendientes** para que otro agente pueda continuar sin reconstruir todo el contexto.

Consultar primero `AGENTS.md`.

---

## Reglas del registro

Cada agente debe agregar una entrada por unidad de trabajo significativa. No borrar entradas anteriores. Si una conclusión cambia, agregar una nueva entrada que la sustituya y referenciar la anterior. No almacenar secretos reales.

Estados permitidos:

- `STATIC-PASS`
- `LAB-READ-PASS`
- `LAB-INTEGRATION-PASS`
- `LAB-FIX-PASS`
- `PHYSICAL-J129-PASS`
- `PRODUCTION-REFERENCE`
- `NOT-TESTED`

---

## 2026-08-31 12:51 -06:00 — OpenAI-GPT-5.6-Sol

**Objetivo:** Consolidar contexto técnico y reglas de colaboración antes del refactor J129.

**Rama:** `Audit`

**Decisiones principales:** limitar alcance a J129; conservar comportamiento funcional mediante tests; mantener core Issabel stock; hacer que Avaya consuma `_accounts`/`Extension`; usar global -> `GET $MACADDR.txt` -> archivo MAC; workflows modificadores manuales.

**Evidencia:** `PRODUCTION-REFERENCE` para `main`; `STATIC-PASS` para core upstream; trabajo de LAB todavía pendiente en ese momento.

**Commits:**
- `0857495e9d72ac48e6cf48786a4c6e10a7887845 Add SOLID audit contract tests`
- `2c71565da242b006496d3c0068ac438a23186e2f docs: add shared AI agent context and collaboration protocol`

---

## 2026-08-31 12:55 -06:00 — OpenAI-GPT-5.6-Sol

**Objetivo:** Crear golden contracts J129 antes de modificar lógica funcional.

**Rama:** `Audit`

**Decisiones:** proteger `GET $MACADDR.txt`, `FORCE_SIP_USERNAME`, `FORCE_SIP_PASSWORD`, `FORCE_SIP_EXTENSION`, normalización MAC; template objetivo debe usar objetos `Extension`; fixture solo con credenciales ficticias.

**Commit:**
- `43a291bfb98f97ad37b779f2438ca9d257ee7f18 test(j129): add golden provisioning contracts`

---

## 2026-09-01 01:20 -06:00 — OpenAI-GPT-5.6-Sol

**Objetivo:** Consolidar evidencia física inicial y lifecycle.

**Rama:** `Audit`

**Decisiones:** Asterisk es fuente autoritativa para registro; registrar `BUG-EC-001`; registrar `BUG-J129-002`; no corregir multicuenta a ciegas.

**Evidencia:** detección, provisioning HTTP, registro SIP, Remove/Rescan/Reassign, cambio de extensión, reproducción multicuenta y eliminación de una de dos cuentas.

**Commits relevantes:**
- `9e0be9f582411e11733729a6aa4f3c63be1addc9 docs(j129): registrar validacion fisica y bug de estado SIP`
- `d3e8d5634c6c653b0d4ee5a1bb2f7720a065b23d docs(agents): actualizar estado validado del J129`
- `14de62cc9858924554c2255e7a73cb36ffa18b8e docs(j129): registrar fallo físico de multicuenta`
- `11aed919747aad07ca7a708f936b918040d26b52 docs(j129): documentar eliminacion de cuenta y estado fisico`

---

## 2026-09-01 02:05 -06:00 — OpenAI-GPT-5.6-Sol

**Objetivo:** Cerrar la sesión con el estado real del J129, documentar bugs de lifecycle, actualizar contexto y dejar investigación de firmware/idioma/administración para continuidad.

**Rama:** `Audit`

**Base revisada:**
- overlay Avaya J129 actual;
- workflows de State/Provisioning/Deploy;
- evidencia física del J129 LAB;
- documentación oficial Avaya J129/J100 Open SIP y Readmes de firmware.

**Archivos modificados durante esta etapa:**
- `tests/audit/test_j129_golden.py`
- `deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py`
- `.github/workflows/lab-j129-state-audit.yml`
- `docs/j129-lab-validation.md`
- `docs/j129-research-notes.md`
- `AGENTS.md`
- `docs/agent-log.md`

**Decisiones:**
- agregar estado `configured_no_accounts` para distinguir endpoint existente con cero cuentas de `removed`;
- clasificar `BUG-J129-003` cuando Apply con cero cuentas dejaba provisioning viejo;
- corregir `BUG-J129-003` reutilizando `BaseEndpoint.deleteContent()` en vez de tocar core;
- no considerar la corrección completa hasta validar teléfono físico;
- registrar `BUG-J129-004` al comprobar que el J129 conserva y reutiliza credenciales SIP locales aunque el archivo MAC ya no exista;
- no intentar resolver `BUG-J129-004` con valores vacíos o parámetros inventados;
- investigar firmware y administración antes de seguir ampliando features;
- considerar viable que la PBX sirva firmware por HTTP/HTTPS, pero con workflow/proceso separado y controlado;
- mantener upgrade físico pendiente hasta identificar hardware/comcode y revisar advisements;
- español latinoamericano es candidato para Honduras mediante `Mlf_J129_LatinAmericanSpanish.xml`;
- `PROCSTAT` es candidato oficial para política de Admin menu;
- no mapear credenciales SSH genéricas porque J100 SSH es Avaya Services/EASG.

**Pruebas/evidencia:**
- `LAB-INTEGRATION-PASS` — endpoint J129 existe con 0 cuentas y `configured_no_accounts` verde antes del Apply general.
- `LAB-INTEGRATION-PASS` — reproducción `BUG-J129-003`: Apply falló con cero cuentas y el archivo MAC antiguo permaneció con identidad/secret de 201.
- `STATIC-PASS` — contrato añadido para el caso `_accounts=[]`.
- `LAB-FIX-PASS` — deploy de `efaa562...`, Apply general con 0 cuentas terminó sin error.
- `LAB-FIX-PASS` — Provisioning Audit #9: 0 cuentas, `/tftpboot/c81fea9b650d.txt AUSENTE`, globals presentes.
- `LAB-INTEGRATION-PASS` — State Audit `configured_no_accounts` verde pre-reboot.
- `PHYSICAL-J129-PASS` como reproducción de defecto — después del reboot, Asterisk mostró `201/201 192.168.1.171 OK`; el teléfono conservó su identidad local pese a no existir archivo MAC. Esto abre `BUG-J129-004`.

**Commits de esta etapa:**
- `19c7e20657c88741008df05783632987e755e34c docs(j129): registrar estado sin cuentas antes del apply general`
- `a7525428b783c9105f99608c683dd68709e9c17c docs(j129): registrar provisioning obsoleto con cero cuentas`
- `38ea0566a1fe6e2a46004b9d7aad4156fa568c35 test(j129): cubrir apply con cero cuentas`
- `efaa562190ef4afbfd4c91379b13d4246ad39515 fix(j129): revocar provisioning al quedar sin cuentas`
- `64e67e5583006c599dbeef0860f2124997060e91 docs(j129): validar correccion server-side sin cuentas`
- `4cef4def52900d1d024179ed290c6a653336795a docs(j129): registrar persistencia SIP local sin archivo MAC`
- `e1c69746b06b2753b6c5a7a046397b2d1562a47a docs(j129): agregar investigacion tecnica de firmware y administracion`
- `b7f41abf0f4a641af49cd565e6bbd6efe9b9a8b9 docs(agents): actualizar contexto J129 y roadmap de cierre v1`

**Investigación oficial relevante:**
- firmware LAB: `3.0.0.0.20`;
- firmware oficial investigado: J100 SIP `4.1.11.0`, binario J129 `FW_S_J129_R4_1_11_0_10.bin`;
- Readme 4.1.11.0 lista Open SIP y Asterisk R16;
- PBX/file server HTTP/HTTPS puede alojar J100Supgrade, binarios y language XML;
- idiomas oficiales J129 incluyen Latin American Spanish y Castilian Spanish;
- issues Open SIP relevantes: HTTP redirect -> HTTPS certificate failure (`SIP96X1-41164`), TRUSTCERTS/HTTPS (`SIP96X1-89301`), Netsapiens Web UI mode (`SIP96X1-66640`);
- `PROCSTAT 0/1` controla disponibilidad del Admin menu;
- para Open SIP deben evaluarse `ENABLE_AVAYA_ENVIRONMENT 0`, `DISCOVER_AVAYA_ENVIRONMENT 0`, `ENABLE_IPOFFICE 0`.

**Riesgos / no comprobado:**
- no se conoce aún mecanismo oficial de revocación remota de `FORCE_SIP_*` persistidos (`BUG-J129-004`);
- no se ha identificado aún comcode/hardware revision exacto del teléfono LAB;
- no se ha probado upgrade de firmware;
- no se ha probado todavía español latinoamericano;
- no se ha probado `PROCSTAT` físicamente;
- multicuenta sigue incorrecta (`BUG-J129-002`);
- helper sync privilegiado sigue siendo temporal;
- falta segunda validación Remove con check directo de archivo MAC;
- falta llamadas/DTMF/hold/transfer, bulk Apply, offline e idempotencia.

**Siguiente paso recomendado:**
1. resolver por documentación oficial `BUG-J129-004`;
2. identificar hardware/comcode;
3. preparar workflow de auditoría de firmware read-only;
4. probar idioma español latinoamericano;
5. probar `PROCSTAT` con recovery documentado;
6. definir preferencias mínimas v1;
7. revisar multicuenta;
8. pruebas funcionales SIP completas;
9. lifecycle final y cleanup;
10. evaluar upgrade de firmware solo después.

---

## Handoff actual

El próximo agente debe leer, en este orden:

1. `AGENTS.md`;
2. `docs/j129-lab-validation.md`;
3. `docs/j129-research-notes.md`;
4. `docs/agent-log.md`;
5. commits recientes de `Audit`.

No debe reiniciar trabajo desde supuestos antiguos. El punto técnico más importante para continuar es `BUG-J129-004`: el servidor ya revoca el archivo MAC correctamente con 0 cuentas, pero el J129 físico conserva y vuelve a registrar `201` desde almacenamiento local. La solución debe basarse en semántica oficial Avaya, no en valores vacíos inventados.
