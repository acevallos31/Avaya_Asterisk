# Base de conocimiento de pruebas

Este documento complementa `docs/j129-test-registry.md` y `docs/agent-log.md`.

Su objetivo es conservar el conocimiento operativo de las pruebas del proyecto para poder reutilizarlo en futuras versiones, otros modelos Avaya y, cuando aplique, otros fabricantes soportados por Issabel Endpoint Configurator.

## Cómo usar esta documentación

Cada prueba debe registrar no solo si pasó o falló, sino también:

- qué problema intenta detectar;
- qué componentes inspecciona;
- qué helper o workflow reutiliza;
- qué evidencia considera suficiente;
- qué datos nunca deben publicarse;
- cómo interpretar sus estados;
- qué limitaciones tiene;
- qué pruebas anteriores sirven como base.

El registro numérico autoritativo sigue siendo `docs/j129-test-registry.md`. Este documento explica el conocimiento detrás de las pruebas.

## Principios de diseño de las pruebas

### Reutilizar antes de crear

Antes de crear un helper nuevo se debe revisar si la prueba puede reutilizar componentes existentes. Actualmente son especialmente reutilizables:

- Test 02: consultas de Endpoint Configurator DB;
- Test 04: provisioning global y por MAC;
- Test 05: estado de registro SIP;
- Test 32: flujo de remoción de endpoint;
- Test 41: `check-sync` controlado;
- Test 43: estado integral J129;
- Test 46: auditoría read-only de producción;
- Test 47/49: resolución dinámica de peer, llamadas controladas y evidencia SIP/RTP;
- Test 51: auditoría segura de dos peers SIP;
- Test 53: inventario de flota Avaya en producción.

### Seguridad

Las pruebas nunca deben subir a GitHub:

- `SIPPASSWORD` en texto claro;
- secretos de Asterisk;
- cabeceras `Authorization` o `Proxy-Authorization`;
- credenciales MySQL;
- cookies o sesiones Web Admin;
- claves privadas;
- capturas SIP crudas con autenticación.

Cuando sea necesario comparar secretos, la comparación debe hacerse localmente y el log debe mostrar únicamente `MATCH`, `MISMATCH` o `UNKNOWN`.

Los workflows de producción deben usar el runner dedicado:

```yaml
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

y helpers restringidos por sudoers. No usar `sudo` genérico.

## Modelo mental de validación de un teléfono

Para considerar que un endpoint está correctamente operativo, la cadena completa es:

```text
Endpoint detectado
        ↓
Fabricante/modelo reconocidos
        ↓
Cuenta asignada en Endpoint Configurator
        ↓
Archivo de provisioning generado
        ↓
Credenciales generadas coinciden con Asterisk
        ↓
Teléfono solicita/descarga el archivo
        ↓
Teléfono envía REGISTER
        ↓
Peer SIP queda OK/Reachable
        ↓
Prueba física de llamada/audio/DTMF cuando aplique
```

Una prueba debe indicar claramente qué parte de esta cadena valida.

## Estados reutilizables de endpoint

### `DETECTED_ONLY`

Endpoint encontrado por Endpoint Configurator pero sin cuenta asignada.

Interpretación típica:

```text
endpoint existe
account = NONE
provisioning = MISSING
peer = NONE
```

No es necesariamente un error; puede ser un teléfono todavía pendiente de configuración.

### `CONFIGURED_NOT_PROVISIONED`

El endpoint tiene una cuenta asignada, pero no existe su archivo de provisioning por MAC.

Posibles causas:

- Apply no completado;
- error del vendor class/template;
- archivo eliminado;
- bug en el flujo de generación.

### `PROVISIONED_NOT_REGISTERED`

La cuenta está asignada y existe el archivo de provisioning, pero Asterisk no ve el peer registrado.

Diagnóstico recomendado:

```text
1. comparar SIPUSERNAME/AUTHNAME con la cuenta asignada;
2. comparar SIPPASSWORD con el secret real de Asterisk sin imprimirlo;
3. comprobar si el teléfono solicitó el archivo por HTTP;
4. revisar IP/puerto/transport/context del peer;
5. comprobar REGISTER sin publicar Authorization.
```

### `CONFIGURED_REGISTERED`

Endpoint asignado, provisionado y peer SIP `OK/Reachable`.

Este estado confirma registro, pero no prueba por sí solo audio bidireccional, DTMF ni operación física.

## Test 32 — Endpoint Remove Flow

### Propósito

Auditar el comportamiento de Endpoint Configurator al remover un endpoint o una cuenta.

### Conocimiento reutilizable

La tabla `endpoint_account` es la relación entre endpoint y cuenta SIP/IAX. Si una asociación queda huérfana, la extensión puede seguir existiendo en Asterisk pero dejar de aparecer como disponible en `Unassigned accounts`.

### Bug confirmado en producción

Caso observado en Ceiba:

```text
extension: 4413
endpoint anterior: id 16
modelo: Avaya J129
MAC: C8:1F:EA:C3:D6:45
```

La extensión fue removida del teléfono equivocado, pero permaneció una fila en `endpoint_account`:

```text
id=3
id_endpoint=16
tech=sip
account=4413
priority=1
```

Al eliminar únicamente esa asociación, la extensión volvió a aparecer como disponible.

### Regla para futuras correcciones

Nunca borrar el endpoint completo ni la extensión de Asterisk para corregir este caso. Se debe validar primero que la fila residual corresponde exactamente a la cuenta y endpoint esperados.

Este escenario debe convertirse en prueba de regresión para el hotfix v0.1.1.

## Test 49 — J129 Physical Call E2E

### Propósito

Validar llamada controlada hacia el J129 y RTP físico.

### Evidencia histórica útil

El helper resolvió dinámicamente la IP registrada a partir de la extensión/MAC, originó una llamada y usó `Echo` para validar RTP bidireccional. El operador confirmó audio físico.

### Reutilización

Sirve como base para:

- resolución de endpoint por extensión/MAC/IP;
- validación de peer READY;
- Caller ID de prueba;
- detección de answer;
- Echo/RTP;
- cleanup SIP/RTP debug.

No usar una IP histórica como fuente primaria: la IP debe resolverse desde el registro SIP actual.

## Test 51 — Dual SIP Peer Audit

### Propósito

Auditar origen y destino SIP antes de una llamada física endpoint-a-endpoint.

### Evidencia confirmada

En LAB:

```text
200 = Avaya J129
201 = Grandstream GXP1625
```

Ambos peers quedaron READY, `from-internal`, RFC2833 y DirectMedia=No.

### Reutilización

Este patrón es útil para validar interoperabilidad entre fabricantes antes de ejecutar llamadas físicas.

## Test 53 — Ceiba Production Avaya Fleet Audit

### Propósito

Inventariar todos los Avaya conocidos por Endpoint Configurator en `cei-pbx02` y clasificarlos sin realizar cambios.

### Datos obtenidos en la primera ejecución útil

```text
Avaya detectados: 17
Avaya configurados: 6
Avaya registrados: 3
Avaya detected_only: 11
Avaya configurados sin registro: 3
Fanvil detectados por Endpoint Configurator: 1
```

Registrados correctamente en esa ejecución:

```text
4413  C8:1F:EA:C3:DB:B2  10.3.40.33
4414  C8:1F:EA:C3:D6:B2  10.3.40.32
4408  C8:1F:EA:C3:D8:6B  10.3.40.37
```

Provisionados pero no registrados:

```text
4409  C8:1F:EA:C3:D6:45  last_ip=10.3.40.34
4412  C8:1F:EA:C3:D4:DD  last_ip=10.3.40.20
4411  C8:1F:EA:C3:D9:B4  last_ip=10.3.40.36
```

### Extensión de esquema

El Test 53 debe comprobar además:

```text
credential_user=MATCH|MISMATCH|UNKNOWN
credential_secret=MATCH|MISMATCH|UNKNOWN
config_request=YES|NO|UNKNOWN
request_ip=<IP o NONE>
request_http=<status o NONE>
request_time=<timestamp o NONE>
```

La comparación de contraseña se hace localmente. El valor nunca debe aparecer en el artifact.

### Interpretación de solicitudes HTTP

`config_request=YES` prueba que existe evidencia en los logs conservados de Apache de que el teléfono pidió su archivo por MAC.

`config_request=NO` no significa necesariamente que nunca lo descargó. Puede significar que:

- el acceso ocurrió antes de la ventana de logs;
- el log fue rotado/eliminado;
- el teléfono usó otro servidor/protocolo;
- la petición nunca ocurrió.

Por eso el estado debe interpretarse como `NO_EVIDENCE_IN_CURRENT_LOGS`, no como certeza histórica absoluta.

## Test 48 — Remote-Originated Call / 3PCC

### Resultado parcial conocido

La implementación actual consiguió:

```text
Asterisk llama al J129
J129 contesta
Asterisk solicita Transfer(SIP/201)
201 timbra
```

Esto prueba REFER/Transfer remoto, pero no prueba todavía que un comando remoto provoque que el J129 genere autónomamente un INVITE nuevo hacia 201.

### Condición real de PASS futuro

Debe demostrarse:

```text
comando remoto/control
        ↓
J129 genera INVITE nuevo
        ↓
destino 201
```

sin que Asterisk tenga que poner primero al J129 en una llamada `Up`.

## Test 50 — IVR y DTMF

### Objetivo

Construir una prueba reutilizable de interacción física:

```text
For English press 1
Para español presione 2
```

Luego validar audio, DTMF y Echo mediante SIP + AGI/dialplan controlado.

Primero se debe inventariar el catálogo de sonidos disponible en Issabel; no asumir que existen prompts en español.

## Plantilla para documentar nuevas pruebas

Agregar una sección con este formato:

```markdown
## Test NN — Nombre

### Propósito
Qué valida y qué problema intenta detectar.

### Entorno
LAB / Producción / manual.

### Dependencias reutilizadas
Helpers/workflows/tests anteriores usados como base.

### Flujo
Secuencia técnica de la prueba.

### Evidencia de PASS
Marcadores y señales suficientes.

### Evidencia de FAIL
Estados y fallos interpretables.

### Datos sensibles
Qué debe redactarse o nunca publicarse.

### Limitaciones
Qué NO demuestra esta prueba.

### Resultado histórico
Run, commit y conclusión cuando corresponda.

### Reutilización futura
Otros modelos, fabricantes o escenarios donde puede aplicarse.
```

## Relación entre documentos

- `docs/j129-test-registry.md`: catálogo autoritativo, número, workflow y estado.
- `docs/test-knowledge-base.md`: conocimiento técnico reusable e interpretación de pruebas.
- `docs/agent-log.md`: historial cronológico de cambios y acciones.
- `CONTEXT.md`: estado actual que un agente necesita para continuar el trabajo.
- runbooks y planes de release: procedimientos específicos de instalación/producción.

La base de conocimiento debe mantenerse estable y orientada a patrones reutilizables; el agent log puede crecer cronológicamente sin convertirse en manual operativo.
