# Avaya J129 para Issabel 5 — release v0.1.0

Paquete mínimo orientado a una primera instalación controlada en producción.

## Alcance validado

- integración Avaya/J129 con Endpoint Configurator estándar;
- detección por OUI validado `C8:1F:EA`;
- una sola cuenta SIP por J129;
- generación de `J100Supgrade.txt`, `46xxsettings.txt` y archivo específico por MAC;
- provisioning HTTP restringido a los archivos Avaya necesarios;
- sin modificación de `/usr/bin/issabel-endpointconfig`, `BaseEndpoint.py`, `Extension.py` ni PHP del módulo.

## Payload

`payload/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py`

`payload/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl`

`payload/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl`

`payload/etc/httpd/conf.d/avaya-j129-provisioning.conf`

Los archivos de integración deben coincidir byte por byte con el payload que pasó las pruebas de LAB del workflow 12.

## No incluido en v0.1.0

- firmware;
- idioma español;
- menú local experimental;
- modificación automática de contraseña Web Admin;
- actualización sin reboot;
- resolución de la identidad SIP persistente tras retirar la última cuenta (`BUG-J129-004`).

## Distribución

La release final debe incluir un instalador autocontenido con:

`preflight -> backup -> install -> verify -> rollback`

No usar este directorio todavía en producción hasta incorporar el instalador final y repetir el smoke test sobre el paquete exacto de release.
