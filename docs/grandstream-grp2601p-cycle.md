# Grandstream GRP2601P — ciclo de integración LAB

Actualizado: 2026-09-12

## Objetivo

Incorporar un GRP2601P físico de fábrica al Endpoint Configurator estándar de
Issabel 5 usando la misma arquitectura general validada con GXP1625/GXP1630,
pero sin asumir que la autenticación Web, la plantilla o los P-values son
idénticos.

## Datos oficiales relevantes

- Dos cuentas SIP y dos líneas.
- Dos puertos Ethernet 10/100 y PoE integrado en la variante P.
- Aprovisionamiento por HTTP/HTTPS, TFTP, FTP/FTPS, DHCP Option 66, TR-069 y
  GDMS.
- Archivos soportados: `cfg<MAC>`, `cfg<MAC>.xml`, `cfggrp2601.xml`,
  `cfg.xml` y `dev<MAC>.cfg`.
- Firmware estable observado en la página oficial al iniciar el ciclo:
  `1.0.7.66`; no se autoriza upgrade durante discovery.
- Usuario administrativo: `admin`; la contraseña inicial es aleatoria y está
  en la etiqueta del teléfono. No debe reutilizarse automáticamente el secret
  de la familia GXP.

Fuentes oficiales:

- https://www.grandstream.com/products/ip-voice-telephony-carrier-grade-ip-phones/grp-series-essential-ip-phones/product/grp2601p/w
- https://www.grandstream.com/support/firmware
- https://documentation.grandstream.com/knowledge-base/grp260x-series-administration-guide/
- https://www.grandstream.com/hubfs/Product_Documentation/GRP26XX_Plug_and_Play_Guide.pdf

## Hipótesis inicial

Endpoint Configurator no detecta el teléfono porque falta uno o más elementos
en su catálogo local: OUI/prefijo MAC, modelo GRP2601P o ambas cosas. También es
posible que la superficie HTTP sin autenticar difiera del contrato GXP.

La hipótesis debe resolverse con evidencia de red y DB, no insertando registros
a ciegas.

## Secuencia

1. Test 62: discovery read-only de red, identidad HTTP y cobertura DB/OUI.
2. Test 63: alta reversible del modelo/OUI exacto y rescan.
3. Test 64: autenticación y lectura de provisioning, con secret GRP separado.
4. Test 65: bootstrap controlado del servidor de configuración.
5. Test 66: Configure, cfg/XML, SIP y auditoría E2E.
6. Validación física manual de llamadas/audio por el operador.


Los Tests 62–66 están cerrados en LAB. La validación física manual de
llamadas/audio permanece pendiente.

## Reglas de seguridad

- Rama `Audit` y runners LAB etiquetados exclusivamente.
- No imprimir contraseñas, cookies, SID, nonces, hashes ni secretos SIP.
- No probar listas de contraseñas.
- No actualizar firmware automáticamente.
- Toda escritura requiere IP/MAC/modelo inequívocos, verificación y rollback.
- Asterisk es la fuente autoritativa del registro SIP.
- El bridge de contraseña por stdin y sustitución temporal del model_property
  es solo para LAB; producción exige almacenamiento cifrado y UI.

## Evidencia ejecutada

| Test | Run | Resultado |
|---:|---:|---|
| 62 | 34620373267 | LAB-READ-PASS: IP/MAC/modelo exactos; OUI y modelo ausentes en DB stock |
| 63 | 34620390872 | LAB-FIX-PASS: OUI + modelo ID 149; discovery stock exacto |
| 64 | 34664338896 | LAB-READ-PASS: contraseña de etiqueta válida con nonce/SHA-256; lectura sin escrituras |
| 65 preflight | 34670448152 | Contrato público GRP: `config_update`, no `api.values.post` |
| 65 | 34670575973 | LAB-FIX-PASS: P212/P237, reboot y persistencia PASS |
| 66 preflight | 34670740654 | Endpoint exacto limpio; SIP 203 presente, libre y no registrado |
| 66 intento 1 | 34671167798 | HARNESS-FAIL: probe sin `/cgi-bin`; ruta GXP usada por error |
| 66 recuperación inicial | 34677542766 | Preflight detuvo la repetición por etapa pendiente |
| 66 autoritativo | 34677554254 | LAB-INTEGRATION-PASS: recovery, patch v2, Apply, cfg/XML, HTTP y SIP 203 PASS |

## Contrato GRP2601P comprobado

```text
POST /cgi-bin/access
  access = SHA256(username)
  response.body = nonce

POST /cgi-bin/dologin
  username = admin
  password = SHA256(label_password + nonce)
  response.body = SID

PUT /cgi-bin/config_update
  Content-Type: application/json
  body = {"alias": {}, "pvalue": {...}}

GET /cgi-bin/api-sys_operation?request=REBOOT&sid=<SID>
```

El teléfono nunca recibe la contraseña administrativa en texto claro durante
el challenge. Los reportes no contienen contraseña, nonce, hash, SID, cookie ni
secreto SIP.

## Hallazgos del harness

Issabel puede devolver exit code 0 aunque un endpoint individual termine con
`failed configuration`. Test 66 ahora trata ese mensaje como fallo, elimina
cuenta/selección/cfg de etapa y conserva un recovery idempotente antes de cada
reintento.

El patch GRP26xx es reversible y se instala únicamente si el SHA del
`Grandstream.py` live coincide con el baseline comprobado. El patch v1 fue
revertido antes de instalar v2 porque el probe debía consultar
`/cgi-bin/api-will_login`.

## Estado final LAB

```text
IP=192.168.1.176
MAC=EC:74:D7:1E:E8:E3
manufacturer=Grandstream
model=GRP2601P
model_id=149
max_accounts=2
max_sip_accounts=2
selected=0
account_count=1
account=203
P212=0
P237=192.168.1.10
binary_cfg_present=YES
xml_cfg_present=YES
phone_http=200
sip_203_ip=192.168.1.176
```

Las extensiones 201 y 202 no fueron desplazadas al GRP. El password temporal
del modelo fue restaurado después de Apply.

## Gate vigente

Estado técnico: `LAB-INTEGRATION-PASS`.

Pendiente antes de producción:

1. confirmar físicamente llamada entrante/saliente y audio con la extensión 203;
2. implementar almacenamiento cifrado de credenciales administrativas;
3. agregar captura manual y carga masiva por MAC desde Endpoint Configurator;
4. definir contraseña administrativa final global por PBX y override por
   endpoint;
5. repetir el flujo desde la UI y documentar la evidencia;
6. preparar después un canario productivo con preflight y rollback propios.
