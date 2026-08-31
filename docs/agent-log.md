# Agent Audit Log

Registro compartido de trabajo realizado por humanos y agentes de IA en Avaya_Asterisk.

Este archivo complementa el historial de Git. No reemplaza commits ni Pull Requests: explica **intención, evidencia, decisiones y pendientes** para que otro agente pueda continuar sin reconstruir todo el contexto.

Consultar primero `AGENTS.md`.

---

## Reglas del registro

Cada agente debe agregar una entrada por unidad de trabajo significativa.

No borrar entradas anteriores. Si una conclusión cambia, agregar una nueva entrada que la sustituya y referenciar la anterior.

No almacenar secretos reales.

Estados permitidos para evidencia:

- `STATIC-PASS`
- `LAB-READ-PASS`
- `LAB-INTEGRATION-PASS`
- `PHYSICAL-J129-PASS`
- `PRODUCTION-REFERENCE`
- `NOT-TESTED`

### Plantilla

```markdown
## YYYY-MM-DD HH:MM TZ — <agent-id>

**Objetivo:**
<qué intentaba resolver>

**Rama:** `<branch>`

**Base revisada:**
- commit/ref: `<sha/ref>`
- upstream: `<si aplica>`

**Archivos leídos:**
- `...`

**Archivos modificados:**
- `...`

**Decisiones:**
- ...

**Pruebas/evidencia:**
- `<estado>` — `<comando/evidencia>`

**Riesgos / no comprobado:**
- ...

**Siguiente paso recomendado:**
- ...

**Commit(s):**
- `<sha> <mensaje>`
```

---

## 2026-08-31 12:51 -06:00 — OpenAI-GPT-5.6-Sol

**Objetivo:**
Consolidar el contexto técnico compartido del proyecto, establecer reglas para colaboración entre múltiples agentes/modelos y crear trazabilidad antes del refactor J129.

**Rama:** `Audit`

**Base revisada:**
- `main` como referencia histórica funcional.
- `Audit` como rama de auditoría y pruebas.
- upstream `IssabelFoundation/endpointconfig2` como referencia de código stock.

**Archivos leídos/revisados durante la auditoría previa:**
- `usr/bin/issabel-endpointconfig`
- `usr/share/issabel/endpoint-classes/class/issabel/BaseEndpoint.py`
- `usr/share/issabel/endpoint-classes/class/issabel/Extension.py`
- `usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py`
- `usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl`
- `usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl`
- `var/www/html/modules/endpoint_configurator/phonesrv/vendor/Avaya.class.php`
- archivos relevantes de `tftpboot/`
- tests existentes bajo `tests/audit/`

**Archivos modificados:**
- `AGENTS.md`
- `docs/agent-log.md`

**Decisiones:**
- El alcance inmediato queda limitado a Avaya J129.
- El comportamiento funcional de `main` se conservará mediante tests, pero su arquitectura no se copiará ciegamente.
- `BaseEndpoint.py` y `Extension.py` deben permanecer stock salvo evidencia extraordinaria.
- Se pretende restaurar `issabel-endpointconfig` al flujo stock eliminando la rama especial Avaya.
- `Avaya.Endpoint` debe consumir `self._accounts`/`Extension`, no consultar nuevamente MySQL para extension/secret/display name.
- La configuración J129 seguirá el patrón global -> `GET $MACADDR.txt` -> archivo por MAC.
- `/tftpboot` se mantiene como directorio lógico de provisioning; HTTP/HTTPS/TFTP son mecanismos de entrega separados.
- Se utilizará una PBX Issabel de laboratorio en Proxmox mediante GitHub Actions self-hosted runner para futuras pruebas de integración.
- Los workflows que puedan modificar la PBX deberán ser manuales (`workflow_dispatch`).

**Pruebas/evidencia:**
- `PRODUCTION-REFERENCE` — la rama `main` representa el comportamiento de una implementación J129 históricamente funcional, pero contiene deuda técnica.
- `STATIC-PASS` — se confirmó previamente que `BaseEndpoint.py` y `Extension.py` de la referencia coinciden con upstream.
- `STATIC-PASS` — suite de contratos de auditoría ya existe en `tests/audit/`; algunos contratos pueden estar intencionalmente rojos para dirigir el refactor.
- `NOT-TESTED` — todavía no se ha probado la futura implementación refactorizada en la PBX de laboratorio ni en un J129 físico.

**Riesgos / no comprobado:**
- Falta implementar el golden fixture J129 con credenciales ficticias.
- Falta configurar el self-hosted runner de laboratorio.
- Falta refactorizar `Avaya.py`.
- Falta restaurar el flujo stock de `issabel-endpointconfig` en una rama de trabajo y validar regresiones.
- Falta probar Apply -> archivo MAC -> HTTP/HTTPS -> registro de J129 físico en el entorno de laboratorio.

**Siguiente paso recomendado:**
- Añadir golden tests J129 antes de cambiar lógica funcional.
- Después configurar el runner read-only de la PBX de laboratorio.
- Refactorizar en commits pequeños y trazables, ejecutando tests después de cada cambio.

**Commit(s):**
- `0857495e9d72ac48e6cf48786a4c6e10a7887845 Add SOLID audit contract tests`
- `2c71565da242b006496d3c0068ac438a23186e2f docs: add shared AI agent context and collaboration protocol`
- El SHA del commit que crea este propio registro debe obtenerse del historial de Git; una entrada futura puede referenciarlo sin reescribir esta entrada.

---

## Handoff actual

El próximo agente debe:

1. leer `AGENTS.md`;
2. leer esta entrada;
3. revisar `tests/audit/`;
4. revisar el diff `main` vs upstream solamente en los componentes relevantes al J129;
5. no modificar todavía producción;
6. crear primero el golden contract del archivo J129 por MAC;
7. registrar aquí cualquier nueva conclusión o cambio.
