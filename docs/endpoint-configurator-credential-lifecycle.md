# Endpoint Configurator — ciclo de credenciales administrativas

Estado: diseño aprobado para implementación en LAB  
Rama de trabajo: `Audit`  
Fecha: 2026-09-12

## Objetivo

Permitir que cada central telefónica defina una contraseña administrativa final
para sus teléfonos, con un override opcional por endpoint identificado por MAC.
La contraseña inicial de fábrica continúa siendo individual por teléfono y solo
se utiliza para el primer acceso autenticado.

Este diseño no modifica la semántica de **Batch of Extensions**. Las extensiones
pertenecen a Asterisk; las credenciales administrativas pertenecen al endpoint.

## Precedencia

```text
override del endpoint/MAC
        ↓ si no existe
contraseña global de la PBX
        ↓ solo como diagnóstico explícito
credencial inicial/fábrica del endpoint
```

La credencial inicial no debe convertirse automáticamente en contraseña final.

## Menú

Agregar una sección **Endpoint Configurator → Seguridad administrativa** con:

- contraseña global de la PBX;
- confirmación y reemplazo controlado;
- versión activa y fecha de rotación;
- cantidad de endpoints pendientes/verificados;
- inicio de rotación por lote;
- historial de eventos sin valores secretos.

Guardar una contraseña nueva no debe cambiar teléfonos inmediatamente. Debe crear
una rotación pendiente y exigir confirmación del lote.

## Override por endpoint

En el detalle del endpoint:

- checkbox «Sobrescribir contraseña global»;
- contraseña específica;
- confirmación;
- estado de validación;
- versión aplicada.

Un endpoint con override no cambia cuando se rota la contraseña global, salvo que
el operador seleccione explícitamente incluir overrides.

## Modelo lógico mínimo

```text
pbx_admin_password_policy
- id
- pbx_identity
- active_version
- ciphertext
- key_reference
- created_at
- rotated_at
- status

endpoint_admin_credential
- id_endpoint
- source: GLOBAL | OVERRIDE | FACTORY
- ciphertext
- key_reference
- version
- validation_status
- last_validated_at
- rotation_status
- updated_at

endpoint_credential_event
- id_endpoint
- operation
- result
- actor
- created_at
- correlation_id
```

Los nombres son conceptuales y deben adaptarse al esquema de Issabel antes de
crear migraciones.

## Reglas de seguridad

- Nunca guardar contraseñas en texto plano.
- Nunca imprimirlas en logs, reportes, artefactos o respuestas JSON.
- La clave de cifrado debe vivir fuera de la base de datos.
- Las pantallas solo muestran estado, versión y fecha; nunca el valor.
- La importación CSV debe cifrar cada fila y eliminar el archivo después del
  procesamiento.
- La MAC es la identidad primaria; la IP solo sirve para localizar el equipo.
- La rotación conserva la credencial anterior hasta verificar la nueva.
- Un fallo de un endpoint no debe detener ni marcar como exitoso el lote completo.
- La contraseña SIP y la contraseña Web Admin son secretos distintos.

## Flujo de rotación

1. Validar la credencial actual.
2. Crear versión nueva en estado pendiente.
3. Probar primero un endpoint canario.
4. Aplicar la nueva contraseña.
5. Esperar el reinicio si el modelo lo requiere.
6. Validar login con la nueva contraseña.
7. Marcar el endpoint como verificado.
8. Continuar con el lote.
9. Retirar la versión anterior solo al cerrar el lote.

## Vista de endpoints

La tabla debe añadir:

- extensiones asociadas;
- estado de registro por extensión;
- IP/contacto observado;
- política de contraseña: global u override;
- versión aplicada;
- estado de rotación.

Asterisk es la fuente autoritativa del registro SIP. El estado no debe
permanecer como un dato histórico que suplante una consulta actual.

## Fases de implementación

1. Definir almacenamiento cifrado y migración reversible.
2. Añadir menú global por PBX.
3. Añadir override por MAC.
4. Añadir importación masiva segura.
5. Añadir extensiones y registro SIP en la tabla principal.
6. Implementar rotación controlada y rollback.
7. Validar con GRP2601P, GXP1625 y GXP1630 en LAB.
8. Preparar revisión para producción.

## Criterio de aceptación inicial

No se habilita Configure para un modelo que requiere autenticación Web si:

- no existe credencial inicial o global aplicable;
- la credencial no fue validada;
- el endpoint tiene conflicto de MAC/IP;
- la rotación anterior quedó pendiente o fallida.

