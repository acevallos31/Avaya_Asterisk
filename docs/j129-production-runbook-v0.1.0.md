# Runbook de producción — Avaya J129 / Issabel v0.1.0

Estado: PREPARADO, pendiente de auditoría de la central destino.

## Release autorizada para evaluar en producción

La única release que puede avanzar a preflight de producción es el contenido exacto del commit:

```text
74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Evidencia LAB asociada:

```text
Workflow 13: 13 | Issabel Lab | J129 Release Package | Smoke Test
Run: 33648748733
Resultado: PASS
```

No sustituir por HEAD de la rama ni por un commit posterior sin repetir validación LAB.

## Principios

- No instalar primero y auditar después.
- No modificar core de Issabel.
- No reconsultar secretos SIP desde DB en el vendor.
- No imprimir credenciales SIP ni credenciales Web Admin.
- No hacer upgrade automático de firmware.
- No reiniciar el teléfono como parte del instalador.
- J129 v0.1.0 soporta una sola cuenta SIP.
- Mantener una vía de rollback disponible antes de instalar.

## 1. Congelamiento e integridad

Generar el manifiesto con:

```text
14 | J129 Release v0.1.0 | Freeze Manifest
confirm: FREEZE-V010
```

El workflow debe terminar con:

```text
J129-V010-FREEZE-MANIFEST-PASS
J129-V010-FROZEN-SHA=74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
J129-V010-FREEZE-PASS
```

Descargar y conservar el artifact `j129-v0.1.0-freeze-manifest` junto con la evidencia del cambio.

Antes de copiar el paquete a producción, verificar localmente los hashes del manifiesto desde la raíz `release/j129-v0.1.0`:

```bash
sha256sum -c j129-v0.1.0-SHA256SUMS.txt
```

Todos deben indicar `OK`.

## 2. Auditoría read-only de la central destino

Antes de instalar registrar, sin secretos:

```bash
cat /etc/redhat-release
asterisk -rx 'core show version'
python3 --version
httpd -v
ls -ld /usr/share/issabel/endpoint-classes
ls -l /usr/bin/issabel-endpointconfig
```

Confirmar que la DB usada por Endpoint Configurator es `endpointconfig` en MySQL/MariaDB.

Auditar fabricante/modelo/OUI existente antes de cualquier escritura. No asumir nombres o estructura distinta sin inspeccionarla primero.

Criterios mínimos:

- Issabel 5 compatible con la estructura probada;
- `/usr/share/issabel/endpoint-classes` presente;
- `/usr/bin/issabel-endpointconfig` presente;
- Apache funcional;
- MySQL/MariaDB accesible mediante la configuración de Issabel;
- no existe conflicto de OUI `C8:1F:EA` con otro fabricante;
- no existe fabricante Avaya duplicado;
- no existe modelo J129 duplicado;
- ningún J129 existente tiene más de una cuenta asignada.

Si cualquiera de estos puntos no coincide con el LAB, detener la instalación y evaluar la diferencia.

## 3. Backup previo

Tomar snapshot/backup del servidor según la política de la central antes de instalar.

Además conservar copia de los archivos que podría tocar la release si existen:

```text
/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py
/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl
/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl
/etc/httpd/conf.d/avaya-j129-provisioning.conf
```

El instalador también mantiene su propio estado de rollback bajo:

```text
/var/lib/avaya-j129-issabel/0.1.0/
```

El snapshot externo sigue siendo obligatorio porque protege más que el alcance del instalador.

## 4. Preflight

Desde la raíz del paquete exacto:

```bash
sudo ./install.sh preflight
```

Continuar únicamente si termina con:

```text
[J129-PATCH 0.1.0] PREFLIGHT-PASS
```

No continuar ante warnings que indiquen conflicto de DB, archivos faltantes o incompatibilidad estructural.

## 5. Instalación

```bash
sudo ./install.sh install
```

Resultado esperado:

```text
[J129-PATCH 0.1.0] VERIFY-PASS
[J129-PATCH 0.1.0] INSTALL-PASS
```

La advertencia Apache `AH00558` sobre ServerName, si ya existía y `Syntax OK` se mantiene, no fue bloqueante en LAB. No cambiar ServerName como parte de esta release.

## 6. Verify independiente

Ejecutar nuevamente:

```bash
sudo ./install.sh verify
```

Debe terminar:

```text
[J129-PATCH 0.1.0] VERIFY-PASS
```

Verificar también:

```bash
apachectl -t
```

Esperado:

```text
Syntax OK
```

## 7. Prueba funcional controlada

Después de verificar instalación:

1. Abrir Endpoint Configurator.
2. Ejecutar Discovery/Rescan sobre un J129 autorizado.
3. Confirmar fabricante `Avaya` y modelo `J129`.
4. Asignar una sola cuenta mediante Accounts estándar de Issabel.
5. Apply.
6. Confirmar que Issabel genera el provisioning desde las plantillas instaladas.
7. Validar acceso HTTP a los archivos de provisioning necesarios.
8. Reiniciar/provisionar el teléfono únicamente durante una ventana controlada si hace falta aplicar configuración física.
9. Confirmar registro SIP en Asterisk; Asterisk es la fuente autoritativa, no el campo stale `Registered at` de la GUI.
10. Realizar llamada entrante y saliente de prueba según la política de la central.

No afirmar éxito físico solo porque `verify` del servidor pasó.

## 8. Criterios de éxito

Producción puede considerarse exitosa únicamente si:

```text
preflight PASS
install PASS
verify PASS
Apache Syntax OK
Discovery identifica Avaya/J129
una cuenta SIP asignada por flujo estándar
provisioning HTTP correcto
J129 registra en Asterisk
prueba de llamada satisfactoria
```

## 9. Rollback

Si falla un criterio crítico antes de declarar éxito:

```bash
sudo ./install.sh rollback
```

Esperado:

```text
[J129-PATCH 0.1.0] ROLLBACK-PASS
```

Después confirmar:

```bash
apachectl -t
```

y revisar que los archivos/valores DB previos hayan sido restaurados.

Si el servidor presenta un problema fuera del alcance del rollback del instalador, utilizar el snapshot/backup externo.

## 10. Cambios explícitamente fuera de v0.1.0

No mezclar durante esta instalación:

- firmware 4.x;
- XML de idioma español;
- parámetros experimentales de menú local;
- multicuenta;
- cambio de contraseña Web Admin;
- nuevas capacidades de polling/reload;
- correcciones de identidad SIP persistente local.

Cualquier cambio anterior requiere una release posterior y su propia validación.

## 11. Evidencia de cierre por central

Registrar al finalizar:

```text
central:
fecha/hora:
operador:
release SHA: 74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
manifest SHA256 verificado: SI/NO
snapshot/backup: SI/NO
preflight: PASS/FAIL
install: PASS/FAIL
verify: PASS/FAIL
J129 probado:
cuenta/extensión probada:
registro Asterisk: PASS/FAIL
llamada entrante: PASS/FAIL
llamada saliente: PASS/FAIL
rollback ejecutado: SI/NO
observaciones:
```

No incluir contraseñas ni secretos en esta evidencia.
