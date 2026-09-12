import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VAULT = ROOT / "deploy/endpoint-configurator/libs/EndpointCredentialVault.class.php"
SCHEMA = ROOT / "deploy/endpoint-configurator/db/001_admin_credentials.sql"
KEY_HELPER = ROOT / "deploy/endpoint-configurator/bin/install-key.sh"


class EndpointCredentialFoundationTests(unittest.TestCase):
    def test_vault_uses_authenticated_encryption_and_external_key(self):
        text = VAULT.read_text(encoding="utf-8")
        self.assertIn("aes-256-gcm", text)
        self.assertIn("/etc/issabel/endpoint-configurator.key", text)
        self.assertIn("openssl_random_pseudo_bytes", text)
        self.assertNotIn("var_dump", text.lower())
        self.assertNotIn("print_r", text.lower())

    def test_vault_never_exposes_plaintext_in_status(self):
        text = VAULT.read_text(encoding="utf-8")
        status = text[text.index("public function status"):text.index("public function createPendingGlobal")]
        self.assertNotRegex(status, r"SELECT[^;]*(?:password|ciphertext)", re.I)

    def test_schema_contains_no_plaintext_credential_column(self):
        text = SCHEMA.read_text(encoding="utf-8")
        self.assertIn("ciphertext MEDIUMTEXT", text)
        self.assertNotRegex(text, r"(password|secret|passwd)\s+(?:VARCHAR|TEXT|CHAR)", re.I)

    def test_key_helper_is_private_and_idempotent(self):
        text = KEY_HELPER.read_text(encoding="utf-8")
        self.assertIn("umask 077", text)
        self.assertIn("chmod 0600", text)
        self.assertIn("if [[ -e", text)
        self.assertNotIn("echo \"$KEY_FILE\"", text)


if __name__ == "__main__":
    unittest.main()
