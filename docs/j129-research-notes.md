# Investigación técnica — Avaya J129 / Open SIP

Actualizado: 2026-09-02

Este documento separa documentación oficial, evidencia propia del LAB e hipótesis pendientes. No contiene secretos reales.

## Firmware LAB

- J129 físico: `3.0.0.0.20`.
- Firmware oficial más reciente investigado: J100 SIP `4.1.11.0`, mayo de 2026.
- Binario J129 documentado: `FW_S_J129_R4_1_11_0_10.bin`.

No realizar upgrade todavía. Firmware queda fuera de v0.1.0.

## Open SIP / Asterisk

El LAB usa Asterisk 18.19.0. La interoperabilidad observada es evidencia propia del proyecto.

Valores Open SIP relevantes:

```text
SET ENABLE_AVAYA_ENVIRONMENT 0
SET DISCOVER_AVAYA_ENVIRONMENT 0
SET ENABLE_3PCC_ENVIRONMENT 1
```

## Provisioning y firmware

La PBX puede servir:

```text
J100Supgrade.txt
46xxsettings.txt
<mac>.txt
FW_S_J129_*.bin
Mlf_J129_*.xml
```

Provisioning normal y firmware upgrade deben permanecer separados.

`46xxsettings.txt` no debe distribuirse como archivo estático de producción. Debe generarse desde `Avaya_global_SIP.tpl` mediante el flujo normal de Issabel.

El archivo histórico `46xxsettings.txt funciona Choloma.txt` representa una configuración conocida funcional. Es útil como evidencia comparativa, pero no como payload. Si se conserva, debe revisarse por secretos y renombrarse/moverse como ejemplo no instalable.

## check-sync / actualización remota

Evidencia física del workflow 09:

```text
check-sync -> reinicio físico -> nueva descarga de provisioning -> nuevo registro SIP
```

No usar `check-sync` para un requisito de actualización sin reboot.

## NTP / hora

Configuración probada:

```text
SET SNTPSRVR 192.168.1.10
SET SNTP_SYNC_INTERVAL 60
SET GMTOFFSET -6:00
SET DAYLIGHT_SAVING_SETTING_MODE 0
```

Workflow 10 validó generación server-side sin caída SIP. El teléfono no hizo polling natural durante 300 s.

En una prueba posterior con reinicio, la hora física del J129 quedó correcta. Esto confirma que esos parámetros funcionan cuando el teléfono consume el provisioning.

Deuda: al reiniciar chronyd, esperar explícitamente la recuperación de sync.

## Idioma español

Avaya distribuye recursos específicos J129:

```text
Mlf_J129_CastilianSpanish.xml
Mlf_J129_LatinAmericanSpanish.xml
```

Para Honduras, el candidato es Latin American Spanish. No incluir en v0.1.0 sin recurso oficial y validación física.

## Admin menu

Investigación oficial registrada:

```text
PROCSTAT 0 -> Admin menu permitido
PROCSTAT 1 -> Admin menu restringido/no permitido
```

Workflow 11 llegó a generar:

```text
SET PROCSTAT 0
SET PROVIDE_OPTIONS_SCREEN 1
SET PROVIDE_NETWORKINFO_SCREEN 1
SET PROVIDE_LOGOUT 1
SET ENTRYNAME Briam
```

Tras reinicio, el menú visible no apareció. Por tanto, no atribuir a esos parámetros la creación de una softkey/menu visible en J129 3.0.0.0.20 sin evidencia adicional.

Esta investigación no bloquea la release mínima.

## Web Admin

La Web UI responde por HTTP y HTTPS. La credencial usada anteriormente debe considerarse comprometida/expuesta y rotarse antes de producción.

No incluir gestión automática del password Web Admin en v0.1.0.

## BUG-J129-004 — identidad SIP persistente

Eliminar el archivo por MAC server-side no garantiza logout local. Una identidad SIP persistida puede sobrevivir y volver a registrar después de reboot.

No resolver con valores vacíos o comandos inventados. Fuera del alcance v0.1.0 salvo documentación de la limitación.

## Esquema Endpoint Configurator

El LAB usa MySQL/MariaDB `endpointconfig`. No usar SQLite ni asumir columnas. Reutilizar consultas validadas o auditar esquema primero.

## Producción patch vs release package

### Workflow 12

El candidato de parche dentro de la estructura de Audit completó:

```text
preflight -> install -> verify -> install -> verify -> rollback
```

Estado: PASS.

Esto demuestra idempotencia y rollback del candidato, pero todavía no es evidencia de que el artefacto autocontenido exacto de distribución haya pasado.

### Workflow 13

Objetivo: probar exactamente `release/j129-v0.1.0`.

Estado actual: bloqueado por infraestructura del self-hosted runner.

Error observado:

```text
EACCES: permission denied, unlink
.../vendor/__pycache__/Avaya.cpython-36.pyc
```

El fallo ocurre durante `actions/checkout`, antes del ciclo del installer. No clasificarlo como fallo funcional de release.

## Investigación del ownership del runner

Causa:

1. runner self-hosted ejecuta el checkout como `github-runner`;
2. un proceso anterior ejecutado con root generó `.pyc` dentro del checkout;
3. el archivo quedó propiedad de root;
4. el siguiente checkout intenta limpiar ese árbol;
5. `github-runner` no puede hacer unlink y el job termina antes de los steps.

Punto importante: un cleanup step colocado después de `actions/checkout` no puede reparar un archivo que impide que ese checkout termine.

Diseño preventivo recomendado:

```text
PYTHONDONTWRITEBYTECODE=1
python3 -B ... para Python ejecutado con privilegios
no generar temporales en $GITHUB_WORKSPACE cuando se ejecuta como root
usar /tmp o /var/lib/... para estado de root
no chmod 777
no ampliar sudo
```

Conviene auditar ownership y `__pycache__` antes/después de operaciones privilegiadas cuando el workflow ya tenga un checkout funcional.

## Rama de release

`release/j129-v0.1.0` debe mantenerse limpia y separada de `Audit`.

No hacer merge masivo de Audit. La release solo necesita installer, payload, documentación, checksums y eventualmente ejemplos sanitizados claramente fuera del payload.

## Fuentes oficiales principales

- Avaya J100 Series SIP Release 4.1.11.0 Readme — https://support.avaya.com/css/en/public/documents/101095479
- Installing and Administering Avaya J100 Series SIP IP Phones in Open SIP — https://support.avaya.com/css/public/documents/101053965
- Installing and Administering Avaya J129 IP Phone in third-party call control setup — https://support.avaya.com/css/public/documents/101037009
- Installing and Administering Avaya J129 IP Phone — https://support.avaya.com/css/public/documents/101033171
- IP Office SIP Telephone Installation Notes — https://support.avaya.com/css/public/documents/101091571

## Próxima investigación/prueba

La prioridad ya no es agregar funciones UX al teléfono. La secuencia es:

1. reparar ownership/residuo root del runner;
2. impedir nuevos `.pyc` root-owned;
3. ejecutar workflow 13 hasta llegar al installer real;
4. validar release exacta;
5. congelar checksums;
6. auditar central de producción;
7. dejar español, menú, Web Admin central y firmware para fases posteriores.
