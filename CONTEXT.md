# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo actual para poder retomar el proyecto sin reconstruir la historia desde cero. No contiene secretos reales.

## Objetivo actual

Cerrar una primera distribución `v0.1.0` que habilite Avaya J129 en Issabel 5 usando el Endpoint Configurator estándar y sin modificar el core de Issabel.

Prioridad inmediata: validar el paquete exacto de release en el LAB y después preparar instalación controlada en una central de producción.

## Estado funcional confirmado

- Discovery identifica el J129 como Avaya/J129.
- El flujo estándar Accounts de Issabel asigna la extensión.
- El vendor usa `_accounts` entregadas por Issabel; no debe consultar secretos directamente desde DB.
- Provisioning funcional:

```text
J100Supgrade.txt
-> 46xxsettings.txt
-> <mac>.txt
-> registro SIP
```

- J129 físico registra cuenta `200` por `chan_sip`.
- Rescan es idempotente.
- v1 soporta una sola cuenta SIP.
- `check-sync` reinicia físicamente el J129 3.0.0.0.20 y luego reprovisiona/re-registra.
- NTP generado por Issabel fue consumido tras reinicio y corrigió la hora física del teléfono.

## LAB

```text
Issabel:    5
OS:         Rocky Linux 8
Asterisk:   18.19.0
Python:     3.6.8
PBX:        192.168.1.10
J129:       192.168.1.168
MAC:        C8:1F:EA:9B:65:0D
Firmware:   3.0.0.0.20
Endpoint:   id 3
SIP:        200
Runner:     github-runner / self-hosted
```

`192.168.1.169` está ocupado por otro dispositivo y no debe usarse para la PBX.

## Ramas

### `main`

Referencia/histórico y workflow definitions visibles en GitHub Actions. Evitar pruebas mutantes.

### `Audit`

Harness de laboratorio, auditorías, helpers, documentación y workflows de validación.

### `release/j129-v0.1.0`

Rama limpia del paquete de distribución. No debe absorber todo `Audit`.

## Arquitectura de release

Payload esperado:

```text
release/j129-v0.1.0/
├── install.sh
├── README.md
└── payload/
    ├── etc/httpd/conf.d/avaya-j129-provisioning.conf
    └── usr/share/issabel/endpoint-classes/
        ├── class/issabel/vendor/Avaya.py
        └── tpl/
            ├── Avaya_J129.tpl
            └── Avaya_global_SIP.tpl
```

No incluir copias estáticas operativas de `46xxsettings.txt` ni archivos históricos de teléfonos en el payload.

## Referencias históricas

El repositorio contiene un archivo llamado `46xxsettings.txt funciona Choloma.txt` que corresponde a una configuración conocida como funcional. No se necesita para instalar v0.1.0.

Si se conserva, debe tratarse solo como evidencia y renombrarse a algo explícito, por ejemplo:

```text
examples/j129-working-reference-choloma.txt
```

Antes de moverlo a `examples/`, revisar que no contenga credenciales o material sensible.

El `46xxsettings.txt` operativo debe ser generado por Issabel desde la plantilla, no copiado desde un ejemplo.

## Workflows relevantes

### 07 — Rescan Idempotency
PASS.

### 08 — Single Account V1
PASS.

### 09 — Remote Restart
PASS físico. `check-sync` implica reboot en este firmware.

### 10 — NTP / Forced Provisioning
PASS server-side. La hora quedó físicamente correcta después de un reinicio posterior.

### 11 — Phone UX & Admin
Apply server-side generó parámetros de menú/nombre. La hora sí cambió después del reinicio, pero el menú visible no apareció. No incluir UX experimental en v0.1.0.

### 12 — Production Patch | Install & Rollback Test
VERDE.

Ciclo validado:

```text
preflight -> install -> verify -> install -> verify -> rollback
```

### 13 — Release Package | Smoke Test
ROJO, pero todavía por infraestructura del runner, no por un fallo demostrado del paquete.

Error vigente:

```text
EACCES: permission denied, unlink
.../vendor/__pycache__/Avaya.cpython-36.pyc
```

## Causa del fallo workflow 13

El self-hosted runner ejecuta checkout como `github-runner`. Una tarea privilegiada anterior generó archivos `.pyc` propiedad de `root` dentro del workspace. `actions/checkout` intenta limpiar el árbol antes de ejecutar steps y no puede eliminar esos archivos.

Esto significa que agregar un step de cleanup después del checkout no resuelve el primer fallo: el job no llega hasta ese step.

## Decisión de corrección

Hacer una limpieza puntual del residuo root-owned fuera del checkout que falla y después cambiar el diseño para impedir que vuelva a ocurrir.

Reglas futuras:

```text
PYTHONDONTWRITEBYTECODE=1
python3 -B ... cuando se ejecute Python privilegiado
no crear temporales root dentro de $GITHUB_WORKSPACE
usar /tmp o /var/lib/... para estado privilegiado
no chmod 777
no sudo amplio
```

Agregar comprobaciones de ownership/residuos antes y después de las operaciones privilegiadas siempre que el flujo permita llegar a esos steps.

## Alcance de v0.1.0

Incluido:

- Avaya J129 en Endpoint Configurator estándar;
- OUI/modelo J129;
- una cuenta SIP;
- generación de provisioning;
- Apache provisioning;
- installer con preflight/install/verify/rollback;
- idempotencia.

Excluido:

- firmware upgrade;
- español;
- menú local experimental;
- cambio automático de Web Admin password;
- polling/update sin reboot;
- solución definitiva a identidad SIP persistente después de retirar la última cuenta.

## Bugs y deuda

- `BUG-EC-001`: Registered at de GUI puede estar stale.
- `BUG-J129-002`: multicuenta no soportada en v1.
- `BUG-J129-004`: identidad SIP puede persistir localmente aunque desaparezca el provisioning por MAC.
- detector HTTP del workflow 11 requiere observabilidad autorizada.
- chronyd debe recuperar sync de forma afirmada después de restart.
- menú local no resuelto.
- español requiere XML oficial Avaya.
- helpers LAB todavía tienen runtime patching/hardcodes históricos.
- runner puede quedar contaminado por archivos root-owned; debe corregirse estructuralmente.

## Seguridad

- No imprimir SIP passwords.
- No imprimir Web Admin password, cookies, nonce, XToken ni hashes.
- La credencial Web Admin expuesta anteriormente debe rotarse antes de producción.
- No subir Phone Reports brutos.
- Mantener sudo mínimo y helper restringido.

## Próxima secuencia

```text
1. limpiar residuo root-owned del runner
2. impedir creación futura de __pycache__ root en workspace
3. nuevo run 13 en Audit / TEST-RELEASE
4. verificar ciclo real release: preflight/install/verify/install/verify/rollback
5. congelar v0.1.0 + SHA256
6. auditar central producción
7. backup/snapshot
8. preflight producción
9. install
10. verify
11. discovery + asignación account + Apply
12. validar HTTP provisioning + SIP
13. rollback si cualquier criterio crítico falla
```

## Regla de handoff

Antes de tocar implementación, leer:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `docs/j129-lab-validation.md`
4. `docs/j129-research-notes.md`
5. `docs/agent-log.md`
6. README de la release si el trabajo es de distribución

El objetivo inmediato no es seguir agregando funciones al teléfono: es cerrar de forma segura y reproducible la v0.1.0 mínima para producción.
