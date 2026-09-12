# Agent Audit Log

Registro compartido de trabajo humano/IA en `Avaya_Asterisk`. Consultar primero `AGENTS.md`, `CONTEXT.md` y `docs/j129-test-registry.md`. No almacenar secretos reales.

Estados usados:

```text
STATIC-PASS
LAB-READ-PASS
LAB-INTEGRATION-PASS
LAB-FIX-PASS
PHYSICAL-J129-PASS
INFRA-BLOCKED
HARNESS-FAIL
RELEASE-PASS
PRODUCTION-SERVER-PASS
PRODUCTION-PHYSICAL-PASS
PRODUCTION-END-TO-END-SERVER-AUDIT-PASS
NOT-TESTED
```

---

## 2026-09-11 — Codex — GRP2601P Tests 62–64

Se inició el ciclo autorizado sobre un GRP2601P de fábrica. Test 62 run
`34620373267` identificó de forma read-only `192.168.1.176`,
`EC:74:D7:1E:E8:E3`, modelo GRP2601P y HTTP 200. Confirmó ausencia stock de
OUI y modelo. El run previo `34619751876` contenía un falso positivo de OUI
por el parser del reporte; se corrigió y repitió.

Test 63 run inicial `34620205736` se detuvo antes de escribir porque la OUI
no existía. Se amplió el cambio reversible para insertar OUI y modelo. Run
`34620390872`: OUI APPLY PASS, modelo ID 149, dos cuentas SIP máximas y
discovery stock exacto PASS; fila única, no seleccionada y sin cuentas.

Antes de modificar el helper se retiraron los triggers por cambios del helper
de los workflows mutantes GXP1630, evitando repetir Configure accidentalmente.
Los audits 58/61 se limitaron a activarse por cambios de su propio workflow.

Test 64 run `34620889592`: preflight server PASS y
`CREDENTIAL-BLOCKED` por ausencia de
`GRANDSTREAM_GRP_HTTP_DEFAULT_PASSWORD`. Los runs
`34628195632`/`34628373795` apuntaron por error a
`GRANDSTREAM_GXP_HTTP_DEFAULT_PASSWORD`; el primero además expuso y permitió
corregir un `HARNESS-FAIL` del parser. Esa evidencia no evaluaba el secreto
que indicó el operador.

El workflow se corrigió para usar
`GRANDSTREAM_GXP1625_HTTP_PASSWORD`. Run definitivo `34642689024`: identidad
IP/MAC exacta, preflight server PASS, HTTP 200, `login=FAILED` y
`TEST64-GRP2601P-AUTH-READ=GXP-CANDIDATE-REJECTED`. No hubo escrituras,
reinicio, provisioning ni firmware upgrade.

Estado actual: Endpoint Configurator ya detecta GRP2601P. La contraseña del
GXP1625 tampoco autentica este equipo; se requiere la contraseña aleatoria de
la etiqueta en el secret GRP dedicado. Provisioning autenticado, cfg/XML y SIP
siguen `NOT-TESTED` hasta cerrar Test 64.

La credencial de etiqueta se cargó posteriormente en el secret MAC-bound
`GRANDSTREAM_GRP2601P_EC74D71EE8E3_HTTP_PASSWORD`. Run `34647374500`:
secret presente e identidad exacta, pero login falló. Para excluir una
diferencia de formato del SID se añadió clasificación sanitizada y se repitió
sin escrituras. Run confirmatorio `34647476040`: HTTP 200,
`login_response_class=ERROR`, cuerpo string y `login=FAILED`. El teléfono
rechazó explícitamente la credencial. Se suspenden más intentos hasta verificar
visualmente caracteres y copia del valor de la etiqueta.


## 2026-09-12 — Codex — diseño de credenciales Endpoint Configurator

Se formalizó `docs/endpoint-configurator-credential-lifecycle.md` para la
contraseña administrativa final global por PBX y el override opcional por MAC.
El diseño separa credencial inicial, contraseña Web Admin final y secretos SIP;
define cifrado en reposo, importación masiva sin persistir CSV, rotación por
lotes, rollback y estados de registro SIP consultados desde Asterisk.

Se actualizó `AGENTS.md` con las reglas de seguridad correspondientes. No se
modificó código operativo ni se ejecutó Configure; el siguiente paso es
implementar el almacenamiento cifrado y el menú en LAB.


## 2026-09-11 — Codex — inicia Test 57 GXP1630 provisioning cycle

El operador autorizó completar y documentar el ciclo LAB sin nuevas preguntas.
Se inicia con bootstrap controlado P212/P237 y guardas exactas de IP/MAC; las
fases posteriores deben detenerse ante conflicto de identidad, cuenta o SIP.

Resultado: bootstrap/reboot `34584178016` PASS; modelo/discovery
`34585294581` PASS; Configure 201 `34585596964` PASS; auditoría E2E
`34585916245` PASS. Estado `LAB-INTEGRATION-PASS`, físico pendiente.

## 2026-09-11 — Codex — inicia Test 56 GXP1630 factory-state discovery

El operador conectó un GXP1630 de fábrica a la red LAB. Se reservó Test 56 para
discovery automático read-only de IP/MAC/modelo y comparación inicial con las
superficies HTTP usadas por GXP1625. Esta fase no configura, reinicia ni escribe
en el teléfono o Endpoint Configurator.

Run `34578860986` terminó PASS: coincidencia única `192.168.1.169`, MAC
`C0:74:AD:B4:AD:70`, modelo GXP1630. `/manager` no respondió y
`api.values.get` sí respondió. La siguiente fase debe validar autenticación y
lectura de estado sin asumir aún compatibilidad completa de provisioning.

Run `34580059714` añadió inventario read-only: modelo/IP/MAC volvieron a
coincidir, pero firmware y hardware quedaron `NOT_EXPOSED_UNAUTHENTICATED`.
No se intentaron credenciales por defecto.

Run inicial `34583129574` fue `HARNESS-FAIL` antes del login porque `ping` no
dispone de CAP_NET_RAW en endpoint-lab. Se sustituyó por una guarda HTTP sin
ampliar privilegios. Run `34583242705` pasó login y lectura autenticada: contrato
GXP1625 compatible y provisioning de fábrica vacío; `phone_write=NO`.

## 2026-09-11 — Codex — Test 55 cerrado con validación física satisfactoria

El operador confirmó que la prueba manual ya fue completada satisfactoriamente
y que el GXP1625 se configuró correctamente. Esta evidencia física, junto con
`TEST55-POST-CONFIG-AUDIT=PASS` del run `34543757258`, cierra Test 55 como
`LAB-INTEGRATION-PASS` y `PHYSICAL-GXP1625-PASS`.

El workflow quedó manual-only con operaciones read-only `post-config-audit` y
`post-reset-audit`; `factory-reset` conserva confirmación destructiva exacta por
MAC. Próximo paso: paquete RC y preflight controlado de Ceiba. Producción no fue
tocada.

## 2026-09-10 — Codex — Test 55 post-Configure corroborado en servidor

El operador ejecutó Configure sobre la única fila `C0:74:AD:E8:66:09` en
`192.168.1.168`; la UI informó que todos los endpoints fueron configurados y
registró respuesta Grandstream `success`.

Run `34543757258` ejecutó solo el modo read-only post-Configure (los jobs de
remoción y factory reset quedaron `skipped`) y terminó
`TEST55-POST-CONFIG-AUDIT=PASS`:

```text
endpoint_rows=1
endpoint_ip=192.168.1.168
manufacturer=Grandstream
model=GXP1625
selected=0
account_count=1
target_account_202_sip_count=1
binary_cfg_present=YES
xml_cfg_present=YES
xml_root_valid=YES
xml_mac_binding=YES
xml_p35_target_202=YES
xml_p36_target_202=YES
xml_p47_target_pbx=YES
xml_p270_target_ashly=YES
target_ip=192.168.1.168
target_registration_match=YES
previous_ip=(Unspecified)
phone_http_status=200
```

La auditoría estática general del repositorio pasó en `34543757263`. La
validación física posterior fue confirmada satisfactoria por el operador el
2026-09-11; producción no fue tocada.

## 2026-09-10 — Codex — Test 55 factory reset y baseline post-reset

Después de eliminar manualmente el endpoint, la IP `192.168.1.167` apareció
como DVR Hikvision. El discovery read-only run `34541156644` encontró una única
coincidencia de la MAC GXP1625 `C0:74:AD:E8:66:09` en `192.168.1.168`.

El run `34541419730` pasó la etapa destructiva controlada: guard exacto de MAC,
login autenticado, un único control factory reset, caída HTTP y retorno HTTP.
Marcadores: `factory_reset_observed=YES` y
`TEST55-FACTORY-RESET=PASS`. El job posterior falló porque el endpoint fue
redescubierto automáticamente y la expectativa histórica de cero filas dejó de
ser válida.

Se protegió el workflow en commits `f7141d1`, `315d372` y `52a1c06`. El reset
ya no puede ejecutarse por push: exige dispatch manual, operación explícita y
confirmación `FACTORY-RESET-C074ADE86609`. El modo push es exclusivamente una
auditoría read-only.

Run `34542431592`: `LAB-READ-PASS` y
`TEST55-POST-RESET-AUDIT=PASS`:

```text
endpoint_rows=1
endpoint_ip=192.168.1.168
manufacturer=Grandstream
model=GXP1625
selected=0
account_count=0
http_password_override_count=0
binary_cfg_absent=YES
xml_cfg_absent=YES
extension_201_exists=YES
extension_202_exists=YES
extension_202_registered_at_target_ip=YES
extension_202_status=UNKNOWN
phone_http_status=200
```

Los jobs de remoción y factory reset quedaron `skipped` en ese run. La dirección
del peer 202 puede ser un binding cacheado; `UNKNOWN` no se promueve a evidencia
de registro activo. Producción no fue modificada. Pendiente: asignar manualmente
`202 / Ashly` desde Endpoint Configurator y validar provisioning/SIP/llamada.

## 2026-09-10 — Codex — cierre nativo Grandstream GXP1625

Se ejecutó H8L run `34506170492` en modo read-only. El login fue aceptado sin
User-Agent explícito y con User-Agent genérico; ambos casos devolvieron HTTP
200, JSON success y SID sin publicar valores sensibles.

H8M run `34506766259` probó el contrato mínimo: el primer ciclo E2E pasó y el
segundo, separado 60 s, falló en activación aunque regeneró XML. El rollback
automático restauró H8J y limpió la selección.

H8M run `34507118291` repitió con 300 s: ambos ciclos terminaron
`grandstream_finished_seen=YES`, `grandstream_failed_seen=NO`, XML 202/Ashly
correcto, `selected_after_applyconfig=0`, SIP 202 `OK` desde `192.168.1.167` y
201 liberada. Se retuvo el parche mínimo sin User-Agent fijo.

Estado: `LAB-INTEGRATION-PASS`. Próximo paso: paquete reproducible, smoke test
exacto en LAB y preflight read-only de la PBX productiva seleccionada.

## 2026-08-31 — OpenAI GPT-5.6 Sol

Se consolidó el contrato de arquitectura J129: core Issabel stock, Accounts estándar, Avaya consume `_accounts`, provisioning global -> `GET $MACADDR.txt` -> archivo por MAC, sin consultas directas de secretos desde vendor.

## 2026-09-01 — OpenAI GPT-5.6 Sol

Se validó físicamente discovery, provisioning HTTP, registro SIP y lifecycle en LAB. Se registraron bugs y deuda de comportamiento del J129.

## 2026-09-02 — OpenAI GPT-5.6 Sol — LAB/release

07–14 quedaron validados/documentados: rescan idempotente, single-account, lifecycle físico, NTP, UX/admin, production patch, smoke test exacto y freeze manifest. Release congelada: `74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3`.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Producción

Workflow 15 validó:

```text
audit                PASS  run 33692817597
preflight            PASS  run 33694718272
verify               PASS  run 33695299816
install-idempotency  PASS  run 33695636455
```

Estado: `PRODUCTION-SERVER-PASS`.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Cierre físico de producción

```text
45 | Production | J129 Physical Validation | Registration & Operation
PRODUCTION-PHYSICAL-PASS
```

El operador confirmó que el J129 registró y funciona correctamente.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 46

Primer run `33701760211`: `HARNESS-FAIL` por ausencia del checkout de la release congelada. No se auditó ni modificó la PBX. Se corrigió el workflow en commit `6bdc195bd0f6d5ef396a78fc437f9145d7209c1b`.

Run válido:

```text
33702529808
PRODUCTION-END-TO-END-SERVER-AUDIT-PASS
```

Marcadores observados:

```text
J129-PROD-FROZEN-PACKAGE-PASS
J129-PROD-SERVER-AUDIT-PASS
J129-PROD-PROVISIONING-AUDIT-PASS
J129-PROD-E2E-RELEASE-VERIFY-PASS
J129-PROD-E2E-HTTP-PASS
J129-PROD-E2E-APACHE-PASS
J129-PROD-MAC-PROVISIONING-PASS=c81feac3d6b2
```

La MAC validada fue `C8:1F:EA:C3:D6:B2`.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 47 cerrado para v0.1.0

Workflow:

```text
.github/workflows/prod-j129-physical-call-e2e.yml
47 | J129 Production | Physical Call | Controlled E2E
```

Evolución:

```text
33703875115  INFRA-BLOCKED: runner sin acceso directo al socket CLI
33710642058  preflight PASS mediante helper restringido
33711068591  llamada automatizada PASS
```

Para habilitar el acceso controlado se creó e instaló:

```text
deploy/j129/avaya-j129-prod-call-test
deploy/j129/avaya-j129-prod-call-test.sudoers
/usr/local/sbin/avaya-j129-prod-call-test
```

No se concedió `sudo asterisk` ni shell root genérico.

Run `33711068591`:

```text
peer 4455 READY
J129 IP 10.3.40.32
MAC C8:1F:EA:C3:D6:B2
100 Trying
180 Ringing
Asterisk mostró SIP/4455 Ringing
cleanup PASS
```

No había operador físicamente junto al J129; `answer` y audio quedaron `NOT-TESTED`. La prueba se cierra para v0.1.0 sin promover este run a evidencia física. La validación física previa 45 sigue siendo la evidencia de operación real en producción.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 48 reservado para v0.2.x

Reservado:

```text
48 | Issabel Lab | J129 Remote-Originated Call | 3PCC/Control Probe
NOT-TESTED
```

Objetivo: investigar primero en LAB si el propio J129 puede iniciar/controlar remotamente una llamada hacia otra extensión, diferenciando ese flujo de un originate generado por Asterisk. No se hará en producción hasta tener evidencia LAB y un procedimiento controlado.

Decisión de secuencia actual: después de actualizar documentación/roadmap de v0.2.x, continuar con esta prueba en el ambiente de laboratorio.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Scripts operativos y roadmap de flota

La carpeta `scripts/` pasa a considerarse catálogo operativo permanente, no solo tooling de pruebas. Se documentó evolución hacia categorías de bootstrap, deploy, diagnostics, maintenance, security y testing.

Se agregó:

```text
docs/pbx-fleet-control-roadmap.md
```

Visión futura: servidor local de distribución/control para múltiples PBX Issabel, con inventario, releases aprobadas, preflight/deploy/verify/rollback, diagnósticos remotos y bootstrap de nuevas PBX. La intención es lograr una experiencia similar a GitHub Actions dentro de la red propia, sin convertir el controlador en una vía de shell root genérico.

Decisión de prioridad: no iniciar todavía el PBX Fleet Controller. Primero continuar la optimización de Endpoint Configurator; mientras tanto, todo procedimiento repetitivo útil debe tender a convertirse en script seguro, versionado e idempotente.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Replanificación J129 v0.2.x Sprint 1

Objetivo recibido: corregir la planificación porque el Sprint 1 ya tenía como requisito principal discovery inter-VLAN y además incorporar las capacidades avanzadas recientemente enumeradas para el J129.

Se actualizó `docs/j129-v0.2.0-sprint-1.md` para dejar como prioridades explícitas:

```text
discovery/importación inter-VLAN IP+MAC
idempotencia y colisiones IP/MAC
capabilities por modelo
idioma/locale
Web UI enable/disable
softkeys/menú
conferencia tripartita
presencia/BLF con Asterisk
SIP TLS/certificados
background/branding
Auto Answer/3PCC
codecs/DTMF/QoS
```

También se actualizó `AGENTS.md` para que cualquier agente futuro conozca estas prioridades, no intente resolver discovery dentro de `Avaya.py`, y reutilice una arquitectura de capabilities/plantillas para nuevos modelos Avaya y fabricantes futuros.

`CONTEXT.md` quedó alineado con esa secuencia y mantiene `release/j129-v0.1.0` congelada.

Archivos modificados en esta replanificación:

```text
docs/j129-v0.2.0-sprint-1.md
AGENTS.md
CONTEXT.md
docs/agent-log.md
```

El registro de pruebas ya contenía Test 47 cerrado y Test 48 reservado, por lo que no fue necesario cambiar su semántica.

Estado final:

```text
v0.1.0: congelada
v0.2.x Sprint 1: alcance ampliado y documentado
Test 48: reservado / NOT-TESTED
siguiente actividad acordada: prueba de llamada en LAB
```
