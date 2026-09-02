# Runner GitHub dedicado para validación J129 en producción

## Objetivo

Instalar un self-hosted runner dedicado en `cei-pbx02.lamundial.hn` para ejecutar y documentar las pruebas controladas de Avaya J129 v0.1.0 en producción.

El runner no sustituye los controles de cambio ni autoriza acciones mutantes por sí mismo.

## Identidad y etiquetas

Host inicial:

```text
cei-pbx02.lamundial.hn
```

Etiquetas propuestas:

```text
self-hosted
linux
x64
j129-production
cei-pbx02
```

Los workflows de producción deberán seleccionar explícitamente `j129-production` y `cei-pbx02` para impedir que se ejecuten accidentalmente en el runner LAB u otro host.

## Seguridad

- No ejecutar el runner como `root`.
- Usuario dedicado: `github-runner-prod`.
- Directorio recomendado: `/opt/actions-runner-prod`.
- No otorgar `NOPASSWD: ALL`.
- No exponer `/etc/amportal.conf`, secretos SIP, Web Admin, tokens de registro ni credenciales MySQL en logs/artifacts.
- Cualquier operación privilegiada futura deberá usar un helper específico con comandos y parámetros restringidos.
- Los workflows read-only no deberán modificar DB, reiniciar teléfonos, recargar servicios ni ejecutar `install.sh install`/`rollback`.
- Los workflows mutantes deberán requerir `workflow_dispatch` y un valor de confirmación explícito.

## Alcance inicial

Primer workflow de producción después de registrar el runner:

1. Guard de hostname/labels.
2. Inventario de OS/Asterisk/Python/Apache.
3. Verificación de archivos v0.1.0 instalados.
4. `apachectl -t` si el usuario tiene permisos suficientes o mediante helper read-only restringido.
5. Verificación de provisioning global y por MAC sin imprimir contenido sensible.
6. HTTP HEAD a `J100Supgrade.txt`, `46xxsettings.txt` y archivo por MAC.
7. Estado SIP de una extensión de prueba sin mostrar secretos.
8. Artifact de evidencia sanitizada.

## Acciones mutantes

No se habilitan inicialmente. Reinicio de teléfono, Apply, instalación, rollback o cambios de DB se mantienen manuales hasta validar el runner y el workflow read-only.

## Contexto de v0.1.0

La release congelada sigue siendo:

```text
74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

La instalación de servidor en `cei-pbx02` ya pasó audit, SHA256, preflight, install, verify y Apache Syntax OK. La prueba funcional física continúa pendiente.

## Hallazgo separado para v0.2.0

El discovery de endpoints en VLAN enrutada queda fuera de v0.1.0 y está planificado para Sprint 1 de v0.2.0. El runner de producción podrá usarse más adelante para pruebas read-only de ese desarrollo, pero no se modificará el core de Issabel en producción durante esta fase.
