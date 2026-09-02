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

```text
payload/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
payload/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
payload/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
payload/etc/httpd/conf.d/avaya-j129-provisioning.conf
```

El installer es autocontenido y trabaja desde este directorio de release.

## Instalador

Comandos previstos:

```text
bash install.sh preflight
bash install.sh install
bash install.sh verify
bash install.sh rollback
```

El diseño conserva backup/estado para poder revertir los archivos y propiedades tocadas.

## Validación previa

El workflow 12 del LAB validó el candidato con:

```text
preflight -> install -> verify -> install -> verify -> rollback
```

Esto confirmó instalación, verificación, idempotencia y rollback del candidato antes del empaquetado final.

## Smoke test del paquete exacto

Workflow:

```text
13 | Issabel Lab | J129 Release Package | Smoke Test
```

Estado actual: bloqueado por infraestructura del self-hosted runner antes de probar el installer exacto.

Error observado:

```text
EACCES: permission denied, unlink
.../vendor/__pycache__/Avaya.cpython-36.pyc
```

La causa es un archivo `.pyc` creado previamente por `root` dentro del workspace del runner. `actions/checkout`, ejecutado como `github-runner`, no puede eliminarlo durante su limpieza inicial.

Este rojo no debe interpretarse como fallo funcional de v0.1.0 porque el job no llegó a ejecutar el ciclo del installer.

La release NO debe usarse todavía en producción hasta que el workflow 13 complete el ciclo exacto y quede verde.

## Archivos de referencia históricos

No incluir dentro del payload:

- copias estáticas de `46xxsettings.txt`;
- configuraciones de un teléfono/sitio histórico;
- Phone Reports;
- credenciales o secretos.

El archivo histórico `46xxsettings.txt funciona Choloma.txt` es una referencia conocida funcional, no un archivo requerido para instalar. Si se conserva, debe revisarse por secretos y guardarse como ejemplo claramente no instalable, por ejemplo:

```text
examples/j129-working-reference-choloma.txt
```

El `46xxsettings.txt` operativo debe generarlo Issabel desde `Avaya_global_SIP.tpl`.

## No incluido en v0.1.0

- firmware;
- idioma español;
- menú local experimental;
- modificación automática de contraseña Web Admin;
- actualización sin reboot;
- resolución definitiva de identidad SIP persistente tras retirar la última cuenta (`BUG-J129-004`).

## Requisitos antes de producción

1. workflow 13 verde sobre este paquete exacto;
2. congelar versión y SHA256;
3. auditar la central destino;
4. confirmar versión Issabel, rutas core, DB y estado Avaya existente;
5. backup/snapshot;
6. ejecutar `preflight` antes de modificar;
7. instalar y ejecutar `verify`;
8. probar discovery, asignación de cuenta, Apply, HTTP provisioning y SIP;
9. ejecutar rollback si cualquier criterio crítico falla.

## Seguridad

- no imprimir secretos SIP;
- no almacenar contraseña Web Admin en el paquete;
- no ampliar sudo para instalar;
- no usar `chmod 777` como workaround;
- no incluir reportes brutos del teléfono.
