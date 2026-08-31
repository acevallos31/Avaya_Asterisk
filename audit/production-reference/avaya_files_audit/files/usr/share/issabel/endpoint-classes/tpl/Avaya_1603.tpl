############################################################
## AVAYA 1603-I / 1603SW-I - SIP CONFIG TEMPLATE         ##
## Generado automáticamente por Issabel Endpoint Config. ##
############################################################

## Configuración del servidor SIP
SET SIPDOMAIN {{server_ip}}
SET SIPPROXYSRVR {{server_ip}}
SET SIPPROXYSRVR_IN_USE {{server_ip}}
SET SIP_CONTROLLER_LIST "{{server_ip}}:5060;transport=udp"
SET SIPPORT 5060
SET SIPREGISTRAR {{server_ip}}
SET SIPREGPORT 5060

## Configuración de la extensión
{{py:n = 1}}{{for extension in sip}}
SET SIPUSERNAME {{extension.extension}}
SET SIPPASSWORD {{extension.secret}}
SET DISPLAY_NAME {{extension.description}}
SET AUTHNAME {{extension.account}}
SET LINEKEY {{n}}
{{n += 1}}{{endfor}}

## Configuración del archivo de aprovisionamiento
GET 46xxsettings.txt
