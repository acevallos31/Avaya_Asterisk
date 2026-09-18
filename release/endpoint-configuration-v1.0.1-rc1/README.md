# Endpoint Configuration v1.0.1-rc1 — prueba Tocoa

Candidato portable para instalar en una central Issabel nueva el soporte validado de
Endpoint Configuration sin copiar la configuración específica de Ceiba.

## Alcance de RC1

Incluye:

- Grandstream GXP1625.
- Grandstream GRP2601P (hasta 2 cuentas SIP).
- Grandstream GRP2602G (hasta 4 cuentas SIP).
- Login/provisioning Grandstream V2 validado en Ceiba.
- OUI Grandstream `C0:74:AD` y `EC:74:D7`.
- Avaya J129 (1 cuenta SIP) y OUI `C8:1F:EA`.
- Publicación HTTP requerida por el provisioning J129.
- preflight, backup, verify y rollback de runtime.

El instalador **no**:

- ejecuta discovery global;
- ejecuta `issabel-endpointconfig --applyconfig`;
- asigna extensiones;
- cambia contraseñas de teléfonos;
- reinicia teléfonos;
- incluye IPs, extensiones o hostname de Ceiba.

La contraseña administrativa de cada teléfono se sigue ingresando desde
**Custom credentials** en Endpoint Configuration durante la prueba.

> El vault de contraseña administrativa global que existe en Ceiba se mantiene fuera
> de este RC1 porque fue desplegado como un bloque separado y todavía no está
> consolidado en `main`. Lo integraremos después de validar este instalador limpio.

## Requisitos

- Issabel con `issabel-endpointconfig` instalado.
- Usuario `root`.
- `python3`, `php`, `mysql`, `apachectl`, `openssl` y `curl`.
- Acceso a la base `endpointconfig` mediante `/etc/amportal.conf`.
- Baseline Grandstream compatible. El RC1 falla cerrado si `Grandstream.py`
  no coincide con el baseline validado o no está ya en V2.

## Instalación en Tocoa

Después de descargar y extraer el paquete:

```bash
cd endpoint-configuration-v1.0.1-rc1
sudo bash install.sh preflight
sudo bash install.sh install
sudo bash install.sh verify
```

Estado:

```bash
bash install.sh status
```

Rollback del runtime:

```bash
sudo bash install.sh rollback
```

El rollback restaura los archivos previos. Los registros de catálogo añadidos de
forma idempotente se conservan para evitar borrar metadata que pueda estar siendo
usada por endpoints creados después de la instalación.

## Prueba funcional prevista en Tocoa

1. Ejecutar `preflight`, guardar la salida.
2. Ejecutar `install` y `verify`.
3. Entrar a **Endpoint Configuration**.
4. Ejecutar discovery manual únicamente sobre el segmento/rango que se decida probar.
5. Seleccionar un teléfono canario.
6. Definir su contraseña administrativa real en **Custom credentials**.
7. Asignar una extensión de prueba.
8. Ejecutar Configure/Apply desde la UI.
9. Confirmar registro SIP y una llamada entrante/saliente.
10. Repetir por modelo.

Modelos que deben probarse primero:

| Modelo | Resultado esperado |
| --- | --- |
| GXP1625 | Login V2, configuración y registro SIP |
| GRP2601P | Challenge login, configuración y registro SIP |
| GRP2602G | Challenge login, configuración y registro SIP |
| Avaya J129 | Generación/provisioning y registro SIP |

## Evidencia esperada del instalador

Una instalación correcta termina con:

```text
[Endpoint Configuration 1.0.1-rc1] VERIFY-PASS
[Endpoint Configuration 1.0.1-rc1] supported_grandstream=GXP1625,GRP2601P,GRP2602G
[Endpoint Configuration 1.0.1-rc1] supported_avaya=J129
[Endpoint Configuration 1.0.1-rc1] phone_write=NO
[Endpoint Configuration 1.0.1-rc1] endpoint_discovery=NO
[Endpoint Configuration 1.0.1-rc1] INSTALL-PASS
```

No continuar con pruebas físicas si `preflight`, `install` o `verify` terminan
con ERROR.
