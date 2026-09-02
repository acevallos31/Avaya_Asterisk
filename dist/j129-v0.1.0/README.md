# Avaya J129 para Issabel 5 — parche v0.1.0

Primer candidato de distribución para una central Issabel 5 existente.

## Objetivo

Instalar la integración Avaya/J129 sin reemplazar core de Issabel y conservando el flujo estándar:

`Discovery -> Avaya/J129 -> Accounts -> Apply -> 46xxsettings -> archivo MAC -> SIP`

## Incluye

- `Avaya.py` refactorizado para consumir las cuentas entregadas por `BaseEndpoint`/`Extension`.
- `Avaya_J129.tpl`.
- `Avaya_global_SIP.tpl`.
- publicación HTTP restringida de los archivos de provisioning Avaya.
- metadata DB idempotente para fabricante `Avaya`, modelo `J129` y OUI `C8:1F:EA`.
- límite v1 de una cuenta: `max_accounts=1`, `max_sip_accounts=1`, `max_iax2_accounts=0`.
- preflight, backup, verify y rollback.

## No incluye en v0.1.0

- actualización automática de firmware;
- idioma español;
- cambios de contraseña Web Admin;
- configuración experimental del menú local;
- NTP/zona horaria específicos de una sede;
- forced update sin reboot;
- resolución de la persistencia SIP local después de retirar la última cuenta (`BUG-J129-004`).

Estas capacidades siguen documentadas como deuda técnica y no deben bloquear el parche mínimo de producción.

## Comandos

Desde la raíz del repositorio, como `root`:

```bash
bash dist/j129-v0.1.0/install.sh preflight
bash dist/j129-v0.1.0/install.sh install
bash dist/j129-v0.1.0/install.sh verify
```

Rollback:

```bash
bash dist/j129-v0.1.0/install.sh rollback
```

## Seguridad y comportamiento

- El instalador obtiene credenciales DB desde `/etc/amportal.conf` mediante un archivo temporal `0600`; no imprime passwords.
- Antes de modificar archivos guarda el estado previo bajo `/var/lib/avaya-j129-issabel/0.1.0/`.
- Aborta si existe fabricante/modelo duplicado, si el OUI pertenece a otro fabricante o si ya existen más de una cuenta asignada a un J129.
- No ejecuta `issabel-endpointconfig --applyconfig` automáticamente y no reinicia teléfonos.
- No toca `/usr/bin/issabel-endpointconfig`, `BaseEndpoint.py`, `Extension.py` ni PHP del módulo.

## Procedimiento previsto en producción

1. snapshot/backup de la VM o servidor;
2. ejecutar `preflight` y guardar la salida;
3. ejecutar `install`;
4. ejecutar `verify`;
5. entrar a Endpoint Configurator y hacer discovery/rescan si corresponde;
6. asignar una extensión desde Accounts;
7. hacer Apply desde Issabel;
8. validar provisioning y registro SIP;
9. reiniciar/resync del teléfono solo como operación separada si necesita consumir el provisioning.

No ejecutar este candidato en producción hasta que el workflow 12 del LAB valide instalación repetida, verify y rollback.
