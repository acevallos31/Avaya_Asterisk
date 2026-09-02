# Validación de gestión remota — Avaya J129

Fecha: 2026-09-01
Rama: `Audit`
Agente: `OpenAI-GPT-5.6-Sol`

Este documento conserva la evidencia de la investigación de gestión remota realizada sobre el J129 físico del laboratorio. No contiene contraseñas, hashes de credenciales, cookies, nonces ni tokens de sesión.

## Objetivo

Conseguir un mecanismo remoto, reproducible y seguro para hacer que el J129 vuelva a consultar provisioning sin introducir credenciales SIP manualmente y sin modificar el core de Issabel.

El caso inmediato es el bootstrap de `SET ENABLE_OOD_RESET_NOTIFY 1`: Issabel ya sirve esa directiva en `46xxsettings.txt`, pero el teléfono debe descargarla al menos una vez antes de poder depender de SIP NOTIFY `resync`/`check-sync` como mecanismo futuro.

## Estado de provisioning global

Después de usar el Apply nativo de Endpoint Configurator, la PBX LAB sirve un `46xxsettings.txt` regenerado por el overlay Avaya. La auditoría confirmó:

```text
ENABLE_OOD_RESET_NOTIFY=1
ENABLE_AVAYA_ENVIRONMENT=0
DISCOVER_AVAYA_ENVIRONMENT=0
ENABLE_3PCC_ENVIRONMENT=1
```

El archivo específico por MAC está ausente porque el endpoint se encuentra con cero cuentas asignadas. Esto es correcto server-side y forma parte de la corrección de `BUG-J129-003`.

Importante: que la PBX sirva la directiva no demuestra que el teléfono ya la haya cargado.

## Web UI — fingerprint y contrato observado

La Web UI del J129 LAB responde por HTTPS y se identificó como Avaya J100 Phone sobre `lighttpd/1.4.48`.

El teléfono expone `/cgi-bin/J100WebServer.cgi` y su propio JavaScript permitió clasificar operaciones relevantes:

- `Operation=4`: reinicio del teléfono. Es una acción modificadora y no se ha ejecutado durante estas auditorías.
- `Operation=6`: carga XML de páginas Web UI.
- `Operation=33`: comprobación de validez/timeout de sesión web. Se usó únicamente como probe read-only.

El JavaScript del propio teléfono muestra que `Operation=4` requiere `XToken` derivado de la cookie `J100sessionId`. No se deben imprimir ni persistir esos valores.

## Contrato real de login

La página de login contiene:

```text
form POST
onsubmit: RequestLogin(); return false
inputs: uname, psw
```

La función `RequestLogin()` no envía la contraseña en claro. El contrato observado en el HTML/JavaScript del teléfono es:

```text
passPhrase = password + J100nonce
passHash = SHA-256(UTF-8(passPhrase))
passHash = hexadecimal en mayúsculas
POST uname + psw=<passHash> a Operation=1
```

Se reprodujo este contrato desde el runner sin imprimir password, nonce, hash ni cookies.

## Resultado del login hash

Workflow: `Issabel Lab J129 Web Hashed Login Response Audit`

Run validado: `33571266115`

Resultado sanitizado del teléfono:

```text
bootstrap-status=200
nonce-presente=1
session-presente=1
login-status=200
login-content-type=text/html
login-bytes=210
text-fragments=Avaya J100 Phone | alert("Invalid username or password"); window.location.assign("/index.html");
semantic-markers=invalid,password
```

Conclusión: el mecanismo HTTP, cookies, nonce, SHA-256 y `Operation=1` fue reproducido suficientemente para obtener una respuesta explícita de autenticación. La credencial almacenada actualmente como GitHub Secret no es aceptada por el teléfono.

No se harán intentos de fuerza bruta ni listas de passwords.

## Operation 33

Cuando el login no establece una sesión válida, `Operation=33` responde con una página de sesión expirada que contiene semánticamente:

```text
You don't have access to this page. Please log in to access.
Web Session Expired.
```

Por tanto, un HTTP 200 por sí solo no prueba autenticación. Las auditorías deben clasificar el contenido de la respuesta.

## Password Web UI y provisioning

La investigación oficial identifica `FORCE_WEB_ADMIN_PASSWORD` como parámetro de provisioning para la contraseña de administración Web. Debe tratarse separadamente de `PROCPSWD` / `ADMIN_PASSWORD`, que pertenecen al menú Admin físico.

No se debe guardar una contraseña real en templates, fixtures, documentación ni Git. Si se prueba `FORCE_WEB_ADMIN_PASSWORD`, el valor deberá venir de un secreto/control de despliegue y la prueba deberá diseñarse para evitar exposición en provisioning histórico y logs.

Actualmente existe un problema circular: para aplicar una nueva contraseña mediante provisioning, el teléfono primero debe volver a descargar `46xxsettings.txt`.

## Preflight remoto previo a SIP NOTIFY

Workflow: `Issabel Lab J129 Notify Bootstrap Preflight`

Run validado: `33573812715`

Resultado:

```text
OOD-RESET-SERVER-SIDE=READY
J129-HTTPS-STATUS=200
J129-WEB-FINGERPRINT=PASS
J129-HTTP-REQUEST-AUDIT-PASS
J129-NOTIFY-BOOTSTRAP-PREFLIGHT-PASS
NOTIFY-ENVIADO=0
RESTART-ENVIADO=0
```

El run confirmó además:

```text
/tftpboot/46xxsettings.txt PRESENTE size=846
/tftpboot/J100Supgrade.txt PRESENTE
/tftpboot/c81fea9b650d.txt AUSENTE
```

El access log conserva evidencia histórica de que el J129 físico descargó `J100Supgrade.txt`, `46xxsettings.txt` y el archivo por MAC en boots anteriores. La última evidencia de esa auditoría no demuestra todavía que el teléfono haya descargado la versión actual de 846 bytes que contiene `ENABLE_OOD_RESET_NOTIFY 1`.

El preflight fue estrictamente preparatorio: no envió NOTIFY, no usó `Operation=4` y no reinició el teléfono.

## Ruta siguiente — SIP NOTIFY

Antes de introducir `FORCE_WEB_ADMIN_PASSWORD`, se añadió un segundo workflow read-only llamado `J129 | SIP | Notify Capability Audit`.

Su objetivo es determinar sin enviar tráfico modificador:

- si el runner puede consultar Asterisk CLI;
- qué ayuda expone `sip notify`;
- qué peer sigue asociado al J129/IP de laboratorio;
- si existen canales activos relacionados;
- si `/etc/asterisk/sip_notify.conf` es legible y qué tipos NOTIFY están definidos, mostrando solo nombres de secciones y cabeceras seguras.

Solo después de ese resultado se diseñará el workflow que envíe exactamente un `check-sync` o `resync` con confirmación explícita.

La prueba modificadora deberá cumplir:

1. confirmar que el destino corresponde al J129 LAB y a su IP esperada;
2. confirmar estado SIP antes de enviar cualquier NOTIFY;
3. confirmar que no hay llamada activa relacionada;
4. no imprimir secretos SIP;
5. no enviar NOTIFY en producción;
6. ejecutar como máximo un evento controlado;
7. observar si el teléfono cae/sube y si solicita `J100Supgrade.txt` / `46xxsettings.txt`;
8. volver a auditar provisioning y estado SIP;
9. clasificar un no-reinicio como evidencia posible de que el teléfono todavía no había cargado `ENABLE_OOD_RESET_NOTIFY=1`, no como fallo del overlay server-side.

## Seguridad

- No brute force de Web UI.
- No password real en Git.
- No cookies, nonce, hashes de login o XToken en logs.
- No `Operation=4` hasta demostrar sesión autenticada.
- No firmware upgrade durante este bootstrap.
- No factory reset como primera opción.
- No modificar core Issabel para resolver gestión remota.
- Los workflows modificadores deben ser `workflow_dispatch`, limitados al runner LAB y con prechecks.
- El capability audit de SIP NOTIFY es read-only y debe terminar con `NOTIFY-ENVIADO=0` y `RESTART-ENVIADO=0`.

## Estado

- Web UI discovery/fingerprint: `LAB-READ-PASS`.
- Contrato de login: `LAB-READ-PASS`.
- Login con credencial disponible: `LOGIN-REJECTED` por respuesta explícita del J129.
- Reinicio Web UI: `NOT-TESTED`.
- SIP NOTIFY preflight: `LAB-READ-PASS`.
- SIP NOTIFY capability audit: `READY-TO-RUN`.
- SIP NOTIFY modificador: `NOT-TESTED`.
- `ENABLE_OOD_RESET_NOTIFY=1` servido por la PBX: `LAB-INTEGRATION-PASS`.
- Carga efectiva de esa directiva por el teléfono: `NOT-TESTED`.

## No confundir con BUG-J129-004

El bootstrap remoto y `BUG-J129-004` están relacionados con lifecycle pero no son el mismo problema. `BUG-J129-004` sigue abierto: con cero cuentas y sin archivo MAC, el teléfono conserva una identidad SIP previamente persistida. Conseguir reiniciar/resincronizar remotamente no demuestra por sí mismo que esa identidad se borre.
