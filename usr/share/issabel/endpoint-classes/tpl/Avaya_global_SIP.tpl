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

## Cada teléfono obtiene sus credenciales desde su archivo específico por MAC.
GET $MACADDR.txt
