import MySQLdb
import socket
import datetime
from issabel.BaseEndpoint import BaseEndpoint

class Endpoint(BaseEndpoint):
    def __init__(self, amipool, dbpool, serverip, ip, mac, ext=None, secret=None):
        super().__init__("Avaya", amipool, dbpool, serverip, ip, mac)
        if self._vendorname.lower() == "avaya":
         self.mac = mac
         self.ext = self.get_extension_from_db()
         self.secret = self.get_secret_from_db()
         self.displayname = self.get_displayname_from_db(self.ext)
         print(f"DEBUG: Display Name asignado en Endpoint -> {self.displayname}")
         self.serverip = self.get_local_ip()  # Obtiene automáticamente la IP del servidor Issabel
         print(f"DEBUG: Creando endpoint Avaya con MAC {mac}, IP {ip}, Ext {ext}, ServerIP {self.serverip}")
         authtoken = self._buildPhoneProv(self.serverip, "Avaya", mac)
        self._setConfigured()

    def get_local_ip(self):
        """ Obtiene la dirección IP del servidor Issabel en la red local. """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Usa Google DNS para determinar la IP local
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            print(f"Error obteniendo la IP del servidor: {e}")
            return "127.0.0.1"

    def get_extension_from_db(self):
        print(f"⚡ DEBUG: Se está ejecutando get_extension_from_db() para MAC {self.mac}")
        """ Obtiene la extensión desde la base de datos Asterisk """
        print("Ejecutando get_extension_from_db()")
        try:
            conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="dcmhr99!",
            db="endpointconfig"
        )
            cursor = conn.cursor()

            print(f"DEBUG: Buscando extensión para MAC: {self.mac}")

            query = """
            SELECT ea.account 
            FROM endpoint_account ea 
            JOIN endpoint e ON ea.id_endpoint = e.id 
            WHERE LOWER(e.mac_address) = LOWER(%s) 
            LIMIT 1
            """
            print(f"DEBUG: Ejecutando consulta SQL -> {query} con parámetro: {self.mac}")

            cursor.execute(query, (self.mac,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
               print(f" DEBUG: Extensión obtenida para {self.mac} -> {result[0]}")
               return result[0]               
            else:
               print(f" No se encontró extensión para {self.mac}, usando default_ext")
               print(f" DEBUG: Esta es la Extensión obtenida para {self.mac} -> {result}")
               return "default_ext"

        except MySQLdb.Error as e:
            print(f" Error en la consulta SQL: {e}")
            return "default_ext"

        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            print(f"⚠️ No se encontró extensión para {self.mac}, usando default_ext")
            return "default_ext"

    def get_displayname_from_db(self, extension):
        """Obtiene el Display Name desde la base de datos de Asterisk."""
        try:
            conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="adm99!",
            database="asterisk"
        )
            cursor = conn.cursor()

            query = "SELECT name FROM users WHERE extension = %s LIMIT 1"
            print(f"DEBUG: Ejecutando consulta SQL -> {query} con parámetro: {extension}")

            cursor.execute(query, (extension,))
            result = cursor.fetchone()
            print(f"DEBUG: Resultado de la consulta: {result}")

            cursor.close()
            conn.close()

            if result:
               print(f"DEBUG: Display Name obtenido de la base de datos para {extension} -> {result[0]}")
               return result[0]  # Retorna el nombre del usuario
            else:
                print(f"DEBUG: No se encontró Display Name para {extension}, usando extensión como fallback")
                return 'no_Hay'  # Si no hay nombre, usa la extensión

        except Exception as e:
            print(f"Error obteniendo el Display Name de la extensión {extension}: {e}")
            return extension


    def get_secret_from_db(self):
        """ Obtiene la contraseña SIP asociada a la extensión desde la base de datos Asterisk """
        print(" Ejecutando get_secret_from_db()")
        try:
            conn = MySQLdb.connect(host="localhost", user="root", password="dcmhr99!", database="asterisk")
            cursor = conn.cursor()
            query = f"SELECT data FROM sip WHERE keyword='secret' AND id='{self.ext}' LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            print(f"DEBUG: Extensión obtenida para {self.mac} -> {result}")
            return result[0] if result else "default_secret"
        except Exception as e:
            print(f"Error obteniendo la contraseña de la base de datos: {e}")
            return "default_secret"

    def updateLocalConfig(self):
        print("Ejecutando updateLocalConfig en Avaya")
        """ Genera el archivo de configuración para el Avaya J129 basado en la MAC del teléfono. """
        
        mac_sin_separadores = self.mac.lower().replace(":", "")  # Convierte la MAC a minúsculas y sin ":"
        config_filename = f"/tftpboot/{mac_sin_separadores}.txt"  # Nombre de archivo sin ":" y en minúsculas
        fecha_actual = datetime.datetime.now().strftime("%Y-%b-%d %H:%M:%S")  # Formato: Año-Mes-Día Hora:Minuto:Segundo (ej. 2025-Mar-06 16:45:30)

        try:
            print(f"DEBUG: MAC -> {self.mac}")
            print(f"DEBUG: Extensión obtenida: {self.ext}")
            print(f"DEBUG: Contraseña obtenida: {self.secret}")
            print(f"DEBUG: Archivo generado -> {config_filename}")
            with open(config_filename, "w") as config_file:
                config_file.write(f"## Configuración Específica de Extensión SIP {self.ext} para Avaya J129 {self.mac}\n")
                config_file.write(f"## Última actualización: {fecha_actual}\n\n")

                config_file.write("###################################\n")
                config_file.write("## Configuración de Servidor SIP ##\n")
                config_file.write("###################################\n")
                config_file.write(f"SET SIP_CONTROLLER_LIST \"{self.serverip}:5060;transport=udp\"\n")
                config_file.write(f"SET SIPPROXYSRVR {self.serverip}\n")
                config_file.write(f"SET SIPPROXYSRVR_IN_USE {self.serverip}\n")
                config_file.write(f"SET SIPDOMAIN {self.serverip}\n")
                config_file.write(f"SET SIPPORT 5060\n")
                config_file.write("SET ENABLE_PRESENCE 1\n\n")

                config_file.write("############################################\n")
                config_file.write(f"## Configuración de la Extensión SIP {self.ext} ##\n")
                config_file.write("############################################\n")
                config_file.write(f"SET DISPLAY_NAME \"{self.displayname}\"\n")  #  Display Name 
                config_file.write(f"SET SIP_USER_ID {self.ext}\n")
                config_file.write(f"SET SIP_USER_ACCOUNT {self.ext}@{self.serverip}\n")
                config_file.write("SET ENABLE_SIP_USER_ID 1\n")
                config_file.write("SET SCREEN_NAME_ORDER 1\n\n")
                config_file.write(f"SET  FORCE_SIP_USERNAME \"{self.ext}\"\n")
                config_file.write(f"SET  FORCE_SIP_PASSWORD \"{self.secret}\"\n")
                config_file.write(f"SET  FORCE_SIP_EXTENSION \"{self.ext}\"\n")
                config_file.write("## Cargar archivo de configuración por MAC (si se usa TFTP o HTTP para provisión)\n")
                config_file.write("## Agencia La Mundial\n")

            print(f"DEBUG: Archivo de configuración generado en {config_filename}")
            return True

        except Exception as e:
            print(f"Error generando configuración para {self.mac}: {e}")
            return False
