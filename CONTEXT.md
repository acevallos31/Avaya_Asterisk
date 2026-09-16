# CONTEXT.md — Estado consolidado Avaya Asterisk / Issabel 5

Actualizado: 2026-09-16. Este archivo resume el estado operativo vigente para
retomar el proyecto sin reconstruir la historia. No contiene secretos reales.
La historia detallada permanece en `docs/agent-log.md`,
`docs/j129-test-registry.md` y los documentos específicos de cada bloque.

## Prioridad actual — Endpoint Configurator

La prioridad inmediata es promover a producción la fundación de credenciales
administrativas y el resumen visible `Extension / Registration`, ya validados en
LAB. La release J129 `v0.1.0` permanece congelada y no debe modificarse para
hacer este rollout.

Secuencia vigente:

```text
LAB schema/runtime/visual PASS
-> Test 70 Ceiba read-only PASS
-> Test 71 controlled install STAGED / NOT-TESTED
-> bootstrap único del helper + grants DDL mínimos
-> ejecutar Test 71
-> validación visual productiva
-> canario real de credencial en una fase posterior separada
```

## Producción

```text
Host:       cei-pbx02
PBX:        10.3.40.2
OS:         Rocky Linux 8.10
Asterisk:   18.19
Runner:     cei-pbx02-j129-production
Usuario:    github-runner-prod
Labels:     self-hosted, Linux, X64, j129-production, cei-pbx02
```

Reglas permanentes:

- no usar selector genérico `self-hosted` para producción;
- no conceder `sudo asterisk`, shell root ni comandos genéricos;
- cualquier operación privilegiada debe pasar por helper root-owned,
  allowlisted y con caller/host/argumentos exactos;
- el runner productivo no puede autoactualizar helpers privilegiados desde el
  workspace público;
- no publicar secretos, passwords, tokens ni contenido de claves en logs.

## Release J129 v0.1.0 congelada

```text
rama:   release/j129-v0.1.0
commit: 74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Evidencia productiva previa:

```text
15  server validation                  PASS
45  physical registration/operation    PRODUCTION-PHYSICAL-PASS
46  read-only E2E                      run 33702529808 PASS
47  controlled signalling              run 33711068591 PASS
```

La señalización Asterisk -> J129 quedó comprobada; la prueba física histórica
confirma operación real. El helper existente
`/usr/local/sbin/avaya-j129-prod-validation` se mantiene congelado para la
release J129 y se reutiliza solo en sus acciones allowlisted, incluido
`fleet-audit`.

## Endpoint Configurator — credenciales administrativas

La rama `feature/endpoint-credential-foundation` contiene:

- esquema versionado para política global, credencial por endpoint/MAC y eventos;
- bóveda PHP AES-256-GCM;
- clave externa `/etc/issabel/endpoint-configurator.key`;
- contraseña administrativa global por PBX;
- override opcional por MAC;
- credencial inicial `FACTORY` por MAC;
- importación CSV `mac_address,password` acotada y transaccional;
- CSRF en operaciones de escritura de la UI;
- CLI interno que recibe secretos por stdin y nunca los imprime;
- diálogo `summary` read-only;
- columna `Extension / Registration` en la tabla principal;
- soporte visible para varias cuentas por endpoint;
- Asterisk como fuente autoritativa del estado de registro.

Guardar políticas/overrides crea estado `PENDING`; esta fundación no cambia por
sí sola la contraseña del teléfono y no ejecuta `Configure`.

## LAB — estado validado

### Test 67

```text
67 | Issabel Lab | Endpoint Credentials | Foundation
run 34681386727
LAB-SCHEMA-CYCLE-PASS
```

Creó, verificó y revirtió las tres tablas. Se adoptó después un modelo de DDL de
mínimo privilegio permanente para evitar grant/revoke en cada despliegue:
`CREATE, ALTER, INDEX, REFERENCES` únicamente sobre las tres tablas de
credenciales y `REFERENCES` sobre la tabla padre `endpoint`; sin `DROP`, sin
`ALL PRIVILEGES` y sin DDL general sobre la base.

### Test 68

```text
68 | Issabel Lab | Endpoint Credentials | Runtime Smoke
run 34805839845
LAB-RUNTIME-SMOKE-PASS
```

Validó esquema, clave, Vault, CLI, lint PHP y smoke autenticado read-only del
GRP2601P. La credencial FACTORY se transportó por stdin, se cifró en reposo y se
descifró solo en memoria. Marcador: `phone_write=NO`.

Validación visual del operador en LAB:

```text
GXP1630   192.168.1.169   extensión 201   Registered
GXP1625   192.168.1.168   extensión 202   Registered
J129      192.168.1.170   extensión 200   Registered
GRP2601P  192.168.1.176   extensión 203   Registered
```

### Test 69

```text
69 | Issabel Lab | PBX Web Interface | Diagnosis
run 34769273874
LAB-FIX-PASS
```

El HTTP 500 del LAB se atribuyó a permisos de recorrido del directorio
`modules/endpoint_configurator/libs` para PHP-FPM `asterisk`. Se corrigió a
`root:root:0755`; Test 68 posterior `34769381087` confirmó runtime/clave/web.

## Test 70 — Ceiba production preflight

```text
70 | Ceiba Production | Endpoint Credentials | Read-Only Preflight
run: 35123613203
resultado: PRODUCTION-SERVER-PASS
```

Marcadores confirmados:

```text
TEST70-PROD-RUNNER-GUARD-PASS
TEST70-HARNESS-INTEGRITY-PASS
TEST70-PROD-ENDPOINT-BASELINE-PASS
J129-PROD-FLEET-AUDIT-PASS
TEST70-PROD-WEB-HEALTH-PASS
TEST70-PROD-ENDPOINT-CREDENTIAL-PREFLIGHT=PASS
production_runtime_write=NO
endpointconfig_write=NO
phone_write=NO
```

HTTPS local respondió `200`. El inventario previo confirmó que la clave,
`EndpointCredentialVault`, diálogo `summary` y CLI productiva todavía estaban
ausentes.

Baselines productivos aprobados:

```text
index.php              60bb6aaa461e72979cfd40551b9ef78e81c75656
reporte_endpoints.tpl  d979762079d4dcc2874759881104b3287fea71c2
javascript.js          44bea8adac8bd15d9b8548922d032fcf924edfc1
```

El `index.php` de Ceiba difería de Audit únicamente en la forma de cargar
librerías; el diff se revisó antes de aceptar ese blob exacto. No se relajó el
gate con wildcard.

Flota observada por `fleet-audit` en el run PASS: 19 J129, 14 configurados, 12
registrados, 2 provisionados/no registrados y 5 `DETECTED_ONLY`. Es inventario
read-only.

## Test 71 — instalación controlada STAGED

```text
71 | Ceiba Production | Endpoint Credentials | Controlled Runtime Install
estado: STAGED / NOT-TESTED
workflow: .github/workflows/prod-endpoint-credential-test71.yml
main commit: 7aba3f2ed5a78cf8d0433283d592ec20043b5acf
candidate: ef176c99935af5f833248358c4daf7b4ca0dde6a
helper blob: 3c16593a0f2490e00ad912838ec32eed2b35e26a
```

Helper dedicado preparado:

```text
repo: deploy/endpoint-configurator/bin/endpoint-credential-prod-deploy
prod: /usr/local/sbin/issabel-endpoint-credential-prod
owner/mode esperado: root:root:0755
```

Sudoers preparado:

```text
repo: deploy/endpoint-configurator/sudoers/issabel-endpoint-credential-prod
prod: /etc/sudoers.d/issabel-endpoint-credential-prod
owner/mode esperado: root:root:0440
```

El helper acepta únicamente el root exacto del checkout Test71, valida todos los
artefactos por Git blob SHA, rechaza symlinks y propietario inesperado, y tiene
acciones exactas `preflight`, `install`, `verify` y `rollback-runtime`.

Antes de crear tablas ejecuta `SHOW GRANTS FOR CURRENT_USER` y exige los grants
DDL limitados definidos para este módulo. El marcador de seguridad esperado es:

```text
TEST71-LIMITED-DDL-GRANTS-PASS
```

El install:

- vuelve a validar los blobs productivos de Test70 antes de escribir;
- acepta únicamente esquema `0/3` o `3/3`; esquema parcial bloquea;
- crea/preserva la key `root:asterisk:0640` sin cambiar owner/mode de
  `/etc/issabel` si ese directorio ya existe;
- no cambia owner/mode de `/usr/local/libexec` si ya existe;
- crea manifest y backup root-only antes de reemplazar runtime;
- instala Vault, CLI, `index.php`, diálogo `summary`, template y JavaScript;
- ejecuta lint PHP, `apachectl -t`, reload, verificación byte a byte, esquema,
  HTTPS y `fleet-audit`;
- no contacta teléfonos: `phone_write=NO`.

Rollback: solo runtime. Las tablas y la clave se conservan. No se ejecuta
`DROP TABLE`, factory reset, cambio de contraseña ni `Configure`.

### Bootstrap único pendiente

Antes del primer run Test71 hay que ejecutar una sola vez el procedimiento
`docs/endpoint-configurator-prod-helper-bootstrap.md` en `cei-pbx02`. Instala el
helper + sudoers root-owned y configura los grants DDL permanentes de mínimo
privilegio para `asteriskuser@localhost`.

El bootstrap no crea las tres tablas, no instala el runtime y no contacta
telefonos. Sí modifica una sola vez la metadata de privilegios MariaDB; no se
concede `DROP`, `ALL PRIVILEGES`, `CREATE USER` ni DDL general sobre
`endpointconfig.*`.

Después se ejecutará Test71 desde `main` con confirmación exacta:

```text
INSTALL-ENDPOINT-CREDENTIALS-PROD
```

A la fecha de este contexto, **Test71 no ha sido ejecutado y la preparación no
ha escrito el nuevo runtime en producción**.

## Grandstream — estado relevante

- GXP1625: `LAB-INTEGRATION-PASS` + validación física satisfactoria; Test55.
- GXP1630: ciclo server-side completo en LAB; bootstrap/model/configure/E2E PASS.
- GRP2601P `EC:74:D7:1E:E8:E3`: Tests62–66 completos; Test66 run
  `34677554254` `LAB-INTEGRATION-PASS` y validación física positiva como ext 203.
- La autenticación GRP2601P usa challenge nonce/SHA-256 y
  `PUT /cgi-bin/config_update`; la credencial de etiqueta se modela como
  `FACTORY`, separada de la contraseña administrativa final.

Producción Grandstream sigue separada de este rollout; Test71 no aprovisiona ni
escribe teléfonos.

## J129 v0.2.x / arquitectura futura

Documento de planificación:

```text
docs/j129-v0.2.0-sprint-1.md
```

Prioridades: discovery inter-VLAN IP+MAC, idempotencia/colisiones, capabilities,
idioma/locale, Web UI enable/disable, softkeys, conferencia, BLF/presencia,
TLS/certificados, branding, Auto Answer/3PCC y codecs/DTMF/QoS.

El scanner stock depende de MAC L2; inter-VLAN requiere una fuente
complementaria confiable (ARP/DHCP/router/inventario) y no debe resolverse
metiendo discovery en `Avaya.py`.

## Numeración

Fuente autoritativa:

```text
docs/j129-test-registry.md
```

Test70 está cerrado PASS, Test71 está reservado y staged. Próximo ID disponible:
`72`.
