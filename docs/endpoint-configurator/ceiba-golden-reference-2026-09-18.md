# Ceiba Endpoint Configuration — Golden Reference 2026-09-18

Referencia obtenida mediante el workflow read-only:

- Workflow: `76 | Ceiba Production | Endpoint Configuration | Golden Reference Audit`
- Run: `35405907865`
- Branch: `main`
- Resultado: `success`
- Evidencia drift SHA-256: `aaf71316cf1de175b36b1d718280779de1d5ca25c1ec2dfaa122071c2e98b283`

## Plataforma observada

- Host: `cei-pbx02.lamundial.hn`
- Asterisk: `18.19.0`
- Python: `3.6.8`
- Apache: `2.4.37`
- Endpoint Configurator RPM: `issabel-endpointconfig2-5.0.0-1.el8.noarch`

## Runtime confirmado

Grandstream V2 en producción:

`f145aa9bba942b9bcd5863bf591e7660e4f805c5a68bbb1b4f235444b99d5441`

Canarios:

| Modelo | IP | Extensión | Estado |
| --- | --- | --- | --- |
| GXP1625 | 10.3.40.29 | 4450 | Registered |
| GRP2601P | 10.3.40.42 | 4453 | Registered |
| GRP2602G | 10.3.40.43 | 4452 | Registered |

Marcadores:

- `GRANDSTREAM-PROD-CATALOG-VERIFY-PASS`
- `GRANDSTREAM-PROD-CANARY-EXTENSION-GUARD-PASS`
- `GRANDSTREAM-PROD-VENDOR-FINGERPRINT-PASS`
- `GRANDSTREAM-PROD-VERIFY-PASS`

## Paridad con el payload portable

Coinciden byte por byte con la referencia revisada:

- Grandstream.py V2
- Avaya.py
- Avaya_J129.tpl
- Avaya_global_SIP.tpl
- avaya-j129-provisioning.conf
- Endpoint Configurator index.php
- summary/index.php
- summary/lang/en.lang
- reporte_endpoints.tpl
- javascript.js
- EndpointCredentialVault.class.php
- BaseEndpoint.py
- paloEndpointScanStatus.class.php
- EndpointManager_Standard.class.php

## Drift encontrado y resolución

### /usr/bin/issabel-endpointconfig

Ceiba:

`2aca894449425f4666a851e6810eb8a51309544d18f3f6fbc563c697cbfe6e32`

Repo antes de normalizar:

`2424c5730fa486bee39e792235796f3c1d4fb236a0e265d09f164ad44d364edf`

El diff demostró que **Ceiba usa el flujo stock/limpio**. El repo arrastraba un
bloque antiguo para Avaya que:

- calculaba `ext` y `secret` fuera del flujo normal;
- instanciaba el endpoint Avaya dos veces;
- duplicaba validaciones;
- alteraba la indentación del bucle de endpoints.

Ese código no forma parte de la referencia productiva y se elimina del baseline
del repo antes de RC4.

### paloSantoEndpoints.class.php

Ceiba:

`f4d8c9150b2709ad3725765bb03eb303427be7b7985cbecfe01b6ae39a76993c`

Repo antes de normalizar:

`752f34818dd5b0720be699944d80783e8566deb521d0cd5cdd40bfda0efce18e`

La única diferencia era un comentario de debug:

`print_r($recordset)`

No tiene efecto funcional y se elimina para igualar Ceiba.

## Hallazgo de instalación limpia

La auditoría de Ceiba demuestra que el problema observado en Tocoa no depende de
un parche oculto de Ceiba.

En el código stock de `paloEndpointScanStatus.class.php`,
`_recogerCuentasRegistradas()` inicializa correctamente la estructura por IP:

`$cuentasRegistradas[$ip] = array('sip' => array(), ...)`

pero luego guarda SIP/IAX2/PJSIP en el nivel equivocado:

`$cuentasRegistradas['sip'][...]`

en lugar de:

`$cuentasRegistradas[$ip]['sip'][]`

El consumidor `_revisarCuentasRegistradasAsterisk()` itera por IP y espera una
lista de cuentas por tecnología. Por lo tanto, este defecto puede impedir que
una central limpia relacione automáticamente:

`IP registrada -> extensión -> endpoint_account`

Esto es consistente con Tocoa mostrando `Not assigned` después del discovery.

## Hallazgo de modelo Grandstream

`Grandstream.probeModel()` sigue dependiendo de métodos antiguos:

- banner Telnet;
- `/manager?action=product`;
- `/cgi-bin/api.values.get?request=phone_model:1395` sin autenticación.

Los GRP26xx modernos no exponen necesariamente el modelo con estos métodos. Esto
es consistente con Tocoa mostrando `(not detected)` aunque el OUI sí determine
`Grandstream`.

No se debe resolver por OUI porque GRP2601P y GRP2602G comparten
`EC:74:D7`.

## Evidencia que falta antes de RC4

El runner de Ceiba no pudo capturar directamente `sip show peer` ni el
inventario DB genérico fuera de los helpers root, por lo que la identificación
de modelo debe validarse contra una central limpia.

Antes de RC4 se debe capturar en Tocoa, read-only:

- qué peers SIP/PJSIP usan `10.3.184.40` y `10.3.184.41`;
- extensión de cada peer;
- `Useragent` real de cada teléfono;
- modelo actual en `endpointconfig.endpoint`;
- asociaciones actuales en `endpoint_account`.

## Criterio RC4

RC4 debe incluir pruebas que demuestren:

1. asociación correcta de cuentas por IP después de un discovery limpio;
2. persistencia correcta de `endpoint_account`;
3. detección GRP26xx sin usar OUI para distinguir modelos;
4. uso de una evidencia real como User-Agent cuando el teléfono ya está
   registrado;
5. ninguna escritura al teléfono durante discovery/model detection;
6. compatibilidad con GXP1625, GRP2601P, GRP2602G y J129;
7. rollback del runtime;
8. paridad con los hashes de la referencia de Ceiba.
