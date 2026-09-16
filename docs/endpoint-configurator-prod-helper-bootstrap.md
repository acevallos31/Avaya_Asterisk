# Test 71 — bootstrap único del helper productivo

Este paso se ejecuta **una sola vez** como `root` en `cei-pbx02` antes del primer
run de Test 71. No instala todavía el runtime de credenciales, no modifica la DB
y no contacta teléfonos. Solo instala el helper root-owned y su allowlist sudo
restringida.

## Artefactos congelados

```text
candidate commit: ef176c99935af5f833248358c4daf7b4ca0dde6a
helper git blob:  3c16593a0f2490e00ad912838ec32eed2b35e26a
sudoers git blob: d82b28e335802034df4c11dae2780e164c823ab3
```

## Comandos en cei-pbx02

Ejecutar como `root`:

```bash
set -euo pipefail
umask 077

COMMIT='ef176c99935af5f833248358c4daf7b4ca0dde6a'
TMP="$(mktemp -d /root/test71-bootstrap.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "https://raw.githubusercontent.com/acevallos31/Avaya_Asterisk/${COMMIT}/deploy/endpoint-configurator/bin/endpoint-credential-prod-deploy" \
  -o "$TMP/helper"
curl -fsSL "https://raw.githubusercontent.com/acevallos31/Avaya_Asterisk/${COMMIT}/deploy/endpoint-configurator/sudoers/issabel-endpoint-credential-prod" \
  -o "$TMP/sudoers"

python3 - "$TMP/helper" '3c16593a0f2490e00ad912838ec32eed2b35e26a' \
                 "$TMP/sudoers" 'd82b28e335802034df4c11dae2780e164c823ab3' <<'PY'
import hashlib
import pathlib
import sys
for path, expected in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):
    data = pathlib.Path(path).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if actual != expected:
        raise SystemExit("BLOB MISMATCH %s expected=%s actual=%s" % (path, expected, actual))
    print("BLOB-PASS %s %s" % (path, actual))
PY

bash -n "$TMP/helper"
visudo -cf "$TMP/sudoers"

install -o root -g root -m 0755 "$TMP/helper" /usr/local/sbin/issabel-endpoint-credential-prod
install -o root -g root -m 0440 "$TMP/sudoers" /etc/sudoers.d/issabel-endpoint-credential-prod
visudo -cf /etc/sudoers.d/issabel-endpoint-credential-prod

stat -c '%U:%G:%a %n' /usr/local/sbin/issabel-endpoint-credential-prod /etc/sudoers.d/issabel-endpoint-credential-prod
sudo -u github-runner-prod sudo -n -l | grep -F '/usr/local/sbin/issabel-endpoint-credential-prod'
```

Resultado esperado:

```text
root:root:755 /usr/local/sbin/issabel-endpoint-credential-prod
root:root:440 /etc/sudoers.d/issabel-endpoint-credential-prod
```

El helper **no se autoactualiza** desde el checkout del runner. Una versión
posterior exige otro bootstrap explícito con blobs nuevos y revisión previa.

## Después del bootstrap

Ejecutar desde GitHub Actions:

```text
71 | Ceiba Production | Endpoint Credentials | Controlled Runtime Install
```

sobre `main`, con confirmación exacta:

```text
INSTALL-ENDPOINT-CREDENTIALS-PROD
```

El workflow vuelve a comprobar el helper root-owned, el payload pinneado, el
baseline productivo, Apache/HTTPS, el esquema y los grants DDL limitados antes
de instalar. El rollback automático ante fallo restaura solo el runtime; no
elimina la clave ni las tablas.
