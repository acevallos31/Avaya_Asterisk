# J129 Test Registry

Registro autoritativo de pruebas, auditorías, probes y validaciones del proyecto Avaya J129 / Issabel.

## Formato obligatorio

Toda prueba debe usar identificación:

```text
NN | Entorno | Componente | Propósito
```

No crear pruebas sin número. No reutilizar números. Los IDs 07–15 quedan congelados por evidencia histórica.

## Registro

| ID | Workflow / tipo | Nombre normalizado | Estado / función |
|---:|---|---|---|
| 00 | `audit-tests.yml` | `00 | Repository | Audit Harness | Static Checks` | Auditoría general del repositorio |
| 01 | `lab-readonly.yml` | `01 | Issabel Lab | Baseline | Read-Only Inventory` | Inventario base LAB |
| 02 | `lab-endpoint-db-audit.yml` | `02 | Issabel Lab | Endpoint DB | Audit` | Auditoría DB Endpoint Configurator |
| 03 | `lab-j129-discovery-audit.yml` | `03 | Issabel Lab | J129 Discovery | Audit` | Discovery/model/OUI |
| 04 | `lab-j129-provisioning-audit.yml` | `04 | Issabel Lab | J129 Provisioning | Audit` | Provisioning global/per-MAC |
| 05 | `lab-j129-sip-registration-audit.yml` | `05 | Issabel Lab | J129 SIP Registration | Audit` | Registro SIP |
| 06 | `lab-j129-apply-config.yml` | `06 | Issabel Lab | J129 Apply Config | Controlled Test` | Apply estándar controlado |
| 07 | `lab-j129-rescan-idempotency-audit.yml` | `07 | Issabel Lab | J129 Rescan | Idempotency Audit` | PASS histórico |
| 08 | `lab-j129-single-account-v1.yml` | `08 | Issabel Lab | J129 Single Account V1 | Apply & Audit` | PASS histórico |
| 09 | `lab-j129-remote-provisioning-reload-audit.yml` | `09 | Issabel Lab | J129 Remote Provisioning | Physical Lifecycle` | PASS físico histórico |
| 10 | `lab-j129-forced-provisioning-audit.yml` | `10 | Issabel Lab | J129 Forced Provisioning | NTP Audit` | PASS server-side + consumo físico posterior |
| 11 | `lab-j129-phone-ux-admin-audit.yml` | `11 | Issabel Lab | J129 Phone UX & Admin | Audit` | UX/admin, menú no resuelto |
| 12 | `lab-j129-production-patch.yml` | `12 | Issabel Lab | J129 Production Patch | Install & Rollback Test` | PASS |
| 13 | `lab-j129-release-package-smoke.yml` | `13 | Issabel Lab | J129 Release Package | Smoke Test` | PASS, release exacta |
| 14 | `lab-j129-release-freeze-manifest.yml` | `14 | Issabel Lab | J129 Release | Freeze Manifest` | PASS, freeze/checksums |
| 15 | `prod-j129-v010-server-validation.yml` | `15 | J129 Production | v0.1.0 Server Validation` | PASS audit/preflight/verify/idempotency |
| 16 | `lab-j129-dryrun.yml` | `16 | Issabel Lab | J129 | Dry Run` | Diagnóstico histórico |
| 17 | `lab-j129-boot-audit.yml` | `17 | Issabel Lab | J129 Boot | Audit` | Diagnóstico boot |
| 18 | `lab-j129-boot-audit-v2.yml` | `18 | Issabel Lab | J129 Boot V2 | Audit` | Diagnóstico boot v2 |
| 19 | `lab-j129-db-deploy.yml` | `19 | Issabel Lab | J129 DB | Controlled Deploy` | Cambio DB controlado |
| 20 | `lab-j129-http-root.yml` | `20 | Issabel Lab | J129 HTTP Root | Controlled Test` | Provisioning HTTP root |
| 21 | `lab-j129-helper-update.yml` | `21 | Issabel Lab | J129 Helper | Controlled Update` | Mantenimiento helper LAB |
| 22 | `lab-j129-core-flow-audit.yml` | `22 | Issabel Lab | J129 Core Apply Flow | Audit` | Auditoría flujo core |
| 23 | `lab-j129-web-audit.yml` | `23 | Issabel Lab | J129 Web | Audit` | Diagnóstico Web Admin |
| 24 | `lab-j129-web-login-audit.yml` | `24 | Issabel Lab | J129 Web Login | Audit` | Diagnóstico login web |
| 25 | `lab-j129-web-routes-audit.yml` | `25 | Issabel Lab | J129 Web Routes | Audit` | Rutas web |
| 26 | `lab-j129-web-mainjs-audit.yml` | `26 | Issabel Lab | J129 Web MainJS | Audit` | main.js público |
| 27 | `lab-j129-http-request-audit.yml` | `27 | Issabel Lab | J129 HTTP Request | Audit` | Request HTTP |
| 28 | `lab-j129-helper-contract-audit.yml` | `28 | Issabel Lab | J129 Helper Contract | Audit` | Contrato helper |
| 29 | `lab-j129-web-control-map-audit.yml` | `29 | Issabel Lab | J129 Web Control Map | Audit` | Mapa de controles web |
| 30 | `lab-j129-current-settings-audit.yml` | `30 | Issabel Lab | J129 Current Settings | Audit` | Settings actuales |
| 31 | `lab-j129-web-hashed-login-probe.yml` | `31 | Issabel Lab | J129 Web Hashed Login | Probe` | Probe autenticación hash |
| 32 | `lab-endpoint-remove-flow-audit.yml` | `32 | Issabel Lab | Endpoint Remove Flow | Audit` | Remoción endpoint |
| 33 | `lab-j129-web-default-login-probe.yml` | `33 | Issabel Lab | J129 Web Default Login | Probe` | Probe login default |
| 34 | `lab-j129-web-login-contract-audit.yml` | `34 | Issabel Lab | J129 Web Login Contract | Audit` | Contrato login |
| 35 | `lab-j129-deploy.yml` | `35 | Issabel Lab | J129 | Controlled Deploy` | Deploy LAB histórico |
| 36 | `lab-j129-notify-bootstrap-preflight.yml` | `36 | Issabel Lab | J129 SIP Notify Bootstrap | Preflight` | Preflight notify |
| 37 | `lab-j129-web-session-validity-probe.yml` | `37 | Issabel Lab | J129 Web Session Validity | Probe` | Validez sesión |
| 38 | `lab-j129-web-session-response-audit.yml` | `38 | Issabel Lab | J129 Web Session Response | Audit` | Respuesta sesión |
| 39 | `lab-j129-sip-notify-capability-audit.yml` | `39 | Issabel Lab | J129 SIP Notify Capability | Audit` | Capacidad NOTIFY |
| 40 | `lab-j129-web-session-bootstrap-audit.yml` | `40 | Issabel Lab | J129 Web Session Bootstrap | Audit` | Bootstrap sesión |
| 41 | `lab-j129-controlled-check-sync.yml` | `41 | Issabel Lab | J129 Check-Sync | Controlled Test` | check-sync controlado |
| 42 | `lab-j129-web-hashed-login-response-audit.yml` | `42 | Issabel Lab | J129 Web Hashed Login Response | Audit` | Respuesta hash login |
| 43 | `lab-j129-state-audit.yml` | `43 | Issabel Lab | J129 State | Audit` | Estado integral |
| 44 | `lab-j129-web-fingerprint-audit.yml` | `44 | Issabel Lab | J129 Web Fingerprint | Audit` | Fingerprint web |
| 45 | `manual-production-physical` | `45 | Production | J129 Physical Validation | Registration & Operation` | `PRODUCTION-PHYSICAL-PASS`: J129 registró y operador confirmó funcionamiento correcto |
| 46 | `prod-j129-v010-end-to-end-audit.yml` | `46 | J129 Production | v0.1.0 End-to-End | Read-Only Audit` | `PRODUCTION-END-TO-END-SERVER-AUDIT-PASS`, run 33702529808; release/DB/provisioning/Apache/HTTP/per-MAC PASS |
| 47 | `prod-j129-physical-call-e2e.yml` | `47 | J129 Production | Physical Call | Controlled E2E` | CERRADA para v0.1.0. Preflight PASS run 33710642058. Llamada automatizada PASS run 33711068591: peer 4455 READY, J129 `10.3.40.32` respondió `100 Trying` y `180 Ringing`, User-Agent/MAC confirmados, cleanup PASS. `answer/audio` físico no probado por ausencia de operador junto al teléfono; no se afirma nuevo `PRODUCTION-PHYSICAL-PASS` a partir de este run. |
| 48 | `planned-v020-lab-remote-originated-call` | `48 | Issabel Lab | J129 Remote-Originated Call | 3PCC/Control Probe` | RESERVADA para v0.2.0. Investigar en LAB si el J129 puede originar/controlar remotamente una llamada real hacia otra extensión y distinguirla de una llamada originada por Asterisk. Repetir primero en LAB; producción solo después de evidencia y control de riesgos. `NOT-TESTED`. |

## Reglas de runners

LAB:

```yaml
runs-on: [self-hosted, Linux, X64, issabel-lab]
```

Producción:

```yaml
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

No se permite un workflow LAB con selector genérico que también pueda ser satisfecho por el runner de producción.

## Alta de una prueba nueva

1. Revisar este registro.
2. Reservar el siguiente ID disponible.
3. Si es workflow, crear/renombrar usando el formato normalizado.
4. Si es prueba manual/física, registrar explícitamente el tipo y la evidencia disponible.
5. Verificar selector de runner y trigger cuando aplique.
6. Ejecutar la prueba.
7. Registrar run/resultado/evidencia en `docs/agent-log.md` y `CONTEXT.md` si cambia el estado del proyecto.

## Estado de normalización

La numeración de 07–15 tiene evidencia histórica. Los IDs restantes formalizan workflows históricos/auxiliares y validaciones de producción. La normalización de los `name:` visibles y selectores de runner debe seguir este registro sin cambiar la semántica de las pruebas.

Próximo ID disponible: `49`.
