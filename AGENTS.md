# AGENTS.md — Avaya Asterisk / Issabel Endpoint Configurator

> Instrucciones obligatorias para humanos y agentes de IA. Leer completo antes de modificar código, workflows, helpers, documentación o release.

## Objetivo

Integrar Avaya J129 al Endpoint Configurator estándar de Issabel 5 sin UI paralela para credenciales SIP y sin modificar el core de Issabel.

Flujo esperado:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Ramas

- `main`: referencia y workflow definitions visibles en GitHub Actions. No usar para pruebas mutantes LAB.
- `Audit`: trabajo, auditoría, harness, helpers, documentación y validaciones.
- `release/j129-v0.1.0`: distribución limpia y congelada de v0.1.0.
- No hacer merge completo de `Audit` a `main` ni a release.
- Todo workflow mutante LAB debe abortar si `GITHUB_REF_NAME != Audit`.

## Arquitectura obligatoria

El vendor Avaya consume `_accounts` entregadas por Issabel. No reconsultar secretos SIP desde DB.

No modificar salvo evidencia extraordinaria:

```text
/usr/bin/issabel-endpointconfig
BaseEndpoint.py
Extension.py
EndpointManager_Standard.class.php
```

Overlay validado:

```text
deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
```

Release autocontenida:

```text
release/j129-v0.1.0/payload/
```

## Seguridad

Nunca almacenar ni imprimir secretos SIP reales, contraseña Web Admin, cookies, XToken, nonce, hashes de autenticación, tokens, claves privadas o credenciales de DB.

- `J129_WEB_PASSWORD` solo como GitHub Repository Secret.
- No ampliar sudo del runner.
- No subir Phone Reports brutos.
- No ejecutar jobs LAB sobre producción.
- No usar selectores genéricos `runs-on: self-hosted` o `[self-hosted, Linux, X64]` para LAB.

Selectores obligatorios:

```yaml
# LAB
runs-on: [self-hosted, Linux, X64, issabel-lab]

# Producción
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

El repositorio es público: cualquier workflow que pueda caer en un runner de producción se trata como riesgo crítico.

## J129 v1

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

Multicuenta queda fuera de v0.1.0.

## Estado de release y producción — 2026-09-02

Release exacta congelada:

```text
74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Producción:

```text
Host: cei-pbx02
PBX: 10.3.40.2
Runner: cei-pbx02-j129-production
Usuario runner: github-runner-prod
```

Validación automática de producción completada:

```text
15 / audit                PASS
15 / preflight            PASS
15 / verify               PASS
15 / install-idempotency  PASS
```

Runs de cierre:

```text
audit:               33692817597
preflight:           33694718272
verify:              33695299816
install-idempotency: 33695636455
```

La validación server-side no equivale a `PHYSICAL-J129-PASS`. Aún se requiere prueba física controlada del teléfono en producción.

## Discovery inter-VLAN

Limitación confirmada del scanner stock de Issabel: `detect_endpoints` usa `nmap -sP` y solo procesa hosts cuando nmap entrega `MAC Address:`. En otra VLAN/ruta L3 el PBX ve el host pero no la MAC.

No modificar core para resolverlo en v0.1.0. Sprint 1 de v0.2.0 documentado en `docs/j129-v0.2.0-sprint-1.md`.

## Numeración obligatoria de pruebas

Fuente autoritativa: `docs/j129-test-registry.md`.

Todo workflow que sea prueba, auditoría, probe, smoke, preflight, deploy controlado o validación debe tener identificador registrado y nombre visible con este formato:

```text
NN | Entorno | Componente | Propósito
```

Ejemplos:

```text
07 | Issabel Lab | J129 Rescan | Idempotency Audit
13 | Issabel Lab | J129 Release Package | Smoke Test
15 | J129 Production | v0.1.0 Server Validation
```

Reglas:

1. No crear pruebas sin número.
2. No reutilizar un número para otra semántica.
3. No renumerar 07–15: ya tienen evidencia histórica y runs asociados.
4. Si una prueba es auxiliar, recibe igualmente un número propio en el registro.
5. Antes de crear un workflow nuevo, reservar el siguiente ID en `docs/j129-test-registry.md`.
6. El nombre del workflow y el registro deben quedar sincronizados.
7. Cambiar solo el `name:` visible no altera el significado histórico del archivo; documentar el cambio.

## Protocolo obligatorio para cualquier agente de IA

Ningún agente puede considerar su trabajo terminado si deja el repositorio sin handoff actualizado.

### Al comenzar

Leer en este orden:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `docs/j129-test-registry.md`
4. `docs/j129-lab-validation.md`
5. `docs/j129-research-notes.md`
6. `docs/agent-log.md`
7. README de release cuando aplique
8. commits/runs recientes de la rama que se vaya a modificar

### Durante el trabajo

- No asumir que documentación vieja sigue vigente: verificar contra código, workflows y runs.
- No borrar contexto histórico útil; marcarlo como superseded/closed cuando corresponda.
- Registrar IDs de runs, commits, hashes de release y decisiones que cambien el estado del proyecto.
- Si aparece un bloqueo, documentar causa, alcance y siguiente paso; no llamarlo fallo de release si es infraestructura.

### Antes de terminar — obligatorio

Actualizar como mínimo:

1. `CONTEXT.md`: estado operativo actual, decisiones, bloqueos y próximo paso.
2. `docs/agent-log.md`: qué hizo el agente, archivos modificados, pruebas ejecutadas, resultado y commits/runs.
3. `docs/j129-test-registry.md`: si creó, renombró, retiró o cambió una prueba/workflow.
4. `AGENTS.md`: solo si cambió una regla de arquitectura, seguridad, proceso o gobernanza.

El agente debe dejar una entrada de handoff con:

```text
fecha
agente/modelo si se conoce
objetivo recibido
cambios realizados
archivos tocados
pruebas/runs y resultado
riesgos o deuda
estado final
siguiente paso exacto
```

No escribir secretos en el log.

### Regla de continuidad

Si un agente encuentra `CONTEXT.md` o `docs/agent-log.md` desactualizados respecto al código/runs, debe corregirlos en el mismo trabajo antes de continuar con cambios no urgentes.

## Estados de evidencia

Usar únicamente etiquetas claras:

```text
STATIC-PASS
LAB-READ-PASS
LAB-INTEGRATION-PASS
LAB-FIX-PASS
PHYSICAL-J129-PASS
INFRA-BLOCKED
RELEASE-PASS
PRODUCTION-SERVER-PASS
PRODUCTION-PHYSICAL-PASS
NOT-TESTED
```

No afirmar `PHYSICAL-J129-PASS` o `PRODUCTION-PHYSICAL-PASS` con evidencia únicamente server-side.

## Bugs / deuda abierta

- `BUG-EC-001`: GUI `Registered at` puede quedar obsoleta; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta no soportada en v1.
- `BUG-J129-004`: identidad SIP puede persistir localmente al retirar provisioning.
- Discovery inter-VLAN stock requiere MAC L2 visible.
- Menú local e idioma español fuera de v0.1.0.
- Reducir hardcodes/helpers históricos después del cierre físico de producción.
- Mantener separación estricta LAB/producción en self-hosted runners.

## Próximo paso

1. Terminar normalización de nombres/selectores de workflows según `docs/j129-test-registry.md`.
2. Confirmar que ningún workflow LAB puede seleccionar el runner de producción.
3. Ejecutar prueba física controlada de un J129 localizable en producción.
4. Validar discovery -> account -> Apply -> HTTP provisioning -> SIP -> llamadas.
5. Documentar cada resultado antes de iniciar el siguiente cambio funcional.
