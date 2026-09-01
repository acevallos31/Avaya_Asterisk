# AGENTS.md — Avaya Asterisk / Issabel Endpoint Configurator

> Documento de contexto operativo para humanos, agentes de IA y otros modelos que trabajen en este repositorio.
>
> **Leer este archivo antes de modificar código.**

## 1. Objetivo del proyecto

Integrar teléfonos Avaya al Endpoint Configurator de Issabel manteniendo el flujo estándar de Issabel y evitando modificaciones innecesarias al core.

### Alcance actual

**Prioridad exclusiva: Avaya J129.**

Otros modelos (1603-I, 1603SW-I, 96xx, J169/J179, etc.) quedan fuera del alcance hasta estabilizar J129.

### Experiencia de usuario objetivo

1. Detección automática del endpoint.
2. Identificación como Avaya/J129.
3. Asignación desde la pestaña estándar **Accounts**.
4. Apply estándar de Issabel.
5. Issabel entrega cuentas mediante `Extension`/`setAccountList()`.
6. El vendor Avaya genera provisioning.
7. El J129 descarga configuración por HTTP/HTTPS.
8. Registro automático en Asterisk sin introducir credenciales SIP manualmente.

No crear una interfaz paralela para usuario/password SIP Avaya.

## 2. Referencias del repositorio

- `main`: referencia histórica funcional con deuda técnica. No copiar ciegamente.
- `Audit`: rama actual de auditoría, pruebas, documentación y refactor controlado.
- Issabel oficial: `IssabelFoundation/endpointconfig2` como upstream.
- `docs/j129-lab-validation.md`: evidencia física y lifecycle.
- `docs/j129-research-notes.md`: investigación oficial de firmware, Open SIP, idiomas y administración.
- `docs/agent-log.md`: bitácora compartida de agentes.

## 3. Comportamiento J129 que debemos conservar

Flujo validado:

```text
J129 boot
  -> servidor de provisioning
  -> J100Supgrade.txt
  -> 46xxsettings.txt
  -> GET $MACADDR.txt
  -> <mac>.txt
  -> credenciales/configuración SIP
  -> registro en Asterisk
```

El archivo específico puede incluir:

```text
SET FORCE_SIP_USERNAME "<extension>"
SET FORCE_SIP_PASSWORD "<secret>"
SET FORCE_SIP_EXTENSION "<extension>"
```

Los archivos se generan bajo `/tftpboot`; HTTP/HTTPS/TFTP son mecanismos de entrega separados.

## 4. Pipeline estándar de Issabel que debemos respetar

```text
endpoint_account
  -> loadEndpointIP()
  -> issabel.Extension
  -> Endpoint.setAccountList()
  -> self._accounts
  -> Avaya.Endpoint
  -> _prepareVarList()
  -> template/provisioning J129
  -> /tftpboot/<mac>.txt
```

`Extension.py` ya obtiene los datos SIP/PJSIP. Avaya no debe volver a consultar MySQL para extension/secret/display name.

## 5. Core que debe permanecer stock salvo evidencia extraordinaria

Preferir no modificar:

```text
/usr/bin/issabel-endpointconfig
/usr/share/issabel/endpoint-classes/class/issabel/BaseEndpoint.py
/usr/share/issabel/endpoint-classes/class/issabel/Extension.py
EndpointManager_Standard.class.php
```

Si se propone tocar core: justificar, comparar con upstream, añadir regresión y documentar explícitamente.

## 6. Área prevista para personalización Avaya

```text
deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
```

más metadata `manufacturer`, `model`, `model_properties`, `mac_prefix`, y artefactos oficiales de provisioning/firmware cuando corresponda.

## 7. Deuda técnica histórica que no debe regresar

- constructor Avaya especial con `ext`/`secret`;
- ramas `if Avaya` en core;
- consultas MySQL directas desde `Avaya.py`;
- logging de secretos;
- credenciales embebidas;
- lógica PHP/Python duplicada;
- secrets en argv;
- lookup externo para IP local;
- templates no compatibles con el comportamiento físico probado.

## 8. Principios SOLID

- SRP: detección, cuentas, vendor, template y file serving separados.
- OCP: extender por vendor/templates/metadata, no por ifs en core.
- LSP: constructor estándar `Endpoint(amipool, dbpool, serverip, ip, mac)`.
- ISP: no asumir que todo Avaya comparte capacidades J129.
- DIP: Avaya depende de `_accounts`, `_serverip`, `_mac`, `_model` y propiedades entregadas por Issabel.

## 9. Seguridad

Nunca almacenar passwords DB, SIP secrets reales, tokens, claves privadas ni credenciales administrativas reales.

Fixture recomendado:

```text
extension = 4200
secret = TEST-SIP-SECRET-NOT-REAL
mac = C8:1F:EA:AA:BB:CC
server = 192.0.2.10
```

Nunca imprimir `Extension.secret` en logs.

## 10. Estrategia de pruebas

### Nivel 1 — GitHub hosted

Tests estáticos/unitarios: arquitectura, SOLID, seguridad, templates, golden fixtures y regresiones.

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Nivel 2 — PBX LAB read-only

Self-hosted runner sobre Issabel 5 / Rocky 8. Permite DB SELECT, Asterisk CLI, `/tftpboot`, HTTP/HTTPS, servicios y logs.

### Nivel 3 — Integración J129

Solo manual (`workflow_dispatch`). Despliegues controlados en LAB. Nunca producción automática.

## 11. Golden path J129

```text
MAC:       C8:1F:EA:AA:BB:CC
IP phone:  192.0.2.100
PBX:       192.0.2.10
Extension: 4200
Secret:    TEST-SIP-SECRET-NOT-REAL
```

Resultado conceptual:

```text
SET FORCE_SIP_USERNAME "4200"
SET FORCE_SIP_PASSWORD "TEST-SIP-SECRET-NOT-REAL"
SET FORCE_SIP_EXTENSION "4200"
```

## 12. Protocolo obligatorio para agentes IA

Antes de trabajar:

1. leer `AGENTS.md`;
2. leer `docs/agent-log.md`;
3. leer `docs/j129-lab-validation.md`;
4. leer `docs/j129-research-notes.md`;
5. revisar commits recientes y tests;
6. no asumir que `main` es arquitectura correcta;
7. comparar con upstream cuando se toque Issabel.

Después de trabajar: ejecutar pruebas, registrar evidencia/no comprobado/riesgos, actualizar bitácora y documentación física/investigación cuando corresponda.

## 13. Identidad de agentes

Usar identificadores visibles como `OpenAI-GPT-5.6-Sol`, `Human-Axeell`, etc. No inventar versiones.

## 14. Commits

Formato recomendado:

```text
<type>(<scope>): <descripción corta>

Agent: <agent-id>
Task: <objetivo>
Tests: <resultado>
Audit: docs/agent-log.md
```

## 15. Estados de evidencia

- `STATIC-PASS`
- `LAB-READ-PASS`
- `LAB-INTEGRATION-PASS`
- `LAB-FIX-PASS`
- `PHYSICAL-J129-PASS`
- `PRODUCTION-REFERENCE`
- `NOT-TESTED`

No afirmar prueba física si solo pasó CI.

## 16. Qué NO hacer

- no push experimental directo a `main`;
- no producción automática;
- no core si el vendor puede resolverlo;
- no segundo origen de SIP secret;
- no secret en properties/argv/logs;
- no asumir soporte de otros Avaya por J129;
- no usar `Registered at` como fuente autoritativa sin Asterisk;
- no asumir que eliminar `<mac>.txt` borra credenciales ya persistidas en el J129;
- no enviar valores vacíos o comandos de logout inventados para resolver persistencia SIP;
- no actualizar firmware sin paquete oficial completo, revisión de hardware y plan de recuperación.

## 17. Definición de terminado para J129 v1

Candidata de producción cuando:

1. core Issabel permanezca stock o excepción probada;
2. detección Avaya/J129 funcione;
3. Accounts estándar funcione;
4. Apply/provisioning funcione;
5. secrets provengan de `Extension`;
6. HTTP provisioning sea reproducible;
7. tests estáticos e integración pasen;
8. J129 físico registre y complete llamadas/hold/transfer/DTMF básicos;
9. lifecycle de cambio/eliminación quede validado;
10. cero cuentas no deje provisioning secreto ni identidad activa después del mecanismo de revocación definido;
11. multicuenta se implemente correctamente o `max_accounts` se limite explícitamente;
12. idioma español y preferencias mínimas v1 queden definidos/probados;
13. política del menú Admin quede definida/probada;
14. exista rollback;
15. helper sync temporal sea retirado;
16. estrategia de firmware quede documentada, aunque upgrade automático pueda quedar para v1.1 si no es necesario para producción inicial.

## 18. Fuente de verdad

1. J129 físico + evidencia reproducible;
2. Asterisk para registro SIP real;
3. documentación oficial Avaya del firmware/modelo;
4. upstream Issabel;
5. tests;
6. referencia histórica de `main`;
7. suposiciones antiguas.

## 19. Estado validado del laboratorio — 2026-09-01 02:05 -06:00

Validado:

- `PHYSICAL-J129-PASS` — detección automática Avaya/J129.
- `LAB-INTEGRATION-PASS` — metadata controlada en Endpoint Configurator.
- `LAB-INTEGRATION-PASS` — Accounts estándar sin UI SIP paralela.
- `PHYSICAL-J129-PASS` — provisioning HTTP `J100Supgrade -> 46xxsettings -> <mac>`.
- `PHYSICAL-J129-PASS` — registro `chan_sip`.
- `PHYSICAL-J129-PASS` — ciclo Remove/Rescan/Reassign/Apply/Reboot/Register.
- `PHYSICAL-J129-PASS` — cambio de extensión.
- `PHYSICAL-J129-PASS` — eliminar una de dos cuentas y volver a 201.
- `LAB-FIX-PASS` — `BUG-J129-003`: con cero cuentas el Apply ahora termina bien y elimina `/tftpboot/<mac>.txt`.
- `PHYSICAL-J129-PASS` como reproducción de `BUG-J129-004`: aun con 0 cuentas y archivo MAC ausente, después de reboot el teléfono volvió a registrar la identidad `201` persistida localmente.

### Bugs abiertos

`BUG-EC-001`: GUI `Registered at` puede mostrar peer obsoleto/UNREACHABLE.

`BUG-J129-002`: metadata permite 2 cuentas pero el template actual no crea dos registros SIP independientes; la segunda cuenta gana.

`BUG-J129-004`: borrar provisioning server-side no limpia credenciales SIP persistidas localmente. No inventar solución; investigar logout/revocación oficial.

### Firmware / Open SIP

- J129 LAB: firmware `3.0.0.0.20`.
- Release oficial investigado: J100 SIP `4.1.11.0`, binario J129 `FW_S_J129_R4_1_11_0_10.bin`.
- Avaya lista Open SIP con Asterisk R16; nuestro Asterisk 18.19.0 está probado por evidencia propia, no como certificación oficial.
- PBX como servidor de firmware es técnicamente viable por HTTP/HTTPS, pero debe existir workflow/procedimiento separado y controlado.
- No actualizar todavía el J129 físico sin identificar hardware/comcode, revisar advisements y preparar recovery.

### Idioma / preferencias / administración

- Paquetes oficiales incluyen `Mlf_J129_LatinAmericanSpanish.xml` y `Mlf_J129_CastilianSpanish.xml`.
- Para Honduras, candidato inicial: Latin American Spanish.
- `PROCSTAT 0` permite Admin menu; `PROCSTAT 1` impide administración mediante ese menú.
- `PROCPSWD`/`ADMIN_PASSWORD` corresponde al menú Admin físico, no al password Web UI.
- SSH J100 es Avaya Services/EASG; no mapear credenciales SSH genéricas de Issabel sin evidencia.
- En Open SIP evaluar parámetros oficiales `ENABLE_AVAYA_ENVIRONMENT 0`, `DISCOVER_AVAYA_ENVIRONMENT 0`, `ENABLE_IPOFFICE 0`.

### Próxima sesión — orden recomendado

1. investigar y resolver `BUG-J129-004`;
2. identificar hardware/comcode del J129 LAB;
3. preparar firmware audit read-only, sin upgrade;
4. validar español latinoamericano;
5. probar política `PROCSTAT`/Admin menu con recovery definido;
6. definir preferencias mínimas de v1 (zona horaria, fecha/hora, dial plan, etc.);
7. revisar `BUG-J129-002` con sintaxis moderna multicuenta;
8. pruebas llamadas/DTMF/hold/transfer;
9. segunda validación de Remove con check directo de archivo MAC;
10. rescan/bulk Apply/offline/idempotencia;
11. rollback/reinstall final y cleanup de helper sync;
12. solo después evaluar upgrade de firmware controlado.

Toda investigación detallada queda en `docs/j129-research-notes.md` y toda evidencia física en `docs/j129-lab-validation.md`.
