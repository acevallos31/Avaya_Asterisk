# Investigación técnica — Avaya J129 / Open SIP

Fecha de investigación: 2026-09-01

Este documento reúne hallazgos de documentación oficial Avaya y separa hechos confirmados, hipótesis y pruebas pendientes. No contiene secretos reales.

## 1. Firmware actual del teléfono de laboratorio

El J129 físico usado en las pruebas reporta firmware `3.0.0.0.20`.

Este firmware es significativamente anterior a la rama actual J100 SIP 4.1.x. No debe actualizarse todavía sin snapshot/plan de recuperación y sin verificar el hardware exacto del teléfono.

## 2. Firmware vigente encontrado

Avaya publicó en mayo de 2026 J100 SIP Release `4.1.11.0`; el paquete documentado contiene para J129:

```text
FW_S_J129_R4_1_11_0_10.bin
```

El Readme oficial indica que J100 SIP 4.1.11.0 soporta J129 y Open SIP, incluyendo Asterisk R16 como plataforma compatible, y que esta versión reemplaza releases anteriores.

Fuente oficial:
- Avaya J100 Series SIP Release 4.1.11.0 Readme, mayo 2026: https://support.avaya.com/css/en/public/documents/101095479

Versiones intermedias relevantes encontradas durante la investigación:

```text
3.0.0.0.20      firmware actual del J129 LAB
4.0.6.1         release con lista pública de issues Open SIP
4.0.11.0        documentación de parámetros Open SIP y SIP controller
4.0.12.1        paquete completo J129 con binario y archivos de idiomas
4.1.2.1         documentación explícita de despliegue Open SIP
4.1.5.0         compatibilidad explícita con Asterisk R16
4.1.11.0        release vigente investigado, mayo 2026
```

No asumir que un salto directo 3.0.0.0.20 -> 4.1.11.0 es seguro hasta revisar advisements, hardware revision y reglas de upgrade/downgrade.

## 3. Viabilidad de usar la PBX como servidor de firmware

**Conclusión preliminar: técnicamente viable.**

Avaya define el provisioning server como un servidor HTTP/HTTPS que aloja firmware, `J100Supgrade.txt`, settings, archivos por MAC y recursos como idiomas. La documentación de IP Office también confirma que cuando se usa un servidor de archivos separado, se copian al servidor `J100Supgrade.txt`, binarios `.bin` y archivos `.xml`.

El J129 ya descarga provisioning desde Apache en la PBX LAB, por lo que la misma infraestructura puede servir firmware. Sin embargo, esto debe implementarse como una capacidad separada y controlada.

Archivos típicos:

```text
J100Supgrade.txt
FW_S_J129_R<version>.bin
Mlf_J129_*.xml
46xxsettings.txt
<mac>.txt
```

Fuentes oficiales:
- Installing and Administering Avaya J100 Series SIP IP Phones in Open SIP: https://support.avaya.com/css/public/documents/101053965
- IP Office SIP Telephone Installation Notes: https://support.avaya.com/css/public/documents/101091571
- J100 SIP 4.1.11.0 Readme: https://support.avaya.com/css/en/public/documents/101095479

### Regla de seguridad para firmware

No reutilizar el `J100Supgrade.txt` histórico del repositorio para producción sin revisar el paquete oficial completo. El archivo de upgrade controla qué binario se descarga y una configuración incorrecta puede forzar upgrades no deseados.

Para la primera versión se recomienda mantener provisioning y firmware como responsabilidades separadas:

- provisioning normal puede continuar usando el bootstrap seguro sin `APPNAME`;
- firmware upgrade debe activarse solo mediante un workflow/procedimiento explícito;
- conservar el paquete oficial completo y hashes;
- verificar espacio, permisos y HTTP 200 antes de habilitar upgrade;
- registrar versión anterior/nueva por MAC;
- prohibir downgrade automático.

## 4. Open SIP / Asterisk

El Readme 4.1.11.0 lista oficialmente Open SIP con:

- BroadSoft BroadWorks R22.0;
- Asterisk R16;
- FreeSWITCH 1.8.5;
- Netsapiens v41.2.2;
- Metaswitch CFS V9.5.

El LAB usa Asterisk 18.19.0. La compatibilidad específica con Asterisk 18 no aparece explícitamente en el Readme encontrado; por tanto, nuestro J129 físico + Asterisk 18 sigue siendo evidencia propia del proyecto, no una certificación oficial de Avaya.

Para Open SIP, Avaya documenta estos valores:

```text
SET ENABLE_AVAYA_ENVIRONMENT 0
SET DISCOVER_AVAYA_ENVIRONMENT 0
SET ENABLE_IPOFFICE 0
```

Deben evaluarse como parte del template objetivo para evitar autodetección de entornos Avaya cuando el teléfono se usa con Issabel/Asterisk.

Fuente: J100 SIP 4.1.2.1 Readme y 4.1.11.0 Readme.

## 5. Bugs / limitaciones relevantes encontrados

### Open SIP — HTTP redirect a HTTPS

Issue `SIP96X1-41164`: una redirección HTTP -> HTTPS puede fallar por validación de certificado. Workaround documentado: configurar directamente la URL HTTPS.

Este issue todavía aparece como no resuelto en el Readme 4.1.11.0.

### Open SIP — TRUSTCERTS con HTTPS

Issue `SIP96X1-89301`: el teléfono puede no descargar la lista `TRUSTCERTS` cuando el usuario define una URL HTTPS y `ENABLE_PUBLIC_CA_CERTS=1`. Workaround: usar HTTP o `ENABLE_PUBLIC_CA_CERTS=0` según el escenario.

### Open SIP — Netsapiens mode

Issue `SIP96X1-66640`: no usar el modo Netsapiens del Web UI aunque aparezca; usar Generic.

### J129 / 3PCC antiguo

J100 SIP 4.0.0.0 documentó para J129:

- `SIP96X1-23559`: problema de backup/PUT tras 404 cuando hay HTTP authentication y el usuario ignora la autenticación.
- `SIP96X1-23211`: glare handling con INVITE retransmitido y 407 con nonce diferente; workaround documentado: cambiar Timer T1.

### Versiones/hardware

Avaya advierte que existen revisiones de hardware J129 con versión mínima de software. Un firmware demasiado antiguo puede ser rechazado por hardware más nuevo, y no debe asumirse que cualquier downgrade es posible.

### Capacidades no soportadas por J129

En J100 SIP 4.1.11.0 Avaya lista varias funciones no soportadas en J129, entre ellas presencia visible, downloadable ringtones, Favorites, Personalize labels, Bluetooth y varias funciones Aura/CC Elite. Esto importa para no diseñar UI o parámetros que el modelo no puede aplicar.

## 6. BUG-J129-004 — persistencia de credenciales SIP locales

Hallazgo físico del proyecto:

- Endpoint Configurator: 0 cuentas.
- Apply general corregido: éxito.
- archivo `<mac>.txt`: eliminado.
- reboot físico: el J129 vuelve a registrar `201`.
- Asterisk: `201/201` en IP del J129 y estado `OK`.

Esto demuestra que eliminar el archivo por MAC del servidor no equivale a borrar credenciales ya persistidas en el teléfono.

La documentación oficial indica que `FORCE_SIP_USERNAME`, `FORCE_SIP_PASSWORD` y `FORCE_SIP_EXTENSION` reemplazan los campos introducidos por el usuario y evitan el prompt de login en power cycle. También documenta precedencia de configuración y valores persistentes en el dispositivo.

**Pendiente crítico:** determinar el mecanismo oficial para borrar/logout/revocar esa identidad de forma remota. No enviar valores vacíos ni inventar un comando hasta encontrar semántica oficial para la versión probada.

Fuentes:
- Avaya Deskphone SIP Release 7.1.1.0.9 Readme, sección FORCE_SIP_*: https://support.avaya.com/css/public/documents/101042670
- Installing and Administering Avaya J129 in third-party call control setup: https://support.avaya.com/css/public/documents/101037009

## 7. Idioma español

**Viable.** El paquete J100 incluye archivos específicos para J129:

```text
Mlf_J129_CastilianSpanish.xml
Mlf_J129_LatinAmericanSpanish.xml
```

Para Honduras, el candidato lógico es `Mlf_J129_LatinAmericanSpanish.xml`.

La familia Avaya utiliza parámetros de idioma como `LANGxFILE`, `LANG0STAT` y `LANGSYS`. Antes de implementar hay que verificar la sintaxis exacta aplicable al firmware J129 Open SIP usado.

Para v1 se propone:

1. alojar el archivo oficial de español latinoamericano en la PBX;
2. configurar un único idioma por defecto inicialmente;
3. comprobar descarga HTTP en access log;
4. comprobar cambio visible en J129 físico;
5. solo después decidir si se permite al usuario cambiar idioma localmente.

## 8. Menú de administración del teléfono

Avaya documenta `PROCSTAT`:

```text
PROCSTAT 0 -> Admin menu permitido
PROCSTAT 1 -> Admin menu no permitido para configuración
```

También documenta `PROCPSWD` / `ADMIN_PASSWORD` para el código de acceso al menú Admin. No confundir este password con el password del Web UI.

Fuente oficial: Installing and Administering Avaya J129 IP Phone, sección Parameters for managing Admin menu: https://support.avaya.com/css/public/documents/101033171

### Propuesta v1

Hacer configurable en Endpoint Configurator una política simple:

```text
Admin menu: enabled | disabled
```

pero no activarla hasta tener golden tests y prueba física. Si se deshabilita el menú, debe existir procedimiento de recuperación/factory reset documentado para evitar bloquear soporte de campo.

## 9. Preferencias del teléfono a investigar

La primera versión todavía necesita decidir cuáles preferencias deben ser administradas centralmente. Priorizar solo parámetros con valor operativo claro:

- idioma;
- zona horaria / hora;
- formato de fecha y hora;
- dial plan / inter-digit timeout;
- volumen/ring settings solo si la documentación confirma soporte J129;
- DHCP/VLAN ya expuestos por Issabel cuando aplique;
- habilitar/deshabilitar Admin menu;
- web server HTTP/HTTPS si se decide incluir gestión remota;
- bloqueo de cambios locales cuando sea necesario.

Evitar convertir Endpoint Configurator en una réplica completa del Web UI del teléfono.

## 10. Gestión web y SSH

La documentación oficial Open SIP indica que el teléfono puede ofrecer Web UI. El usuario web es `admin`; la administración de password web no debe confundirse con `ADMIN_PASSWORD` del menú físico.

SSH del J100 está orientado a Avaya Services/EASG y cuentas predefinidas como `craft`; no debe mapearse el campo genérico SSH username/password de Issabel a un login arbitrario del J129 sin evidencia oficial.

## 11. Firmware upgrade — plan de laboratorio recomendado

Antes de intentar upgrade físico:

1. identificar hardware/comcode exacto del J129;
2. guardar versión actual `3.0.0.0.20` y estado funcional;
3. descargar paquete oficial 4.1.11.0 completo desde Avaya;
4. verificar hashes y contenido del paquete;
5. revisar advisements y minimum firmware/hardware revision;
6. desplegar binario y XML en ruta LAB separada;
7. validar HTTP GET de todos los archivos desde otro cliente;
8. crear workflow manual `firmware-audit` primero read-only;
9. crear workflow de activación separado que publique el `J100Supgrade.txt` oficial únicamente durante la ventana de prueba;
10. capturar requests HTTP y progreso del teléfono;
11. probar llamadas, registro, provisioning, idioma y lifecycle después del upgrade;
12. documentar si rollback/downgrade está permitido para esa revisión de hardware.

No realizar upgrade en el teléfono de prueba antes de cerrar el mecanismo de recuperación.

## 12. Prioridad para la próxima sesión

Orden sugerido:

1. investigar y resolver `BUG-J129-004` — logout/borrado remoto de identidad SIP persistente;
2. identificar comcode/hardware revision del J129 LAB;
3. preparar auditoría de firmware sin actualizar todavía;
4. validar español latinoamericano;
5. probar `PROCSTAT` y política de Admin menu;
6. revisar parámetros Open SIP recomendados (`ENABLE_AVAYA_ENVIRONMENT`, `DISCOVER_AVAYA_ENVIRONMENT`, `ENABLE_IPOFFICE`);
7. definir preferencias mínimas v1;
8. revisar `BUG-J129-002` multicuenta con documentación moderna;
9. ejecutar pruebas de llamada/DTMF/transfer/hold con Asterisk;
10. solo al final probar actualización de firmware controlada.

## 13. Fuentes oficiales principales

- Avaya J100 Series SIP Release 4.1.11.0 Readme — https://support.avaya.com/css/en/public/documents/101095479
- Installing and Administering Avaya J100 Series SIP IP Phones in Open SIP — https://support.avaya.com/css/public/documents/101053965
- Installing and Administering Avaya J129 IP Phone in third-party call control setup — https://support.avaya.com/css/public/documents/101037009
- Installing and Administering Avaya J129 IP Phone — https://support.avaya.com/css/public/documents/101033171
- IP Office SIP Telephone Installation Notes — https://support.avaya.com/css/public/documents/101091571
- J100 SIP 4.1.5.0 Readme — https://support.avaya.com/css/public/documents/101090998
- J100 SIP 4.1.2.1 Readme — https://support.avaya.com/css/public/documents/101087449
- J100 SIP 4.0.12.1 Readme — https://support.avaya.com/css/public/documents/101081837
- J100 SIP 4.0.6.1 Readme — https://support.avaya.com/css/public/documents/101070565
- J100 SIP 4.0.0.0 Readme — https://support.avaya.com/css/public/documents/101054005
