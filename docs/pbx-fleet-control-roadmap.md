# PBX Fleet Control — Roadmap

Estado: idea/arquitectura futura. No desplazar el objetivo inmediato: terminar de optimizar y estabilizar Endpoint Configurator.

## Visión

Construir un servidor local de distribución y control para administrar múltiples PBX Issabel de la red con una experiencia parecida a GitHub Actions, pero operada dentro de la infraestructura propia.

Objetivos futuros:

- mantener todas las PBX en una misma versión/base aprobada;
- distribuir paquetes, overlays, templates y scripts versionados;
- ejecutar diagnósticos remotos controlados;
- hacer preflight, deploy, verify y rollback por PBX;
- inventariar versiones de Issabel, Asterisk, OS y componentes;
- conservar evidencia de cada cambio y diagnóstico;
- preparar nuevas implementaciones de PBX desde un baseline conocido;
- evitar acceso root genérico: usar agentes/helpers allowlisted y auditables.

## Principio de diseño

El repositorio sigue siendo la fuente de verdad de código, scripts y releases. El futuro servidor local será el orquestador/distribuidor, no un lugar para editar manualmente configuraciones sin trazabilidad.

Flujo conceptual:

```text
Git / release aprobada
        |
        v
PBX Fleet Controller
        |
        +--> PBX A -> preflight -> deploy -> verify
        +--> PBX B -> preflight -> deploy -> verify
        +--> PBX C -> diagnóstico read-only
        +--> PBX nueva -> bootstrap -> baseline -> verify
```

## Componentes previstos

### Controller

Servidor central local con:

- inventario de PBX y roles;
- repositorio/cache de releases aprobadas;
- scheduler/orquestador de jobs;
- dashboard de estado;
- historial de runs;
- control de concurrencia y ventanas de mantenimiento;
- RBAC y auditoría.

### Agent por PBX

Agente ligero o runner dedicado por PBX que:

- solo acepte jobs firmados/autorizados;
- no exponga shell root genérico;
- ejecute helpers versionados y allowlisted;
- reporte versión, hashes, salud y resultado;
- soporte rollback controlado.

### Catálogo de scripts

La carpeta `scripts/` crecerá más allá de pruebas y debe separar claramente:

```text
scripts/bootstrap/     instalación inicial de runners/agentes
scripts/deploy/        instalación/actualización de paquetes
scripts/diagnostics/   inventario y diagnóstico read-only
scripts/maintenance/   backup, restore, limpieza, checks
scripts/security/      revisión de sudoers, permisos, runners y hardening
scripts/testing/       utilidades exclusivas de LAB/pruebas
```

No es obligatorio reorganizar inmediatamente los scripts existentes; esta estructura es el destino recomendado a medida que aumente el catálogo.

## Fases propuestas

### Fase 0 — ahora

Terminar Endpoint Configurator/J129 y convertir procedimientos manuales repetitivos en scripts seguros e idempotentes.

### Fase 1 — bootstrap e inventario

- instalador de runner/agente que solo solicite token/credencial temporal;
- script de inventario de PBX;
- healthcheck común;
- manifest de versión por PBX;
- backup previo a cambios.

### Fase 2 — distribución versionada

- publicar una release aprobada;
- preflight remoto;
- instalar solo si hashes/versión esperada coinciden;
- verify posterior;
- rollback automático o asistido.

### Fase 3 — diagnóstico centralizado

- ejecutar checks read-only por grupos de PBX;
- comparar drift de configuración/versiones;
- detectar PBX fuera de baseline;
- exportar evidencia y reportes.

### Fase 4 — aprovisionamiento de PBX nuevas

- bootstrap de OS/PBX compatible;
- instalar runner/agente;
- aplicar baseline;
- instalar componentes aprobados;
- validar servicios, telefonía y seguridad.

## Seguridad

- Nunca almacenar SIP secrets, tokens de registro ni claves privadas en el repositorio.
- Preferir credenciales temporales y secretos gestionados fuera de Git.
- Toda acción mutante debe tener preflight, confirmación explícita, verify y rollback definido.
- Producción y LAB deben seguir separados por identidad/labels/policies.
- Los helpers privilegiados deben ser root-owned, mínimos, con argumentos validados y sin posibilidad de shell arbitrario.
- El controller no debe convertirse en una vía de root remoto universal.

## Prioridad actual

Este roadmap queda documentado para no perder la dirección futura, pero el trabajo inmediato continúa siendo:

```text
optimizar Endpoint Configurator
-> cerrar deuda de v0.1.0
-> trabajar mejoras v0.2.0
-> consolidar scripts reutilizables
-> luego diseñar/prototipar PBX Fleet Controller
```
