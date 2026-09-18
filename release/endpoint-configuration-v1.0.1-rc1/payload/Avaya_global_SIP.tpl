## Avaya J129 - configuración global SIP/3PCC
## Este archivo no contiene credenciales de extensiones.

SET SIPDOMAIN {{server_ip}}
SET SIPPROXYSRVR {{server_ip}}
SET SIPPROXYSRVR_IN_USE {{server_ip}}
SET SIP_CONTROLLER_LIST "{{server_ip}}:5060;transport=udp"
SET SIPPORT 5060

## Operación con servidor SIP de terceros (3PCC)
SET ENABLE_AVAYA_ENVIRONMENT 0
SET DISCOVER_AVAYA_ENVIRONMENT 0
SET ENABLE_3PCC_ENVIRONMENT 1

## Avaya J129 SIP R2.0.0.0+ soporta OOD SIP NOTIFY Event:resync/check-sync.
## Permite solicitar resync/restart remoto una vez que el teléfono haya cargado
## este parámetro. No actualiza firmware por sí solo; el teléfono consulta
## J100Supgrade.txt/settings al recibir la notificación.
SET ENABLE_OOD_RESET_NOTIFY 1

## Cada teléfono obtiene sus credenciales desde su archivo específico por MAC.
GET $MACADDR.txt
