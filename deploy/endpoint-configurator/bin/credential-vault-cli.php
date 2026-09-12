#!/usr/bin/env php
<?php
/* LAB/runtime bridge. Secret input/output is restricted to stdin/stdout pipes. */
if (PHP_SAPI !== 'cli') {
    fwrite(STDERR, "ERROR: CLI only\n");
    exit(2);
}

class EndpointCredentialCliDb
{
    public $errMsg = '';
    private $pdo;

    public function __construct()
    {
        $values = array();
        foreach (file('/etc/amportal.conf', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
            if ($line === '' || $line[0] === '#' || strpos($line, '=') === FALSE) continue;
            list($key, $value) = explode('=', $line, 2);
            $values[trim($key)] = trim($value);
        }
        $host = isset($values['AMPDBHOST']) && $values['AMPDBHOST'] !== '' ? $values['AMPDBHOST'] : 'localhost';
        try {
            $this->pdo = new PDO(
                'mysql:host=' . $host . ';dbname=endpointconfig;charset=utf8',
                isset($values['AMPDBUSER']) ? $values['AMPDBUSER'] : '',
                isset($values['AMPDBPASS']) ? $values['AMPDBPASS'] : '',
                array(PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_EMULATE_PREPARES => FALSE)
            );
        } catch (Exception $e) {
            $this->errMsg = 'Database connection failed.';
        }
    }

    public function genQuery($sql, $params = array())
    {
        if (!$this->pdo) return FALSE;
        try {
            $stmt = $this->pdo->prepare($sql);
            return $stmt->execute($params);
        } catch (Exception $e) {
            $this->errMsg = 'Database operation failed.';
            return FALSE;
        }
    }

    public function getFirstRowQuery($sql, $assoc = TRUE, $params = array())
    {
        if (!$this->pdo) return FALSE;
        try {
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute($params);
            $row = $stmt->fetch($assoc ? PDO::FETCH_ASSOC : PDO::FETCH_NUM);
            return $row === FALSE ? array() : $row;
        } catch (Exception $e) {
            $this->errMsg = 'Database query failed.';
            return FALSE;
        }
    }
}

require_once '/var/www/html/modules/endpoint_configurator/libs/EndpointCredentialVault.class.php';

$action = isset($argv[1]) ? $argv[1] : '';
$mac = isset($argv[2]) ? strtoupper(preg_replace('/[^0-9A-F]/i', '', $argv[2])) : '';
if (!preg_match('/^[0-9A-F]{12}$/', $mac)) {
    fwrite(STDERR, "ERROR: invalid MAC\n");
    exit(2);
}

$db = new EndpointCredentialCliDb();
if ($db->errMsg !== '') {
    fwrite(STDERR, "ERROR: database unavailable\n");
    exit(1);
}
$vault = new EndpointCredentialVault($db);
$endpointId = $vault->findEndpointIdByMac($mac);
if ($endpointId === NULL) {
    fwrite(STDERR, "ERROR: endpoint not found\n");
    exit(1);
}

if ($action === 'store-override') {
    $password = rtrim(stream_get_contents(STDIN, 129), "\r\n");
    if ($vault->createPendingOverride($endpointId, $password, 'lab-test68') === FALSE) {
        fwrite(STDERR, "ERROR: override storage failed\n");
        exit(1);
    }
    unset($password);
    echo "CREDENTIAL-OVERRIDE-STORED=PENDING\n";
    exit(0);
}

if ($action === 'emit-pending') {
    if (!function_exists('posix_geteuid') || posix_geteuid() !== 0 || getenv('ENDPOINT_CREDENTIAL_ALLOW_EMIT') !== '1') {
        fwrite(STDERR, "ERROR: credential emission denied\n");
        exit(1);
    }
    $password = $vault->pendingCredentialForValidation($endpointId);
    if ($password === NULL) {
        fwrite(STDERR, "ERROR: pending credential unavailable\n");
        exit(1);
    }
    fwrite(STDOUT, $password);
    unset($password);
    exit(0);
}

if ($action === 'mark-validated') {
    if (!$vault->markEndpointValidated($endpointId, 'lab-test68')) {
        fwrite(STDERR, "ERROR: validation state update failed\n");
        exit(1);
    }
    echo "CREDENTIAL-OVERRIDE-STATUS=VALIDATED\n";
    exit(0);
}

if ($action === 'status') {
    $status = $vault->endpointStatus($endpointId);
    if (!is_array($status)) {
        fwrite(STDERR, "ERROR: status unavailable\n");
        exit(1);
    }
    echo 'source=' . $status['source'] . "\n";
    echo 'version=' . (int)$status['version'] . "\n";
    echo 'validation_status=' . $status['validation_status'] . "\n";
    echo 'rotation_status=' . $status['rotation_status'] . "\n";
    exit(0);
}

fwrite(STDERR, "ERROR: unsupported action\n");
exit(2);
?>
