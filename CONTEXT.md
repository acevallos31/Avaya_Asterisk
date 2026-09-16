# CONTEXT.md — Estado consolidado Avaya Asterisk / Issabel 5

Actualizado: 2026-09-16. Este archivo resume el estado operativo vigente para
retomar el proyecto sin reconstruir la historia. No contiene secretos reales.
La historia detallada permanece en `docs/agent-log.md`,
`docs/j129-test-registry.md` y los documentos específicos de cada bloque.

## Prioridad actual — Endpoint Configurator

La fundación de credenciales administrativas y el resumen visible
`Extension / Registration` ya están instalados server-side en producción Ceiba.
La release J129 `v0.1.0` permanece congelada y separada de este rollout.

Secuencia vigente:

```text
LAB schema/runtime/visual PASS
-> Test 70 Ceiba read-only PASS
-> Test 71 Ceiba controlled install PASS
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

El helper existente `/usr/local/sbin/avaya-j129-prod-validation` se mantiene
congelado para la release J129 y se reutiliza solo en sus acciones allowlisted,
incluido `fleet-audit`.

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
mínimo privilegio permanente: `CREATE, ALTER, INDEX, REFERENCES` únicamente
sobre las tres tablas de credenciales y `REFERENCES` sobre `endpoint`; sin
`DROP`, sin `ALL PRIVILEGES` y sin DDL general sobre la base.

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

Baselines productivos aprobados antes del install:

```text
index.php              60bb6aaa461e72979cfd40551b9ef78e81c75656
reporte_endpoints.tpl  d979762079d4dcc2874759881104b3287fea71c2
javascript.js          44bea8adac8bd15d9b8548922d032fcf924edfc1
```

HTTPS local respondió `200`. El inventario previo confirmó que la clave, Vault,
diálogo `summary` y CLI productiva todavía estaban ausentes. La flota observada
fue 19 J129: 14 configurados, 12 registrados, 2 provisionados/no registrados y
5 `DETECTED_ONLY`.

## Test 71 — instalación controlada PASS

```text
71 | Ceiba Production | Endpoint Credentials | Controlled Runtime Install
run: 35138230754
resultado: PRODUCTION-SERVER-PASS
workflow head: c2946b390ae2f68529dff20fced9708765c5a44a
candidate: ef176c99935af5f833248358c4daf7b4ca0dde6a
helper blob: 3c16593a0f2490e00ad912838ec32eed2b35e26a
```

Runs previos:

```text
35130705534  FAIL antes de preflight; guard del helper no determinista
35131492883  FAIL antes de preflight; helper productivo aún ausente/no ejecutable
35138230754  PASS autoritativo
```

Los dos fallos previos no llegaron a `preflight`, `install` ni `verify`; no
escribieron producción.

El run autoritativo confirmó:

```text
TEST71-CANDIDATE-HELPER-INTEGRITY-PASS
TEST71-INSTALLED-HELPER-META=root:root:755
TEST71-INSTALLED-HELPER-INTEGRITY-PASS
TEST71-ROOT-HELPER-GUARD-PASS
TEST71-PAYLOAD-INTEGRITY-PASS
TEST71-WEB-HEALTH-PASS status=200
TEST71-LIMITED-DDL-GRANTS-PASS
TEST71-PREINSTALL-BASELINE-PASS
TEST71-BACKUP-MANIFEST-PASS
TEST71-SCHEMA-INSTALL-PASS
TEST71-SCHEMA-VERIFY-PASS
TEST71-KEY-INSTALL-PASS existing=NO
TEST71-PROD-ENDPOINT-CREDENTIAL-RUNTIME=PASS
TEST71-CONTROLLED-INSTALL-PASS
J129-PROD-FLEET-AUDIT-PASS
TEST71-PROD-CONTROLLED-INSTALL=PASS
phone_write=NO
```

Quedaron instalados server-side:

- las tres tablas de credenciales (`3/3` verificadas);
- la clave externa protegida `root:asterisk:0640`;
- `EndpointCredentialVault.class.php`;
- CLI productiva de bóveda;
- `index.php` del módulo candidato;
- diálogo `summary` y `en.lang`;
- `reporte_endpoints.tpl` y `javascript.js` del candidato.

Antes de reemplazar runtime se creó manifest/backup root-only. Apache pasó lint,
se recargó correctamente y HTTPS local permaneció `200`. El `fleet-audit`
posterior volvió a pasar con 19 J129, 14 configurados, 12 registrados, 2
provisionados/no registrados y 5 `DETECTED_ONLY`. Test71 no contactó ni
reconfiguró teléfonos: `phone_write=NO`.

Evidencia sanitizada:

```text
artifact: test71-endpoint-credential-prod-35138230754
artifact id: 10464202042
sha256(zip): 63d4c189ca23574520b2783f2c333722c9333769a7993eff18a44befffbdc0d6
retención: 90 días
```

Helper dedicado productivo:

```text
/usr/local/sbin/issabel-endpoint-credential-prod
root:root:0755
```

Sudoers:

```text
/etc/sudoers.d/issabel-endpoint-credential-prod
root:root:0440
```

Acciones allowlisted: `preflight`, `install`, `verify` y `rollback-runtime`.
Los grants DDL mínimos permanentes quedan limitados a las tres tablas del módulo
más `REFERENCES` sobre `endpoint`.

Rollback disponible: solo runtime. Las tablas y la clave se conservan. No se
ejecuta `DROP TABLE`, factory reset, cambio de contraseña ni `Configure`.

## Próximo paso

La instalación server-side está cerrada. Falta únicamente la validación visual
manual de Endpoint Configurator en producción. Después de esa validación, el
canario real de credencial administrativa debe ejecutarse como una fase separada
y sobre un solo endpoint seleccionado; no forma parte de Test71.

## Grandstream — estado relevante

- GXP1625: `LAB-INTEGRATION-PASS` + validación física satisfactoria; Test55.
- GXP1630: ciclo server-side completo en LAB; bootstrap/model/configure/E2E PASS.
- GRP2601P `EC:74:D7:1E:E8:E3`: Tests62–66 completos; Test66 run
  `34677554254` `LAB-INTEGRATION-PASS` y validación física positiva como ext 203.

Producción Grandstream sigue separada de este rollout; Test71 no aprovisionó ni
escribió teléfonos.

## J129 v0.2.x / arquitectura futura

Documento de planificación:

```text
docs/j129-v0.2.0-sprint-1.md
```

Prioridades: discovery inter-VLAN IP+MAC, idempotencia/colisiones, capabilities,
idioma/locale, Web UI enable/disable, softkeys, conferencia, BLF/presencia,
TLS/certificados, branding, Auto Answer/3PCC y codecs/DTMF/QoS.

## Numeración

Fuente autoritativa:

```text
docs/j129-test-registry.md
```

Test70 y Test71 están cerrados PASS. Próximo ID disponible: `72`.
