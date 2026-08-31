import re
import unittest
from pathlib import Path

from tests.audit.support import RepositoryTextSource


TARGET_AVAYA = "usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
SNAPSHOT_ROOT = "audit/production-reference/avaya_files_audit"
SNAPSHOT_AVAYA = SNAPSHOT_ROOT + "/files/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
SNAPSHOT_PHP = SNAPSHOT_ROOT + "/files/var/www/html/modules/endpoint_configurator/phonesrv/vendor/Avaya.class.php"


class SecurityAuditTests(unittest.TestCase):
    """Security boundaries: repository code must not embed operational secrets."""

    @classmethod
    def setUpClass(cls):
        cls.repo = RepositoryTextSource()

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

    def test_snapshot_contains_no_python_bytecode(self):
        root = Path(__file__).resolve().parents[2] / SNAPSHOT_ROOT
        pyc_files = list(root.rglob("*.pyc"))
        self.assertEqual([], pyc_files, "Audit snapshot must not store Python bytecode")

    def test_php_snapshot_does_not_log_sip_secret(self):
        text = self.repo.read(SNAPSHOT_PHP)
        secret_log = re.search(r"error_log\([^\n]*Secret:\s*\$secret", text, flags=re.I)
        self.assertIsNone(secret_log, "Avaya.class.php writes SIP credentials to application logs")


if __name__ == "__main__":
    unittest.main()
