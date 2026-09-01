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

1. El administrador ejecuta la detección automática de endpoints.
2. Issabel detecta el dispositivo como Avaya y lo asocia al modelo J129.
3. El administrador abre el endpoint.
4. En la pestaña estándar **Accounts** asigna una extensión SIP/PJSIP.
5. Pulsa Apply.
6. Issabel obtiene la cuenta mediante su pipeline estándar.
7. El vendor Avaya genera el archivo de provisioning por MAC.
8. El J129 descarga su configuración por HTTP/HTTPS.
9. El teléfono registra automáticamente en Asterisk sin introducir manualmente usuario o contraseña SIP.

No se debe crear una interfaz paralela para introducir credenciales SIP Avaya.

## 2. Referencias del repositorio

- `main`: referencia histórica de una implementación funcional usada con J129. Contiene experimentos y deuda técnica. **No copiar ciegamente.**
- `Audit`: rama actual de auditoría, pruebas, documentación y futuro refactor controlado.
- Issabel oficial: `IssabelFoundation/endpointconfig2` debe utilizarse como referencia upstream para distinguir código stock de personalizaciones.

La implementación de `main` sirve como **reference implementation de comportamiento**, no necesariamente como arquitectura final.

## 3. Comportamiento J129 que debemos conservar

La implementación probada demuestra que el J129 necesita el concepto de configuración global + configuración específica por MAC.

Flujo esperado:

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

El archivo específico debe poder expresar, entre otros parámetros requeridos por el J129/firmware utilizado:

```text
SET FORCE_SIP_USERNAME "<extension>"
SET FORCE_SIP_PASSWORD "<secret>"
SET FORCE_SIP_EXTENSION "<extension>"
```

Los archivos se generan bajo `/tftpboot` como directorio lógico de provisioning. Ese contenido puede ser servido por HTTP/HTTPS y, para otros equipos cuando corresponda, TFTP.

No asumir que todos los modelos Avaya utilizan el mismo protocolo o parámetros.

## 4. Pipeline estándar de Issabel que debemos respetar

El diseño objetivo es:

```text
endpoint_account
  -> loadEndpointIP()
  -> issabel.Extension
       extension
       account
       secret
       description
       server_port
  -> Endpoint.setAccountList()
  -> self._accounts
  -> Avaya.Endpoint
  -> _prepareVarList()
  -> template/provisioning J129
  -> /tftpboot/<mac>.txt
```

`Extension.py` ya obtiene los datos SIP/PJSIP desde la base Asterisk. El vendor Avaya **no debe volver a consultar MySQL para obtenerlos**.

## 5. Archivos core que deben permanecer stock salvo evidencia extraordinaria

Preferir no modificar:

```text
/usr/bin/issabel-endpointconfig
/usr/share/issabel/endpoint-classes/class/issabel/BaseEndpoint.py
/usr/share/issabel/endpoint-classes/class/issabel/Extension.py
EndpointManager_Standard.class.php
```

Si un agente considera indispensable modificar uno de estos archivos:

1. debe documentar por qué el mecanismo de extensión de Issabel es insuficiente;
2. debe comparar explícitamente con upstream;
3. debe añadir pruebas que demuestren la necesidad;
4. no debe realizar el cambio silenciosamente.

## 6. Área prevista para personalización Avaya

Preferentemente:

```text
usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
```

más metadata necesaria en `endpointconfig`:

```text
manufacturer
model
model_properties
mac_prefix
```

y archivos globales de provisioning requeridos por J129.

## 7. Hallazgos de auditoría ya establecidos

### Stock confirmado

En la referencia analizada, `BaseEndpoint.py` y `Extension.py` coinciden con upstream de Issabel.

### Deuda técnica conocida en `main`

La implementación funcional contiene experimentos que **no deben convertirse automáticamente en diseño final**:

- constructor Avaya especial con `ext`/`secret`;
- ramas específicas `if Avaya` dentro de `issabel-endpointconfig`;
- construcción duplicada del objeto Endpoint;
- consultas MySQL directas desde `Avaya.py`;
- búsqueda manual de extension/secret/display name;
- descubrimiento de IP local mediante una conexión externa en vez de `_serverip`;
- logging de información sensible;
- credenciales de ejemplo/históricas embebidas;
- SQL construido por interpolación en algunos puntos;
- lógica duplicada entre PHP y Python;
- paso de secretos SIP mediante argumentos de proceso;
- templates experimentales que no representan necesariamente el archivo J129 que funciona en producción.

Las credenciales históricas encontradas en `main` ya fueron rotadas y se consideran ejemplos/referencia. Aun así, **ningún código nuevo debe incorporar secretos reales o de ejemplo reutilizables**.

## 8. Principios SOLID aplicados

### SRP — Single Responsibility

- detección detecta endpoints;
- UI estándar asigna cuentas;
- `Extension` resuelve datos de la extensión;
- `Avaya.Endpoint` implementa comportamiento Avaya;
- templates representan configuración;
- HTTP/HTTPS/TFTP sirven archivos, no resuelven cuentas SIP.

### OCP — Open/Closed

Agregar Avaya debe extender Issabel mediante vendor/templates/metadata, no llenar el core de condiciones `if manufacturer == Avaya`.

### LSP — Liskov

`Avaya.Endpoint` debe respetar el contrato normal:

```python
Endpoint(amipool, dbpool, serverip, ip, mac)
```

### ISP — Interface Segregation

No obligar a todos los Avaya a implementar capacidades de J129. En el futuro cada familia/modelo podrá tener perfiles distintos.

### DIP — Dependency Inversion

Avaya debe depender de los datos que Issabel le entrega (`_accounts`, `_serverip`, `_mac`, `_model`, propiedades), no de conexiones paralelas a MySQL ni de servicios externos.

## 9. Reglas de seguridad

Nunca incluir en commits, logs, tests o documentación:

- passwords reales de MariaDB/MySQL;
- SIP secrets reales;
- tokens GitHub;
- claves privadas;
- credenciales SSH;
- credenciales administrativas reales de teléfonos.

Fixtures deben utilizar valores inequívocamente ficticios, por ejemplo:

```text
extension = 4200
secret = TEST-SIP-SECRET-NOT-REAL
mac = C8:1F:EA:AA:BB:CC
server = 192.0.2.10
```

Nunca imprimir `Extension.secret` en logs de producción.

## 10. Estrategia de pruebas

### Nivel 1 — GitHub hosted

Tests estáticos/unitarios sin PBX:

- arquitectura;
- contratos SOLID;
- seguridad;
- templates;
- golden fixtures J129;
- regresiones.

Comando base:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Nivel 2 — PBX laboratorio read-only

Self-hosted GitHub Actions runner en PBX Issabel de laboratorio sobre Proxmox.

Permite auditar:

- versiones;
- `rpm -V`;
- Asterisk CLI;
- DB mediante SELECT controlado;
- `/tftpboot`;
- HTTP/HTTPS;
- servicios y logs.

### Nivel 3 — Integración J129

Solo manual (`workflow_dispatch`). Puede desplegar código candidato en la PBX de laboratorio, ejecutar Endpoint Configurator y comprobar provisioning.

Nunca desplegar automáticamente a producción desde un push.

Antes de pruebas destructivas debe existir snapshot de Proxmox.

## 11. Golden path J129

Todo agente que modifique provisioning debe conservar un test equivalente a:

```text
MAC:       C8:1F:EA:AA:BB:CC
IP phone:  192.0.2.100
PBX:       192.0.2.10
Extension: 4200
Secret:    TEST-SIP-SECRET-NOT-REAL
```

Resultado esperado conceptualmente:

```text
SET FORCE_SIP_USERNAME "4200"
SET FORCE_SIP_PASSWORD "TEST-SIP-SECRET-NOT-REAL"
SET FORCE_SIP_EXTENSION "4200"
```

El secret debe provenir del objeto `Extension` entregado por Issabel, no de consultas directas desde Avaya.

## 12. Protocolo obligatorio para agentes IA

Antes de trabajar:

1. Leer `AGENTS.md` completo.
2. Leer `docs/agent-log.md`.
3. Leer `docs/j129-lab-validation.md` para el estado físico/laboratorio más reciente.
4. Revisar los commits recientes de la rama de trabajo.
5. Revisar tests existentes.
6. Identificarse en el registro de agentes.
7. No asumir que `main` es arquitectura correcta solo porque funciona.
8. Comparar con upstream cuando se toque comportamiento de Issabel.

Después de trabajar:

1. ejecutar las pruebas relevantes;
2. registrar qué cambió;
3. registrar qué no se pudo comprobar;
4. registrar riesgos y próximos pasos;
5. incluir identificador del agente/modelo en el commit;
6. actualizar `docs/agent-log.md` en el mismo commit o inmediatamente después;
7. actualizar `docs/j129-lab-validation.md` si cambió evidencia física, lifecycle o provisioning.

## 13. Convención de identidad de agentes

Cada sesión debe escoger un identificador estable y visible:

```text
OpenAI-GPT-5.6-Sol
Claude-<version>
Gemini-<version>
Codex-<version>
Human-Axeell
```

Si no se conoce la versión exacta:

```text
<Proveedor>-<Modelo>-unknown
```

No inventar versiones.

## 14. Convención de commits

Formato recomendado:

```text
<type>(<scope>): <descripción corta>

Agent: <agent-id>
Task: <objetivo>
Tests: <comandos/resultados>
Audit: docs/agent-log.md
```

Tipos sugeridos: `docs`, `test`, `refactor`, `fix`, `feat`, `chore`, `security`.

Un commit debe representar una intención coherente. Evitar mezclar refactor, feature y cambios de infraestructura sin necesidad.

## 15. Regla de trazabilidad

Ningún agente debe afirmar que algo fue probado en una PBX real si solamente pasó tests estáticos.

Usar estados explícitos:

- `STATIC-PASS`
- `LAB-READ-PASS`
- `LAB-INTEGRATION-PASS`
- `PHYSICAL-J129-PASS`
- `PRODUCTION-REFERENCE`
- `NOT-TESTED`

La evidencia debe quedar en commits, Actions, `docs/agent-log.md` o `docs/j129-lab-validation.md`.

## 16. Qué NO hacer

- No hacer push directo a `main` para experimentos.
- No cambiar producción desde un workflow automático.
- No modificar core para resolver algo que puede implementarse en el vendor.
- No introducir un segundo origen para SIP secrets.
- No guardar SIP secret en `endpoint_properties`.
- No pasar SIP secret en argv.
- No registrar SIP secret en logs.
- No afirmar compatibilidad con otros modelos Avaya basándose en J129.
- No eliminar comportamiento funcional de `main` sin un test que explique qué se reemplaza.
- No interpretar `Registered at` de Endpoint Configurator como fuente autoritativa de registro SIP sin contrastar Asterisk.

## 17. Definición de terminado para J129

La primera versión refactorizada estará lista para candidata de producción cuando:

1. core Issabel permanezca stock o cualquier excepción esté justificada y probada;
2. detección Avaya/J129 funcione;
3. Accounts estándar asigne SIP/PJSIP;
4. Apply genere correctamente `<mac>.txt`;
5. credenciales provengan de `Extension`;
6. global config redirija a `$MACADDR.txt`;
7. archivo sea accesible mediante el protocolo requerido;
8. tests estáticos pasen;
9. integración en PBX de laboratorio pase;
10. un J129 físico registre y realice llamadas de prueba;
11. no existan secretos expuestos en logs/argv/repositorio;
12. exista procedimiento de rollback;
13. lifecycle de cambio/eliminación de cuentas y endpoint quede validado;
14. soporte real de dos cuentas quede validado o documentado explícitamente como limitación.

## 18. Fuente de verdad

En caso de contradicción, usar este orden:

1. comportamiento comprobado con J129 físico y evidencia reproducible;
2. Asterisk para estado real de registro SIP (`cuenta + IP + estado`);
3. documentación oficial Avaya aplicable al firmware/modelo;
4. código upstream oficial de Issabel;
5. tests del proyecto;
6. implementación histórica de `main`;
7. suposiciones/comentarios antiguos.

Toda discrepancia importante debe documentarse antes de decidir.

## 19. Estado validado del laboratorio — 2026-09-01

El refactor J129 ya superó varias etapas que antes figuraban como pendientes:

- `PHYSICAL-J129-PASS` — detección automática por OUI como Manufacturer `Avaya` y Model `J129`.
- `LAB-INTEGRATION-PASS` — metadata Avaya/J129 instalada de forma controlada en `endpointconfig`.
- `LAB-INTEGRATION-PASS` — Accounts estándar de Issabel asigna la extensión sin UI SIP paralela.
- `PHYSICAL-J129-PASS` — Apply estándar genera provisioning global y archivo por MAC.
- `PHYSICAL-J129-PASS` — el teléfono descarga por HTTP `J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt` con HTTP 200.
- `PHYSICAL-J129-PASS` — J129 registra correctamente en Asterisk mediante `chan_sip`.
- `PHYSICAL-J129-PASS` — ciclo `Remove -> Rescan -> Reassign -> Apply -> Reboot -> Auto-provision -> Register` validado.
- `PHYSICAL-J129-PASS` — cambio de extensión validado: guardar Accounts cambia DB, Apply regenera provisioning y el cambio se materializa en el teléfono después del reboot.

### Incidencia conocida: BUG-EC-001

Endpoint Configurator puede mostrar `Registered at: <IP>` para una cuenta SIP antigua que conserva el mismo host/IP pero cuyo peer está `UNREACHABLE`, mientras la cuenta actualmente asignada al teléfono sí aparece `OK` en Asterisk.

Regla operativa hasta corregir o comprender el comportamiento upstream:

```text
Estado SIP autoritativo = Asterisk + cuenta + IP + estado
```

No utilizar únicamente el texto `Registered at` de la GUI para decidir qué cuenta está activa.

### Pendientes inmediatos de validación v1

- probar dos extensiones simultáneas en J129;
- quitar una de dos cuentas y confirmar ausencia de residuos;
- quitar todas las cuentas manteniendo el endpoint;
- repetir `Remove configuration` y verificar DB + archivo por MAC + estado físico;
- probar idempotencia de rescan y Apply;
- validar comportamiento con endpoint offline durante Apply;
- completar pruebas de llamadas;
- añadir hashes/mtime a auditoría de archivos para demostrar recreación/idempotencia;
- mejorar auditoría SIP para observar registro residual aun cuando `endpoint_account` ya no exista;
- eliminar helper sync temporal antes de congelar candidata de producción.

La evidencia detallada de estas pruebas debe mantenerse en `docs/j129-lab-validation.md` y las acciones correspondientes.
