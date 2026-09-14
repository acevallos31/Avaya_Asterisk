<?php
/*
 * Read-only account/registration summary for the Endpoint Configurator list.
 * Loaded automatically by endpoint_configurator/index.php as Dialog_Summary.
 */

class Dialog_Summary
{
    static function templateContent($smarty, $module_name, $local_templates_dir)
    {
        // This dialog exposes JSON only. The main endpoint table renders the UI.
        return '';
    }

    static function handleJSON_loadAll($smarty, $module_name, $local_templates_dir, $dlglist)
    {
        $respuesta = array(
            'status' => 'success',
            'message' => '(no message)',
            'endpoints' => array(),
            'labels' => array(
                'header' => _tr('Extension / Registration'),
                'not_assigned' => _tr('Not assigned'),
                'registered' => _tr('Registered'),
                'not_registered' => _tr('Not registered'),
                'registration_unknown' => _tr('Registration unknown'),
                'registered_at' => _tr('Registered at'),
            ),
        );

        $dsn = generarDSNSistema('asteriskuser', 'endpointconfig');
        $db = new paloDB($dsn);
        if ($db->errMsg != '') {
            $respuesta['status'] = 'error';
            $respuesta['message'] = '(internal) Failed to open endpoint database: '.$db->errMsg;
            return self::_json($respuesta);
        }
        $db->genQuery('SET NAMES utf8');

        $endpointRows = $db->fetchTable(
            'SELECT id AS id_endpoint, last_known_ipv4 FROM endpoint ORDER BY id',
            TRUE
        );
        if (!is_array($endpointRows)) {
            $respuesta['status'] = 'error';
            $respuesta['message'] = '(internal) Failed to read endpoints: '.$db->errMsg;
            return self::_json($respuesta);
        }

        $endpoints = array();
        foreach ($endpointRows as $row) {
            $id = (string)$row['id_endpoint'];
            $endpoints[$id] = array(
                'id_endpoint' => (int)$row['id_endpoint'],
                'last_known_ipv4' => $row['last_known_ipv4'],
                'accounts' => array(),
            );
        }

        $accountRows = $db->fetchTable(
            'SELECT ea.id_endpoint, ea.tech, ea.account, ea.priority, '.
            'ad.id AS extension, ad.description '.
            'FROM endpoint_account ea '.
            'LEFT JOIN asterisk.devices ad ON ea.account = ad.id '.
            'ORDER BY ea.id_endpoint, ea.priority',
            TRUE
        );
        if (!is_array($accountRows)) {
            $respuesta['status'] = 'error';
            $respuesta['message'] = '(internal) Failed to read endpoint accounts: '.$db->errMsg;
            return self::_json($respuesta);
        }

        $registered = self::_collectRegisteredAccounts();

        foreach ($accountRows as $row) {
            $id = (string)$row['id_endpoint'];
            if (!isset($endpoints[$id])) continue;

            $tech = strtolower((string)$row['tech']);
            $account = (string)$row['account'];
            $registrationKnown = isset($registered[$tech]) && is_array($registered[$tech]);
            $registerIp = NULL;
            if ($registrationKnown && isset($registered[$tech][$account])) {
                $registerIp = $registered[$tech][$account];
            }

            $extension = is_null($row['extension']) || $row['extension'] === ''
                ? $account
                : (string)$row['extension'];

            $endpoints[$id]['accounts'][] = array(
                'tech' => $tech,
                'account' => $account,
                'extension' => $extension,
                'priority' => (int)$row['priority'],
                'description' => $row['description'],
                'registration_known' => $registrationKnown,
                'registered' => !is_null($registerIp),
                'registerip' => $registerIp,
                'registered_here' => !is_null($registerIp)
                    && !empty($endpoints[$id]['last_known_ipv4'])
                    && $registerIp === $endpoints[$id]['last_known_ipv4'],
            );
        }

        $respuesta['endpoints'] = array_values($endpoints);
        return self::_json($respuesta);
    }

    private static function _json($respuesta)
    {
        $json = new Services_JSON();
        Header('Content-Type: application/json');
        return $json->encode($respuesta);
    }

    private static function _collectRegisteredAccounts()
    {
        $registered = array(
            'sip' => NULL,
            'iax2' => NULL,
            'pjsip' => NULL,
        );

        if (!file_exists('/var/lib/asterisk/agi-bin/phpagi-asmanager.php')) {
            return $registered;
        }

        require_once '/var/lib/asterisk/agi-bin/phpagi-asmanager.php';
        $astman = new AGI_AsteriskManager();
        if (!$astman->connect('localhost', 'admin', obtenerClaveAMIAdmin())) {
            return $registered;
        }

        // chan_sip: a dynamic peer with a concrete IPv4 address is registered.
        $r = $astman->Command('sip show peers');
        if (isset($r['Response']) && $r['Response'] != 'Error') {
            $registered['sip'] = array();
            $data = isset($r['data']) ? $r['data'] : '';
            foreach (explode("\n", $data) as $line) {
                $line = trim($line);
                if ($line === '') continue;
                $parts = preg_split('/\s+/', $line);
                if (count($parts) < 2) continue;
                if (!preg_match('/^\d{1,3}(?:\.\d{1,3}){3}$/', $parts[1])) continue;
                $name = explode('/', $parts[0]);
                if (!empty($name[0])) $registered['sip'][(string)$name[0]] = $parts[1];
            }
        }

        // IAX2: keep the same successful-peer criterion used by the legacy module.
        $r = $astman->Command('iax2 show peers');
        if (isset($r['Response']) && $r['Response'] != 'Error') {
            $registered['iax2'] = array();
            $data = isset($r['data']) ? $r['data'] : '';
            foreach (explode("\n", $data) as $line) {
                $line = trim($line);
                if ($line === '') continue;
                $parts = preg_split('/\s+/', $line);
                if (count($parts) < 2) continue;
                if (!preg_match('/^\d{1,3}(?:\.\d{1,3}){3}$/', $parts[1])) continue;
                if (strpos($line, 'OK') === FALSE) continue;
                $registered['iax2'][(string)$parts[0]] = $parts[1];
            }
        }

        // PJSIP: prefer contacts, which directly expose endpoint/account and IP.
        $r = $astman->Command('pjsip show contacts');
        if (isset($r['Response']) && $r['Response'] != 'Error') {
            $registered['pjsip'] = array();
            $data = isset($r['data']) ? $r['data'] : '';
            foreach (explode("\n", $data) as $line) {
                if (strpos($line, 'Avail') === FALSE) continue;
                if (preg_match('/Contact:\s+([^\/\s]+)\/sip:[^@\s]+@(\d{1,3}(?:\.\d{1,3}){3})/i', $line, $m)) {
                    $registered['pjsip'][(string)$m[1]] = $m[2];
                }
            }
        } else {
            // Compatibility fallback for older Asterisk/Issabel builds.
            $r = $astman->Command('pjsip show endpoints');
            if (isset($r['Response']) && $r['Response'] != 'Error') {
                $registered['pjsip'] = array();
                $data = isset($r['data']) ? $r['data'] : '';
                foreach (explode("\n", $data) as $line) {
                    if (strpos($line, 'Avail') === FALSE) continue;
                    if (preg_match('/Contact:\s+([^\/\s]+)\/sip:[^@\s]+@(\d{1,3}(?:\.\d{1,3}){3})/i', $line, $m)) {
                        $registered['pjsip'][(string)$m[1]] = $m[2];
                    }
                }
            }
        }

        $astman->disconnect();
        return $registered;
    }
}

?>
