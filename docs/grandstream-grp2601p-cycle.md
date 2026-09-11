# Grandstream GRP2601P — ciclo de integración LAB

Actualizado: 2026-09-11

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
2. Test 63: autenticación y lectura de provisioning, con secret GRP separado.
3. Test 64: alta reversible del modelo/OUI exacto y rescan.
4. Test 65: bootstrap controlado del servidor de configuración.
5. Test 66: Configure, cfg/XML, SIP y auditoría E2E.
6. Validación física manual de llamadas/audio por el operador.

Los números 63–66 describen la secuencia prevista; deben reservarse únicamente
cuando cada prueba sea implementada.

## Reglas de seguridad

- Rama `Audit` y runner `issabel-lab` exclusivamente.
- No imprimir contraseñas, cookies, SID, nonces ni secretos SIP.
- No probar listas de contraseñas.
- No escribir teléfono/DB durante Test 62.
- No actualizar firmware automáticamente.
- Toda escritura posterior requiere IP/MAC/modelo inequívocos y rollback.
- Asterisk será la fuente autoritativa del registro SIP.

## Evidencia ejecutada

| Test | Run | Resultado |
|---:|---:|---|
| 62 | 34620373267 | LAB-READ-PASS: IP/MAC/modelo exactos; OUI y modelo ausentes en DB stock |
| 63 inicial | 34620205736 | Detención segura antes de escritura: OUI ausente |
| 63 corregido | 34620390872 | LAB-FIX-PASS: OUI + modelo ID 149; discovery stock exacto |
| 64 | 34620889592 | Server preflight PASS; lectura Web CREDENTIAL-BLOCKED por secret ausente |

Estado del endpoint después de Test 63:

```text
IP=192.168.1.176
MAC=EC:74:D7:1E:E8:E3
manufacturer=Grandstream
model=GRP2601P
model_id=149
max_accounts=2
max_sip_accounts=2
selected=0
account_count=0
```

La causa de la falta de detección quedó cerrada: Issabel no contenía la OUI
`EC:74:D7` ni el modelo `GRP2601P`. Ambos fueron agregados con estado de
rollback. El teléfono no ha sido configurado ni reiniciado.

## Gate vigente

Antes de bootstrap debe existir el Repository Secret
`GRANDSTREAM_GRP_HTTP_DEFAULT_PASSWORD` con la contraseña administrativa
aleatoria impresa en la etiqueta trasera del teléfono. No usar
`GRANDSTREAM_GXP_HTTP_DEFAULT_PASSWORD`.

Repetir Test 64 y exigir:

```text
login=SUCCESS
read=SUCCESS
model_match=YES
TEST64-GRP2601P-AUTH-READ=PASS
```

