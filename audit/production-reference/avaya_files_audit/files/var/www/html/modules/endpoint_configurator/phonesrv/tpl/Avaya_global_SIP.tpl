# Avaya Global SIP Configuration Template

SET SIPDOMAIN {{server_ip}}
SET SIPPROXYSRVR {{server_ip}}
SET SIPPROXYSRVR_IN_USE {{server_ip}}
SET SIP_CONTROLLER_LIST "{{server_ip}}:5060;transport=udp"

# ConfiguraciÃ³n de la extensiÃ³n SIP
{{py:n = 1}}{{for extension in sip}}
SET SIPUSERNAME {{extension.extension}}
SET SIPPASSWORD {{extension.secret}}
SET DISPLAY_NAME {{extension.description}}
SET AUTHNAME {{extension.account}}
SET LINEKEY {{n}}
SET SIPPORT 5060
SET SIPREGISTRAR {{server_ip}}
SET SIPREGPORT 5060
{{n += 1}}{{endfor}}

# ConfiguraciÃ³n de aprovisionamiento
SET CONFIG_SERVER_PATH "http://{{server_ip}}/settings/"

# ?? ACTIVAR INTERFAZ WEB
SET ENABLE_WEBSERVER 1
SET ADMIN_PASSWORD 12345
SET FORCE_WEB_ADMIN_PASSWORD XXXXXXXX
SET WEBSERVER_PORT 80
SET WEBSERVER_SECURE_MODE 0

# ?? CONFIGURACIÃ“N PARA SIP ESTÃNDAR
SET ENABLE_AVAYA_ENVIRONMENT 0
SET DISCOVER_AVAYA_ENVIRONMENT 0
SET ENABLE_3PCC_ENVIRONMENT 1

# Nombre del archivo de configuraciÃ³n generado
GET $MACADDR.txt

