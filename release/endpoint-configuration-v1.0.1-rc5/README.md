# Endpoint Configuration v1.0.1-rc5 — Ceiba Golden + Clean Bootstrap

RC5 parte del runtime auditado de Ceiba y agrega únicamente dos correcciones para
que una central limpia pueda llegar al mismo estado funcional sin seleccionar
modelos ni asociar extensiones manualmente.

## Base requerida

- Rocky Linux 8.10
- Asterisk 18.19.0
- Python 3.6.8
- Apache 2.4.37
- issabel-endpointconfig2-5.0.0-1.el8.noarch

Es la misma base confirmada en Ceiba y Tocoa.

## Cambios sobre la imagen dorada de Ceiba

Solo cambian dos componentes:

1. `Grandstream.py`
   - conserva Grandstream V2 validado en Ceiba;
   - si los métodos legacy no detectan el modelo, consulta Asterisk en modo
     read-only;
   - correlaciona el peer registrado por IP;
   - lee `Useragent`;
   - mapea únicamente modelos conocidos:
     - `GRP2601` / `GRP2601P` -> `GRP2601P`
     - `GRP2602G` -> `GRP2602G`
     - `GXP1625` -> `GXP1625`;
   - no autentica contra el teléfono y no escribe en él durante detección.

2. `paloEndpointScanStatus.class.php`
   - corrige la estructura interna de cuentas registradas para guardar:
     `IP -> tecnología -> lista de extensiones`;
   - permite que el flujo stock reconcilie una extensión ya registrada con el
     endpoint detectado y cree `endpoint_account`.

Todos los demás archivos siguen siendo los hashes auditados de Ceiba.

## Seguridad

El instalador NO:

- ejecuta discovery automáticamente;
- ejecuta Configure/Apply;
- cambia contraseñas de teléfonos;
- reinicia teléfonos;
- copia extensiones o datos de Ceiba.

El bootstrap DBA temporal de RC3/RC4 se conserva para crear el esquema de
credenciales si hace falta.

## Instalación limpia

```bash
tar -xzf endpoint-configuration-v1.0.1-rc5.tar.gz
cd endpoint-configuration-v1.0.1-rc5

sudo bash install.sh preflight
sudo bash install.sh install
sudo bash install.sh verify
```

Marcadores esperados:

```text
CEIBA-GOLDEN-PAYLOAD-PASS
RC5-CLEAN-BOOTSTRAP-PAYLOAD-PASS
CEIBA-GOLDEN-RUNTIME-INSTALL-PASS
CEIBA-GOLDEN-SHA-PARITY-PASS
RC5-CLEAN-BOOTSTRAP-PASS
VERIFY-PASS
INSTALL-PASS
```

## Después de instalar

Los teléfonos deben estar registrados en Asterisk antes del discovery si se
quiere usar el fallback de modelo por User-Agent.

Luego se ejecuta el discovery manual desde Endpoint Configurator. El resultado
esperado en Tocoa es:

- fabricante Grandstream por OUI;
- modelo GRP2601P detectado desde Asterisk Useragent cuando corresponda;
- extensión registrada reconciliada por IP;
- columna Extension / Registration mostrando el estado correcto.

## Rollback

```bash
sudo bash install.sh rollback
```

RC5 hace backup antes de modificar archivos.
