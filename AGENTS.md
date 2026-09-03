# AGENTS.md — Avaya Asterisk / Issabel Endpoint Configurator

> Instrucciones obligatorias para humanos y agentes de IA. Leer completo antes de modificar código, workflows, helpers, documentación o release.

## Objetivo

Integrar teléfonos Avaya al Endpoint Configurator estándar de Issabel 5 sin UI paralela para credenciales SIP y sin modificar innecesariamente el core de Issabel.

La primera implementación estable es Avaya J129 v0.1.0. La línea v0.2.x amplía discovery y capacidades configurables por modelo antes de incorporar otros modelos/fabricantes.

Flujo esperado:

```text
Discovery -> fabricante/modelo -> capabilities -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> vendor -> provisioning -> SIP
```

Para J129 v0.1.0:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Ramas

- `main`: referencia y workflow definitions visibles en GitHub Actions. No usar para pruebas mutantes LAB.
- `Audit`: trabajo, auditoría, harness, helpers, documentación y validaciones.
- `release/j129-v0.1.0`: distribución limpia y congelada de v0.1.0.
- Las ramas `feature/<fabricante>-<modelo>-<versión>` son temporales para nuevas líneas funcionales y deben integrarse después de validación; no mantener forks permanentes por modelo.
- No hacer merge completo de `Audit` a `main` ni a release.
- Todo workflow mutante LAB debe abortar si `GITHUB_REF_NAME != Audit` o la rama LAB autorizada correspondiente.

## Arquitectura obligatoria

El vendor Avaya consume `_accounts` entregadas por Issabel. No reconsultar secretos SIP desde DB.

No modificar salvo evidencia extraordinaria:

```text
/usr/bin/issabel-endpointconfig
BaseEndpoint.py
Extension.py
EndpointManager_Standard.class.php
```

Overlay validado J129 v0.1.0:

```text
deploy/j129/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
deploy/j129/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
```

Release autocontenida:

```text
release/j129-v0.1.0/payload/
```

### Regla para v0.2.x y modelos futuros

Las diferencias de modelo deben concentrarse en capabilities/plantillas y lógica vendor reutilizable. Evitar duplicar lógica común por cada teléfono.

El discovery inter-VLAN no se resuelve dentro de `Avaya.py`; debe ser una capacidad de inventario/discovery complementaria y reutilizable por otros fabricantes.

## Seguridad

Nunca almacenar ni imprimir secretos SIP reales, contraseña Web Admin, cookies, XToken, nonce, hashes de autenticación, tokens, claves privadas o credenciales de DB.

- `J129_WEB_PASSWORD` solo como GitHub Repository Secret.
- No ampliar sudo del runner de forma genérica.
- No subir Phone Reports brutos ni trazas SIP con secretos.
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

## J129 v0.1.0

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

Multicuenta queda fuera de v0.1.0 y no cambia hasta una release que lo declare explícitamente.

Release exacta congelada:

```text
74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Estado de producción:

```text
15 | server validation                    PASS
45 | physical registration/operation      PRODUCTION-PHYSICAL-PASS
46 | read-only end-to-end server audit    PASS
47 | controlled Asterisk -> J129 call     automated signalling PASS
```

En Test 47 se comprobó `100 Trying` y `180 Ringing`; answer/audio de ese run quedaron `NOT-TESTED` porque no había operador junto al teléfono. No reinterpretar esto como evidencia física adicional.

## J129 v0.2.x — prioridad

Fuente de planificación: `docs/j129-v0.2.0-sprint-1.md`.

Sprint 1 incluye obligatoriamente:

1. discovery/importación inter-VLAN mediante fuente confiable `IP + MAC`, sin reemplazar el discovery local stock;
2. idempotencia y manejo de colisiones IP/MAC;
3. diseño de capabilities por modelo;
4. comenzar opciones configurables J129, priorizando idioma/locale y habilitar/deshabilitar Web UI;
5. investigar/documentar softkeys/menú, conferencia tripartita, presencia/BLF, TLS/certificados, background/branding, 3PCC/Auto Answer, codecs/DTMF/QoS;
6. mantener scripts reutilizables fuera de workflows cuando sirvan para operación futura.

Test 48 está reservado para LAB:

```text
48 | Issabel Lab | J129 Remote-Originated Call | 3PCC/Control Probe
```

La prueba 48 se retomará después de cerrar la actualización documental y al volver al ambiente de laboratorio.

## Discovery inter-VLAN

Limitación confirmada del scanner stock de Issabel: `detect_endpoints` usa Nmap y solo procesa hosts cuando Nmap entrega `MAC Address:`. En otra VLAN/ruta L3 la PBX puede ver el host pero no su MAC L2.

No modificar core para resolverlo. El diseño de v0.2.x debe aceptar inicialmente `IP + MAC` confiables y permitir fuentes futuras como ARP/DHCP/router/API.

## Scripts operativos

`scripts/` es catálogo permanente para automatización de bootstrap, deploy, diagnóstico, mantenimiento, seguridad y testing. No limitarlo a pruebas.

Roadmap de gestión central de PBX:

```text
docs/pbx-fleet-control-roadmap.md
```

Ese proyecto queda después de optimizar Endpoint Configurator; los scripts reutilizables creados ahora deben favorecer esa evolución futura.

## Numeración obligatoria de pruebas

Fuente autoritativa: `docs/j129-test-registry.md`.

Todo workflow que sea prueba, auditoría, probe, smoke, preflight, deploy controlado o validación debe tener identificador registrado y nombre visible con este formato:

```text
NN | Entorno | Componente | Propósito
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
4. `docs/j129-v0.2.0-sprint-1.md` cuando el trabajo sea v0.2.x
5. `docs/j129-lab-validation.md`
6. `docs/j129-research-notes.md`
7. `docs/agent-log.md`
8. README de release cuando aplique
9. commits/runs recientes de la rama que se vaya a modificar

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

No escribir secretos en el log.

## Estados de evidencia

Usar etiquetas claras:

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

No afirmar evidencia física con resultados únicamente server-side.

## Bugs / deuda abierta

- `BUG-EC-001`: GUI `Registered at` puede quedar obsoleta; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta no soportada en v0.1.0.
- `BUG-J129-004`: identidad SIP puede persistir localmente al retirar provisioning.
- Discovery inter-VLAN stock requiere MAC L2 visible; Sprint 1 v0.2.x debe resolver importación complementaria.
- Idioma español/selección de locale pendiente.
- Softkeys y menú local pendientes.
- Toggle Web UI pendiente.
- Conferencia tripartita pendiente de investigación/validación.
- Presencia/BLF con Asterisk pendiente.
- TLS/certificados pendiente.
- Background/branding pendiente.
- 3PCC/Auto Answer pendiente; Test 48 reservado.
- Reducir hardcodes/helpers históricos y evolucionar a capabilities por modelo.
- Mantener separación estricta LAB/producción en self-hosted runners.

## Próximo paso

1. Mantener v0.1.0 congelada.
2. Preparar rama feature de J129 v0.2.x desde la línea de trabajo validada cuando se inicie implementación.
3. Implementar primero discovery inter-VLAN + base de capabilities según Sprint 1.
4. Continuar idioma/Web UI y luego el resto de capacidades avanzadas según evidencia.
5. Retomar Test 48 de llamada remota en LAB después de esta planificación/documentación.
6. Incorporar nuevos modelos Avaya mediante ramas feature temporales y luego otros fabricantes sin duplicar arquitectura.
