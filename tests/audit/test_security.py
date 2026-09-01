import re
import unittest
from pathlib import Path

from tests.audit.support import RepositoryTextSource


DEPLOY_ROOT = "deploy/j129"
TARGET_AVAYA = DEPLOY_ROOT + "/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
SNAPSHOT_ROOT = "audit/production-reference/avaya_files_audit"
SNAPSHOT_AVAYA = SNAPSHOT_ROOT + "/files/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"


class SecurityAuditTests(unittest.TestCase):
    """Límites de seguridad del artefacto que sí será desplegado."""

    @classmethod
    def setUpClass(cls):
        cls.repo = RepositoryTextSource()
        cls.deploy_root = Path(__file__).resolve().parents[2] / DEPLOY_ROOT

    def test_sanitized_snapshot_does_not_keep_literal_mysql_passwords(self):
        text = self.repo.read(SNAPSHOT_AVAYA)
        assignments = re.findall(r"(?:passwd|password)\s*=\s*[\"']([^\"']+)[\"']", text, flags=re.I)
        unsafe = [value for value in assignments if value not in ("XXXXXXXX",)]
        self.assertEqual([], unsafe, "Sanitized audit snapshot still contains literal DB credentials")

    def test_target_avaya_has_no_literal_mysql_password_arguments(self):
        text = self.repo.read(TARGET_AVAYA)
        assignments = re.findall(r"(?:passwd|password)\s*=\s*[\"']([^\"']+)[\"']", text, flags=re.I)
        unsafe = [value for value in assignments if value not in ("XXXXXXXX",)]
        self.assertEqual([], unsafe, "Target Avaya.py contains hard-coded database credentials")

    def test_target_avaya_does_not_log_sip_secrets(self):
        text = self.repo.read(TARGET_AVAYA)
        forbidden = ("secret}", "self.secret", "extension.secret")
        log_lines = [line for line in text.splitlines() if "logging." in line.lower()]
        leaked = [line for line in log_lines if any(token in line for token in forbidden)]
        self.assertEqual([], leaked, "El overlay registra secretos SIP: %r" % leaked)

    def test_overlay_contains_no_legacy_php_vendor(self):
        legacy = self.deploy_root / "var/www/html/modules/endpoint_configurator/phonesrv/vendor/Avaya.class.php"
        self.assertFalse(legacy.exists())

    def test_overlay_contains_no_python_bytecode(self):
        pyc_files = list(self.deploy_root.rglob("*.pyc"))
        self.assertEqual([], pyc_files, "El overlay no debe almacenar bytecode Python")


if __name__ == "__main__":
    unittest.main()
