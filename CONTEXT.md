# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo vigente para retomar el proyecto sin reconstruir la historia. No contiene secretos reales.

## Objetivo actual

La release `v0.1.0` ya está instalada y validada server-side, físicamente y mediante auditoría post-implementación read-only en producción. El J129 registró y el operador confirmó funcionamiento correcto.

Arquitectura objetivo:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Release congelada

```text
rama: release/j129-v0.1.0
commit: 74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
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

Workflow 15:

```text
audit                PASS  run 33692817597
preflight            PASS  run 33694718272
verify               PASS  run 33695299816
install-idempotency  PASS  run 33695636455
```

Prueba física manual:

```text
45 | Production | J129 Physical Validation | Registration & Operation
PRODUCTION-PHYSICAL-PASS
```

## Auditoría post-implementación — Test 46

```text
46 | J129 Production | v0.1.0 End-to-End | Read-Only Audit
run: 33702529808
resultado: PRODUCTION-END-TO-END-SERVER-AUDIT-PASS
```

Validó paquete congelado, DB, Apache, provisioning global, HTTP, verify oficial y provisioning per-MAC para `C8:1F:EA:C3:D6:B2`.

## E2E físico — Test 47

Workflow:

```text
.github/workflows/prod-j129-physical-call-e2e.yml
47 | J129 Production | Physical Call | Controlled E2E
```

Primer preflight:

```text
run: 33703875115
resultado: INFRA-BLOCKED
causa: github-runner-prod no puede abrir /var/run/asterisk/asterisk.ctl
```

El guard de producción pasó y no se originó ninguna llamada. El runner no tendrá `sudo asterisk` genérico.

Se preparó un helper privilegiado mínimo y root-owned:

```text
deploy/j129/avaya-j129-prod-call-test
deploy/j129/avaya-j129-prod-call-test.sudoers
instalación destino: /usr/local/sbin/avaya-j129-prod-call-test
```

El helper solo admite `preflight`, `peer EXT`, `call EXT [IP]` y `cleanup`; valida caller, host, extensión e IP. Durante `call` eleva verbose a 10, habilita SIP debug del peer y RTP debug por IP opcional, origina `SIP/<ext> -> Playback hello-world`, captura evidencia sanitizada y restaura SIP/RTP debug + verbose 3 aun ante fallo.

El workflow 47 fue actualizado en `Audit` y `main` para invocar exclusivamente ese helper mediante sudo. No puede desplegarse desde el runner actual porque eso requeriría privilegios que deliberadamente no tiene. La instalación del helper y su sudoers requiere una intervención root única cuando haya acceso administrativo a `cei-pbx02`.

## Seguridad de runners

```yaml
# LAB
runs-on: [self-hosted, Linux, X64, issabel-lab]

# Producción
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

No se permite `sudo asterisk` ni shell root genérico. Las excepciones privilegiadas de producción deben ser helpers root-owned, allowlisted y con validación estricta de caller/host/argumentos.

## Discovery inter-VLAN — limitación confirmada

El scanner stock `/usr/share/issabel/privileged/detect_endpoints` solo procesa endpoints cuando nmap entrega `MAC Address:`. En misma VLAN/L2 discovery funciona; inter-VLAN/L3 responde host pero no hay MAC L2. No es fallo v0.1.0. Sprint 1 de v0.2.0: `docs/j129-v0.2.0-sprint-1.md`.

## Numeración

Fuente autoritativa: `docs/j129-test-registry.md`.

```text
00–44 pruebas históricas/workflows
45 validación física de producción — PASS
46 auditoría post-implementación read-only — PASS run 33702529808
47 llamada física controlada E2E — INFRA-BLOCKED hasta instalar helper mínimo
```

Próximo ID disponible: `48`.

## Próxima secuencia

```text
1. con acceso root a cei-pbx02, instalar avaya-j129-prod-call-test como root:root 0755
2. instalar sudoers mínimo como root:root 0440 y validar con visudo -cf
3. reejecutar workflow 47 branch=Audit mode=preflight confirm=PREFLIGHT-PROD-J129-CALL
4. si preflight PASS, ejecutar mode=call cuando haya alguien junto al J129
5. confirmar físicamente ring/answer/audio y revisar artifact sanitizado
6. terminar normalización de workflows/runners
```
