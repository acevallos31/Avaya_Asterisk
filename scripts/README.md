# Scripts operativos

Esta carpeta concentra automatizaciones repetibles para preparar servidores Issabel/PBX y runners del proyecto sin depender de copiar comandos manualmente.

## Reglas

- Ejecutar como `root` salvo que el script indique lo contrario.
- No almacenar tokens, contraseñas SIP ni credenciales en archivos o commits.
- Los scripts deben ser idempotentes cuando sea razonable.
- Producción y LAB deben mantener runners y labels separados.
- Revisar el contenido antes de ejecutar desde `curl` en producción.

## Scripts disponibles

### `install-j129-prod-call-helper.sh`

Instala/actualiza el helper restringido usado por la prueba 47 y su regla sudoers. Descarga los dos archivos desde la rama `Audit`, valida sintaxis Bash y `visudo`, instala permisos correctos y muestra el estado final.

Uso desde un checkout del repositorio:

```bash
bash scripts/install-j129-prod-call-helper.sh
```

Uso directo desde la PBX:

```bash
curl -fsSL https://raw.githubusercontent.com/acevallos31/Avaya_Asterisk/Audit/scripts/install-j129-prod-call-helper.sh | bash
```

### `install-production-runner.sh`

Instala un GitHub Actions self-hosted runner dedicado a producción para este repositorio. Está diseñado para `cei-pbx02` y usa:

```text
usuario: github-runner-prod
directorio: /opt/actions-runner-prod
runner: <hostname>-j129-production
labels: j129-production,cei-pbx02
repo: acevallos31/Avaya_Asterisk
```

El único dato interactivo solicitado es el token temporal de registro del runner. El token se lee sin eco y no se guarda en archivos por el script.

```bash
bash scripts/install-production-runner.sh
```

> El token de registro se obtiene en GitHub: Settings -> Actions -> Runners -> New self-hosted runner. Es temporal; nunca debe quedar en documentación, historial o commits.
