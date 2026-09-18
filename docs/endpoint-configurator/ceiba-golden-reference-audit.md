# Ceiba Endpoint Configuration — Golden Reference Audit

Objetivo: capturar el estado real y funcional de `cei-pbx02` antes de construir
el siguiente release candidate portable para una central limpia.

La auditoría es **read-only**. No ejecuta discovery, no cambia modelos, no asigna
extensiones, no instala runtime, no recarga servicios y no escribe en teléfonos.

## Workflow

`76 | Ceiba Production | Endpoint Configuration | Golden Reference Audit`

Confirmación manual:

`AUDIT-CEIBA-ENDPOINT-GOLDEN`

Debe ejecutarse únicamente sobre `main` y en el runner de producción
`cei-pbx02`.

## Qué documenta

La auditoría captura:

- versión real de Asterisk, Python, httpd e Issabel Endpoint Configurator;
- hashes y ownership de los helpers instalados;
- hash/paridad de Grandstream.py V2;
- hash/paridad de Avaya.py, templates J129 y configuración HTTP;
- hash/paridad de la UI de Endpoint Configurator instalada por Test71;
- hash/paridad de dependencias stock que RC3 no empaca explícitamente:
  - `/usr/bin/issabel-endpointconfig`;
  - `BaseEndpoint.py`;
  - `paloEndpointScanStatus.class.php`;
  - `paloSantoEndpoints.class.php`;
  - `EndpointManager_Standard.class.php`;
- esquema y runtime del vault de credenciales;
- catálogo Grandstream y sus canarios productivos;
- inventario/fleet audit de Avaya;
- evidencia SIP de 4450, 4452 y 4453 si el runner puede consultar Asterisk;
- inventario directo de endpoints/modelos/cuentas/OUI si el runner puede leer
  `/etc/amportal.conf`.

## Criterio para el próximo RC

No se debe construir RC4 hasta revisar el artefacto de esta auditoría.

El siguiente RC debe:

1. reproducir todos los archivos que en Ceiba difieran del stock o de RC3;
2. documentar explícitamente dependencias que se asumen stock;
3. explicar por qué Ceiba muestra modelo y registro para los Grandstream;
4. cubrir el caso de central limpia donde el endpoint existe pero todavía no
   tiene `endpoint_account`;
5. tener pruebas estáticas que reproduzcan las condiciones observadas en Ceiba;
6. mantener `production_runtime_write=NO`, `endpointconfig_write=NO` y
   `phone_write=NO` durante la auditoría.

## Evidencia esperada

El workflow genera un artefacto con:

- `ceiba-endpoint-golden-reference.txt`;
- `ceiba-endpoint-golden-reference.md`;
- `ceiba-endpoint-golden-fleet.txt`.

Después de ejecutar el workflow, el resultado real debe convertirse en un
documento versionado del repositorio con los hashes, modelos, cuentas y
diferencias encontradas. Ese documento será la referencia de aceptación para
RC4.
