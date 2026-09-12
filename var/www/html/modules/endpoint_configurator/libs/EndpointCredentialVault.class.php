<?php
/*
 * Endpoint Configurator administrative credential vault.
 * Plaintext exists only in process memory and is never returned by this class.
 */
class EndpointCredentialVault
{
    const KEY_FILE = '/etc/issabel/endpoint-configurator.key';
    const CIPHER = 'aes-256-gcm';
    const KEY_REFERENCE = 'file:/etc/issabel/endpoint-configurator.key';

    private $_db;
    private $_errMsg;

    public function __construct($db = NULL)
    {
        if ($db !== NULL) {
            $this->_db = $db;
            return;
        }

        $dsn = generarDSNSistema('asteriskuser', 'endpointconfig');
        $this->_db = new paloDB($dsn);
        if ($this->_db->errMsg != '') {
            $this->_errMsg = $this->_db->errMsg;
            $this->_db = NULL;
        } else {
            $this->_db->genQuery('SET NAMES utf8');
        }
    }

    public function getErrMsg() { return $this->_errMsg; }

    public function validatePassword($password)
    {
        if (!is_string($password) || strlen($password) < 12 || strlen($password) > 128) {
            $this->_errMsg = 'Administrative password must contain 12 to 128 characters.';
            return FALSE;
        }
        return TRUE;
    }

    private function _key()
    {
        if (!is_readable(self::KEY_FILE)) {
            $this->_errMsg = 'Endpoint Configurator encryption key is unavailable.';
            return NULL;
        }
        $key = file_get_contents(self::KEY_FILE);
        if ($key === FALSE || strlen($key) < 32) {
            $this->_errMsg = 'Endpoint Configurator encryption key is invalid.';
            return NULL;
        }
        return hash('sha256', $key, TRUE);
    }

    public function encrypt($password)
    {
        if (!$this->validatePassword($password)) return NULL;
        $key = $this->_key();
        if ($key === NULL || !function_exists('openssl_encrypt')) return NULL;

        $iv = openssl_random_pseudo_bytes(12);
        $tag = '';
        $ciphertext = openssl_encrypt(
            $password, self::CIPHER, $key, OPENSSL_RAW_DATA, $iv, $tag, '', 16
        );
        if ($ciphertext === FALSE || strlen($tag) !== 16) {
            $this->_errMsg = 'Unable to encrypt administrative credential.';
            return NULL;
        }

        return json_encode(array(
            'v' => 1,
            'alg' => self::CIPHER,
            'iv' => base64_encode($iv),
            'tag' => base64_encode($tag),
            'ct' => base64_encode($ciphertext),
        ));
    }

    public function decrypt($payload)
    {
        $key = $this->_key();
        if ($key === NULL || !is_string($payload)) return NULL;
        $data = json_decode($payload, TRUE);
        if (!is_array($data) || $data['v'] !== 1 || $data['alg'] !== self::CIPHER) {
            $this->_errMsg = 'Encrypted credential payload is invalid.';
            return NULL;
        }
        $iv = base64_decode($data['iv'], TRUE);
        $tag = base64_decode($data['tag'], TRUE);
        $ct = base64_decode($data['ct'], TRUE);
        if ($iv === FALSE || strlen($iv) !== 12 || $tag === FALSE || strlen($tag) !== 16 || $ct === FALSE) {
            $this->_errMsg = 'Encrypted credential payload is malformed.';
            return NULL;
        }
        $plain = openssl_decrypt($ct, self::CIPHER, $key, OPENSSL_RAW_DATA, $iv, $tag, '');
        if ($plain === FALSE) {
            $this->_errMsg = 'Encrypted credential cannot be authenticated.';
            return NULL;
        }
        return $plain;
    }

    public function status()
    {
        if ($this->_db === NULL) return NULL;
        $row = $this->_db->getFirstRowQuery(
            'SELECT active_version, pending_version, status, rotated_at, key_reference FROM pbx_admin_password_policy WHERE id = 1',
            TRUE
        );
        if (!is_array($row)) {
            $this->_errMsg = $this->_db->errMsg;
            return NULL;
        }
        if (count($row) === 0) {
            return array(
                'active_version' => 0,
                'pending_version' => NULL,
                'status' => 'UNCONFIGURED',
                'rotated_at' => NULL,
                'key_reference' => self::KEY_REFERENCE,
            );
        }
        return array(
            'active_version' => (int)$row['active_version'],
            'pending_version' => $row['pending_version'] === NULL ? NULL : (int)$row['pending_version'],
            'status' => $row['status'],
            'rotated_at' => $row['rotated_at'],
            'key_reference' => self::KEY_REFERENCE,
        );
    }

    public function createPendingGlobal($pbxIdentity, $password, $actor = 'issabel-ui')
    {
        if ($this->_db === NULL || !$this->validatePassword($password)) return FALSE;
        $encrypted = $this->encrypt($password);
        if ($encrypted === NULL) return FALSE;
        $now = date('Y-m-d H:i:s');
        $current = $this->status();
        if ($current === NULL) return FALSE;
        $next = $current['active_version'] + 1;
        $sql = 'INSERT INTO pbx_admin_password_policy ' .
            '(id, pbx_identity, active_version, pending_version, ciphertext, key_reference, status, created_at) ' .
            'VALUES (1, ?, ?, ?, ?, ?, ?, ?) ' .
            'ON DUPLICATE KEY UPDATE pbx_identity = VALUES(pbx_identity), pending_version = VALUES(pending_version), ' .
            'ciphertext = VALUES(ciphertext), key_reference = VALUES(key_reference), status = VALUES(status), created_at = VALUES(created_at)';
        if (!$this->_db->genQuery($sql, array($pbxIdentity, $current['active_version'], $next, $encrypted, self::KEY_REFERENCE, 'PENDING', $now))) {
            $this->_errMsg = $this->_db->errMsg;
            return FALSE;
        }
        $correlation = sprintf('%08x-%04x-%04x-%04x-%012x', mt_rand(0, 0xffffffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffffffffffff));
        if (!$this->_db->genQuery(
            'INSERT INTO endpoint_credential_event (id_endpoint, operation, result, actor, correlation_id, created_at) VALUES (NULL, ?, ?, ?, ?, ?)',
            array('CREATE_PENDING', 'PENDING', substr((string)$actor, 0, 191), $correlation, $now)
        )) {
            $this->_errMsg = $this->_db->errMsg;
            return FALSE;
        }
        return $next;
    }

    public function endpointStatus($idEndpoint)
    {
        if ($this->_db === NULL) return NULL;
        $row = $this->_db->getFirstRowQuery(
            'SELECT source, version, validation_status, last_validated_at, rotation_status FROM endpoint_admin_credential WHERE id_endpoint = ?',
            TRUE, array((int)$idEndpoint)
        );
        if (!is_array($row)) {
            $this->_errMsg = $this->_db->errMsg;
            return NULL;
        }
        if (count($row) === 0) {
            return array('source' => 'GLOBAL', 'version' => 0, 'validation_status' => 'MISSING', 'last_validated_at' => NULL, 'rotation_status' => 'NONE');
        }
        return $row;
    }
}
?>
