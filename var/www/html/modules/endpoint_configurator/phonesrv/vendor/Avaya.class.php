<?php
/*
  Avaya J100 Series Configurator for Issabel
*/

require_once '/var/www/html/libs/misc.lib.php'; // Cargar librería de Issabel

// Definir ISSABEL_BASE si no está definido
if (!defined('ISSABEL_BASE')) {
    define('ISSABEL_BASE', '/var/www/html/');
}

// Cargar la clase base del vendor
require_once __DIR__ . '/BaseVendorResource.class.php';


ini_set('log_errors', 1);
ini_set('error_log', '/var/log/avaya_debug.log');
ini_set('display_errors', 1);
error_reporting(E_ALL);

error_log("### DEBUG: Iniciando Avaya.class.php ###");




class Avaya extends BaseVendorResource
{
    public function __construct($db, $url)
{
    parent::__construct($db, $url);
    $this->brand_name = "Avaya";
    $this->config_dir = "/tftpboot/";

    // Habilitar logging manualmente
    ini_set('log_errors', 1);
    ini_set('error_log', '/var/log/avaya_debug.log');
    ini_set('display_errors', 1);
    error_reporting(E_ALL);

    // Prueba de log inmediato
    error_log("### DEBUG: Iniciando Avaya.class.php ###");

    error_log("### DEBUG: Avaya.class.php cargado correctamente ###");
}


    public function handle($endpoint_id, $pathList)
    {
        try {
            error_log("### DEBUG: handle() ejecutado en Avaya.class.php con endpoint_id: $endpoint_id ###");

            // Verificar que el ID del endpoint es válido
            if (!$endpoint_id) {
                throw new Exception("ID del endpoint inválido o no proporcionado.");
            }

            // Obtener datos del endpoint desde la base de datos
            $sql = "SELECT e.id, e.mac_address, mo.name AS model, ea.account AS exten, ep.property_value AS secret
        FROM endpoint e
        LEFT JOIN manufacturer m ON e.id_manufacturer = m.id
        LEFT JOIN model mo ON e.id_model = mo.id
        LEFT JOIN endpoint_account ea ON e.id = ea.id_endpoint
        LEFT JOIN endpoint_properties ep ON e.id = ep.id_endpoint AND ep.property_key = 'sip_secret'
        WHERE e.id = ?";

$endpoint = $this->_db->getFirstRowQuery($sql, true, array($endpoint_id));

if (!$endpoint) {
    error_log("### ERROR: No se encontró el endpoint en la base de datos ###");
    return;
}

error_log("### DEBUG: Datos obtenidos: " . print_r($endpoint, true));


            if (!$endpoint) {
                throw new Exception("No se encontró el endpoint en la base de datos para ID: $endpoint_id.");
            }

            error_log("### DEBUG: Datos obtenidos del endpoint: " . print_r($endpoint, true));

            $mac = $endpoint['mac_address'];
            $model = $endpoint['model'];
            $settings = [
                'server'   => $endpoint['ip_address'],
                'account'  => $endpoint['exten'],
                'password' => $endpoint['secret']
            ];

            if (empty($settings['account']) || empty($settings['password'])) {
                throw new Exception("Extensión o contraseña vacías para el endpoint ID: $endpoint_id.");
            }

            error_log("### DEBUG: handle() llamando a build_config_files() con MAC: $mac, Modelo: $model ###");
            $this->build_config_files($mac, $model, $settings);

        } catch (Exception $e) {
            error_log("### ERROR: " . $e->getMessage() . " ###");
        }
    }

    public function build_config_files($mac, $model, $settings)
    {
        try {
            error_log("### DEBUG: build_config_files() ejecutado para MAC: $mac, Modelo: $model ###");

            if (empty($settings)) {
                throw new Exception("settings está vacío, Issabel no está pasando datos.");
            }

            error_log("### DEBUG: Configuración recibida - " . print_r($settings, true));

            // Asegurar que los valores requeridos están presentes
            $server    = isset($settings['server']) ? $settings['server'] : '0.0.0.0';
            $extension = !empty($settings['account']) ? $settings['account'] : "0000";
            $secret    = !empty($settings['password']) ? $settings['password'] : "defaultpassword";

            error_log("### DEBUG: Valores extraídos - Server: $server, Ext: $extension, Secret: $secret ###");

            // Nombre del archivo de configuración
            $config_filename = $this->config_dir . strtoupper($mac) . ".cfg";

            // Contenido del archivo de configuración
            $config_content = "## Avaya J100 Series Configuration\n";
            $config_content .= "SET SIPDOMAIN $server\n";
            $config_content .= "SET SIPPORT 5060\n";
            $config_content .= "SET SIPREGISTRAR1 $server\n";
            $config_content .= "SET SIPUSERNAME $extension\n";
            $config_content .= "SET SIPPASSWORD $secret\n";
            $config_content .= "SET PHONEMODEL $model\n";
            $config_content .= "SET SIPPROXY $server\n";
            $config_content .= "SET SIPPROXYPORT 5060\n";
            $config_content .= "SET HTTPPROXYDISABLED 1\n";
            $config_content .= "SET CONFIG_SERVER_PATH tftp://$server/\n";

            // Activar Web Server en el teléfono
            $config_content .= "SET ENABLE_WEBSERVER 1\n";
            $config_content .= "SET ADMIN_PASSWORD 12345\n";
            $config_content .= "SET FORCE_WEB_ADMIN_PASSWORD admin123\n";
            $config_content .= "SET WEBSERVER_PORT 80\n";
            $config_content .= "SET WEBSERVER_SECURE_MODE 0\n";

            // Configuración adicional de SIP
            $config_content .= "SET ENABLE_AVAYA_ENVIRONMENT 0\n";
            $config_content .= "SET DISCOVER_AVAYA_ENVIRONMENT 0\n";
            $config_content .= "SET ENABLE_3PCC_ENVIRONMENT 1\n";

            // Escribir configuración en archivo
            if (file_put_contents($config_filename, $config_content) === false) {
                throw new Exception("No se pudo escribir el archivo de configuración: $config_filename.");
            }

            error_log("### DEBUG: Archivo de configuración generado correctamente: $config_filename ###");

            // Ejecutar Avaya.py para generar el archivo de configuración
            $command = "python3 /var/www/html/modules/endpoint_configurator/phonesrv/vendor/Avaya.py $server $mac $extension $secret";
            exec($command . " 2>&1", $output, $return_var);

            if ($return_var !== 0) {
                throw new Exception("Fallo al ejecutar Avaya.py: " . implode("\n", $output));
            }

            error_log("### DEBUG: Avaya.py ejecutado con éxito ###");

        } catch (Exception $e) {
            error_log("### ERROR: " . $e->getMessage() . " ###");
        }
    }
}
?>
