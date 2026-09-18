# Endpoint Configuration v1.0.1-rc2 — Tocoa

RC2 corrige el paquete RC1 para reproducir el runtime funcional completo que fue
validado en Ceiba.

## Por qué existe RC2

RC1 instaló correctamente:

- Grandstream GXP1625 / GRP2601P / GRP2602G;
- Grandstream runtime V2;
- Avaya J129;
- catálogo de modelos y OUI.

Pero dejó fuera el bloque Test71 que en Ceiba aporta:

- columna **Extension / Registration**;
- sección de **Seguridad administrativa**;
- contraseña administrativa global;
- override de credencial por endpoint/MAC;
- vault cifrado;
- diálogo de resumen de registro.

RC2 agrega exactamente esos componentes desde el candidato inmutable de producción:

`6fc9334130b8867d7dc1722bfe35fd895e30d321`

No reconstruye manualmente esa UI.

## Uso sobre Tocoa con RC1 ya instalado

No es necesario hacer rollback de RC1.

```bash
tar -xzf endpoint-configuration-v1.0.1-rc2.tar.gz
cd endpoint-configuration-v1.0.1-rc2

sudo bash install.sh preflight
```

Revisar primero la salida del preflight. Si termina en `PREFLIGHT-PASS`, ejecutar:

```bash
sudo bash install.sh install
sudo bash install.sh verify
```

Estado:

```bash
bash install.sh status
```

Se espera:

```text
version=1.0.1-rc2
installed=YES
credential_vault=YES
extension_registration_ui=YES
admin_security_ui=YES
```

La verificación completa debe incluir:

```text
VERIFY-PASS
ui_extension_registration=YES
ui_admin_security=YES
credential_vault=YES
supported_grandstream=GXP1625,GRP2601P,GRP2602G
supported_avaya=J129
phone_write=NO
endpoint_discovery=NO
INSTALL-PASS
```

## Seguridad

- La clave AES se crea en `/etc/issabel/endpoint-configurator.key`.
- Debe quedar `root:asterisk:640`.
- Las contraseñas se almacenan cifradas en la base `endpointconfig`.
- El instalador no imprime contraseñas.
- No ejecuta discovery.
- No ejecuta Apply/Configure.
- No asigna extensiones.
- No reinicia teléfonos.

## Backup y rollback

RC2 crea un backup nuevo bajo:

`/var/lib/issabel-endpoint-configuration/1.0.1-rc2/`

Por tanto, en Tocoa el rollback de RC2 vuelve al runtime que estaba justo antes de
RC2, es decir, al RC1 actualmente instalado.

```bash
sudo bash install.sh rollback
```

El rollback restaura archivos. Por seguridad no elimina automáticamente:

- las tres tablas de credenciales;
- la clave de cifrado;
- filas de catálogo.

Esto evita destruir credenciales o metadata que ya puedan estar en uso.

## Nota sobre permisos DB

Si la base de Tocoa no permite crear las tres tablas de credenciales con el usuario
definido en `/etc/amportal.conf`, la instalación se detendrá. No se amplían
privilegios DB automáticamente. En ese caso se revisarán los grants antes de
continuar.

## Prueba funcional después de RC2

Antes de hacer discovery o configurar teléfonos:

1. recargar Endpoint Configuration;
2. confirmar la columna **Extension / Registration**;
3. confirmar la sección/panel de seguridad administrativa;
4. comprobar que la pantalla no genere error 500.

Solo después se continúa con el canario de Tocoa.
