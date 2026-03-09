## Configuración de Avaya J129 ##
##
## Archivo generado automáticamente por Issabel Endpoint Configurator
##

[GENERAL]
SIP_SERVER={{server_ip}}
SIP_PORT={{server_port}}
USERNAME={{extension}}
PASSWORD={{password}}
DISPLAY_NAME={{display_name}}

[NETWORK]
DHCP=1
STATIC_IP={{static_ip}}
SUBNET_MASK={{subnet_mask}}
GATEWAY={{gateway}}
DNS={{dns_server}}

[PROVISIONING]
PROVISIONING_SERVER={{provisioning_server}}
PROVISIONING_METHOD=HTTPS
CONFIG_FILE_NAME={{mac_address}}.cfg

