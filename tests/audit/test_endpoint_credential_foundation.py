import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VAULT = ROOT / "deploy/endpoint-configurator/libs/EndpointCredentialVault.class.php"
SCHEMA = ROOT / "deploy/endpoint-configurator/db/001_admin_credentials.sql"
KEY_HELPER = ROOT / "deploy/endpoint-configurator/bin/install-key.sh"
MODULE_INDEX = ROOT / "var/www/html/modules/endpoint_configurator/index.php"
MODULE_TEMPLATE = ROOT / "var/www/html/modules/endpoint_configurator/themes/default/reporte_endpoints.tpl"
MODULE_JS = ROOT / "var/www/html/modules/endpoint_configurator/themes/default/js/javascript.js"


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

    def test_global_policy_write_is_csrf_protected_and_pending_only(self):
        index = MODULE_INDEX.read_text(encoding="utf-8")
        self.assertIn("handleJSON_saveCredentialPolicy", index)
        self.assertIn("hash_equals", index)
        self.assertIn("credential_csrf", index)
        self.assertIn("'status' => 'PENDING'", index)
        self.assertNotIn("applyconfig", index[index.index("handleJSON_saveCredentialPolicy"):index.index("function handleJSON_configStart")])

    def test_security_view_does_not_render_a_secret(self):
        template = MODULE_TEMPLATE.read_text(encoding="utf-8")
        javascript = MODULE_JS.read_text(encoding="utf-8")
        self.assertIn("endpoints/security", template)
        self.assertIn("type=\"password\"", template)
        self.assertIn("credential_csrf", template)
        self.assertIn("action: 'saveCredentialPolicy'", javascript)
        self.assertNotIn("policy.ciphertext", template)

if __name__ == "__main__":
    unittest.main()
