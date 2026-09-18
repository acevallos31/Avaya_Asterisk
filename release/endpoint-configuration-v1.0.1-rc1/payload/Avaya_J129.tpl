## Avaya J129 - configuración específica por MAC
## Generado por Issabel Endpoint Configurator

SET SIP_CONTROLLER_LIST "{{server_ip}}:5060;transport=udp"
SET SIPPROXYSRVR {{server_ip}}
SET SIPPROXYSRVR_IN_USE {{server_ip}}
SET SIPDOMAIN {{server_ip}}
SET SIPPORT 5060
SET ENABLE_PRESENCE 1

{{for extension in sip}}
SET DISPLAY_NAME "{{extension.description}}"
SET SIP_USER_ID {{extension.extension}}
SET SIP_USER_ACCOUNT {{extension.extension}}@{{server_ip}}
SET ENABLE_SIP_USER_ID 1
SET SCREEN_NAME_ORDER 1
SET FORCE_SIP_USERNAME "{{extension.extension}}"
SET FORCE_SIP_PASSWORD "{{extension.secret}}"
SET FORCE_SIP_EXTENSION "{{extension.extension}}"
{{endfor}}
