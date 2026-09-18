# Endpoint Configuration v1.0.1-rc3 — Tocoa

RC3 corrige el paquete RC1 para reproducir el runtime funcional completo que fue
validado en Ceiba.

## Por qué existe RC3

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

RC3 agrega exactamente esos componentes desde el candidato inmutable de producción:

`6fc9334130b8867d7dc1722bfe35fd895e30d321`

No reconstruye manualmente esa UI.

## Uso sobre Tocoa con RC1 ya instalado

No es necesario hacer rollback de RC1.

```bash
tar -xzf endpoint-configuration-v1.0.1-rc3.tar.gz
cd endpoint-configuration-v1.0.1-rc3

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
version=1.0.1-rc3
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

RC3 crea un backup nuevo bajo:

`/var/lib/issabel-endpoint-configuration/1.0.1-rc3/`

Por tanto, en Tocoa el rollback de RC3 vuelve al runtime que estaba justo antes de
RC3, es decir, al RC1 actualmente instalado.

```bash
sudo bash install.sh rollback
```

El rollback restaura archivos. Por seguridad no elimina automáticamente:

- las tres tablas de credenciales;
- la clave de cifrado;
- filas de catálogo.

Esto evita destruir credenciales o metadata que ya puedan estar en uso.

## Bootstrap DBA temporal

RC3 ya no requiere conceder DDL permanente a `asteriskuser`.

Si las tres tablas de credenciales no existen, `preflight` informa:

```text
DBA-BOOTSTRAP=REQUIRED-DURING-INSTALL
```

Al ejecutar `install`, el instalador intenta primero autenticación DBA local. Si
no está disponible, solicita:

```text
Usuario DBA MariaDB [root]:
Contraseña MariaDB para root:
```

La contraseña se captura con entrada oculta. Se guarda únicamente en un archivo
temporal `0600` dentro de `/tmp`, nunca se pasa por argv ni se imprime en logs,
y ese archivo se elimina al terminar el bootstrap. La variable que contiene la
contraseña también se elimina antes de ejecutar el cliente MySQL.

El DBA crea únicamente el esquema requerido. No se otorgan `CREATE`, `ALTER`,
`INDEX`, `REFERENCES`, `DROP` ni `ALL PRIVILEGES` permanentes a
`asteriskuser`.

Después de crear el esquema, RC3 valida que el usuario normal de Issabel puede
hacer SELECT/INSERT/UPDATE/DELETE mediante una transacción que termina en ROLLBACK.

## Prueba funcional después de RC3

Antes de hacer discovery o configurar teléfonos:

1. recargar Endpoint Configuration;
2. confirmar la columna **Extension / Registration**;
3. confirmar la sección/panel de seguridad administrativa;
4. comprobar que la pantalla no genere error 500.

Solo después se continúa con el canario de Tocoa.
