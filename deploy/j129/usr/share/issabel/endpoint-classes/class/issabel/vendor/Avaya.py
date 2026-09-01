# vim: set fileencoding=utf-8 :
# vim: set expandtab tabstop=4 softtabstop=4 shiftwidth=4:
# Codificación: UTF-8

import logging

import issabel.BaseEndpoint
from issabel.BaseEndpoint import BaseEndpoint


class Endpoint(BaseEndpoint):
    """Provisionamiento Avaya J129 integrado al pipeline estándar de Issabel.

    Las cuentas SIP son entregadas por BaseEndpoint.setAccountList() y se exponen
    a las plantillas mediante _prepareVarList(). Esta clase no consulta MySQL ni
    recibe credenciales SIP fuera del flujo estándar de Issabel.
    """

    _global_serverip = None

    def __init__(self, amipool, dbpool, serverip, ip, mac):
        BaseEndpoint.__init__(self, "Avaya", amipool, dbpool, serverip, ip, mac)

        if Endpoint._global_serverip is None:
            Endpoint._global_serverip = serverip
        elif Endpoint._global_serverip != serverip:
            logging.warning(
                "Avaya global server IP is %s but endpoint %s requires %s",
                Endpoint._global_serverip,
                ip,
                serverip,
            )

    @staticmethod
    def updateGlobalConfig(serveriplist, amipool, endpoints):
        """Genera el archivo global que dirige al J129 a su archivo por MAC."""
        serverip = Endpoint._global_serverip
        if serverip is None and serveriplist:
            serverip = serveriplist[0]

        if serverip is None:
            logging.error("No hay IP de servidor disponible para Avaya")
            return False

        vars = {
            "server_ip": serverip,
            "phonesrv": BaseEndpoint._buildPhoneProv(serverip, "Avaya", "GLOBAL"),
        }
        config_path = issabel.BaseEndpoint.TFTP_DIR + "/46xxsettings.txt"

        try:
            BaseEndpoint._writeTemplate("Avaya_global_SIP.tpl", vars, config_path)
        except IOError as error:
            logging.error(
                "No se pudo escribir la configuración global Avaya %s - %s",
                config_path,
                str(error),
            )
            return False

        return True

    def updateLocalConfig(self):
        """Genera /tftpboot/<mac>.txt para un Avaya J129."""
        if len(self._accounts) <= 0:
            logging.error(
                "Endpoint %s@%s no tiene cuentas para configurar",
                self._vendorname,
                self._ip,
            )
            return False

        mac_sin_separadores = self._mac.lower().replace(":", "")
        config_filename = "%s.txt" % mac_sin_separadores
        config_path = self._tftpdir + "/" + config_filename

        vars = self._prepareVarList()
        vars["mac_address"] = self._mac
        vars["config_filename"] = config_filename

        try:
            self._writeTemplate("Avaya_J129.tpl", vars, config_path)
        except IOError as error:
            logging.error(
                "Endpoint %s@%s no pudo escribir %s - %s",
                self._vendorname,
                self._ip,
                config_path,
                str(error),
            )
            return False

        self._setConfigured()
        return True
