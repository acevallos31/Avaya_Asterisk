import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VAULT = ROOT / "deploy/endpoint-configurator/libs/EndpointCredentialVault.class.php"
SCHEMA = ROOT / "deploy/endpoint-configurator/db/001_admin_credentials.sql"
KEY_HELPER = ROOT / "deploy/endpoint-configurator/bin/install-key.sh"
VAULT_CLI = ROOT / "deploy/endpoint-configurator/bin/credential-vault-cli.php"
LAB_HELPER = ROOT / "deploy/j129/avaya-j129-lab-deploy"
RUNTIME_WORKFLOW = ROOT / ".github/workflows/lab-endpoint-credential-test68.yml"
MODULE_INDEX = ROOT / "var/www/html/modules/endpoint_configurator/index.php"
MODULE_TEMPLATE = ROOT / "var/www/html/modules/endpoint_configurator/themes/default/reporte_endpoints.tpl"
MODULE_JS = ROOT / "var/www/html/modules/endpoint_configurator/themes/default/js/javascript.js"


class EndpointCredentialFoundationTests(unittest.TestCase):
    def test_vault_uses_authenticated_encryption_and_external_key(self):
        text = VAULT.read_text(encoding="utf-8")
        self.assertIn("aes-256-gcm", text)
        self.assertIn("endpoint_credential_event", text)
        self.assertIn("/etc/issabel/endpoint-configurator.key", text)
        self.assertIn("openssl_random_pseudo_bytes", text)
        self.assertNotIn("var_dump", text.lower())
        self.assertNotIn("print_r", text.lower())

    def test_vault_never_exposes_plaintext_in_status(self):
        text = VAULT.read_text(encoding="utf-8")
        status = text[text.index("public function status"):text.index("public function createPendingGlobal")]
        self.assertNotRegex(status, r"SELECT[^;]*\\bciphertext\\b", re.I)

    def test_schema_contains_no_plaintext_credential_column(self):
        text = SCHEMA.read_text(encoding="utf-8")
        self.assertIn("ciphertext MEDIUMTEXT", text)
        self.assertNotRegex(text, r"(password|secret|passwd)\s+(?:VARCHAR|TEXT|CHAR)", re.I)

    def test_key_helper_is_private_and_idempotent(self):
        text = KEY_HELPER.read_text(encoding="utf-8")
        self.assertIn("umask 077", text)
        self.assertIn("root:apache:640", text)
        self.assertIn("chmod 0640", text)
        self.assertIn("if [[ -e", text)
        self.assertNotIn("echo \"$KEY_FILE\"", text)

    def test_csrf_token_is_loaded_in_render_scope(self):
        index = MODULE_INDEX.read_text(encoding="utf-8")
        render = index[index.index("function handleHTML_mainReport"):index.index("function handleJSON_unimplemented")]
        self.assertIn("$_SESSION[$module_name]['credential_csrf']", render)
        self.assertIn("'CREDENTIAL_CSRF'", render)

    def test_global_policy_write_is_csrf_protected_and_pending_only(self):
        index = MODULE_INDEX.read_text(encoding="utf-8")
        self.assertIn("handleJSON_saveCredentialPolicy", index)
        self.assertIn("hash_equals", index)
        self.assertIn("REQUEST_METHOD", index)
        self.assertIn("credential_csrf", index)
        self.assertIn("'status' => 'PENDING'", index)
        self.assertNotIn("applyconfig", index[index.index("handleJSON_saveCredentialPolicy"):index.index("function handleJSON_configStart")])

    def test_mac_override_is_encrypted_csrf_protected_and_pending_only(self):
        vault = VAULT.read_text(encoding="utf-8")
        index = MODULE_INDEX.read_text(encoding="utf-8")
        template = MODULE_TEMPLATE.read_text(encoding="utf-8")
        javascript = MODULE_JS.read_text(encoding="utf-8")
        self.assertIn("findEndpointIdByMac", vault)
        self.assertIn("createPendingOverride", vault)
        self.assertIn("clearOverride", vault)
        self.assertIn("CREATE_OVERRIDE", vault)
        self.assertIn("saveEndpointCredentialOverride", index)
        self.assertIn("clearEndpointCredentialOverride", index)
        override = index[index.index("function handleJSON_saveEndpointCredentialOverride"):index.index("function handleJSON_loadStatus")]
        self.assertIn("REQUEST_METHOD", override)
        self.assertIn("hash_equals", override)
        self.assertIn("findEndpointIdByMac", override)
        self.assertNotIn("applyconfig", override)
        self.assertIn("overrideMac", template)
        self.assertIn("saveEndpointOverride", javascript)
        self.assertIn("credential_csrf", javascript)

    def test_runtime_smoke_uses_encrypted_factory_credential_and_lab_runner_only(self):
        vault = VAULT.read_text(encoding="utf-8")
        cli = VAULT_CLI.read_text(encoding="utf-8")
        helper = LAB_HELPER.read_text(encoding="utf-8")
        workflow = RUNTIME_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pendingCredentialForValidation", vault)
        self.assertIn("markEndpointValidated", vault)
        self.assertIn("stream_get_contents(STDIN", cli)
        self.assertNotIn("echo $password", cli)
        self.assertIn("createPendingFactory", vault)
        self.assertIn("'FACTORY'", vault)
        self.assertIn("store-factory", cli)
        self.assertIn("store-factory EC:74:D7:1E:E8:E3", helper)
        self.assertIn("credential-status-grp2601p", helper)
        self.assertIn("avaya-j129-lab-deploy credential-status-grp2601p", workflow)
        self.assertNotIn("sudo /usr/local/libexec/issabel-endpoint-credential-vault", workflow)
        self.assertIn("credential-smoke-grp2601p", helper)
        self.assertIn("phone_write=NO", helper)
        self.assertIn("runs-on: [self-hosted, Linux, X64, issabel-lab]", workflow)
        self.assertIn('"deploy/endpoint-configurator/**"', workflow)
        self.assertNotIn("j129-production", workflow)
        self.assertIn("GRANDSTREAM_GRP2601P_EC74D71EE8E3_HTTP_PASSWORD", workflow)
        self.assertNotIn("rollback-endpoint-credentials", workflow)

    def test_factory_csv_import_is_csrf_protected_bounded_and_phone_write_free(self):
        vault = VAULT.read_text(encoding="utf-8")
        index = MODULE_INDEX.read_text(encoding="utf-8")
        template = MODULE_TEMPLATE.read_text(encoding="utf-8")
        javascript = MODULE_JS.read_text(encoding="utf-8")
        self.assertIn("importPendingFactoryCsv", vault)
        self.assertIn("START TRANSACTION", vault)
        self.assertIn("ROLLBACK", vault)
        self.assertIn("count($rows) >= 100", vault)
        self.assertIn("handleJSON_importFactoryCredentialsCsv", index)
        self.assertIn("is_uploaded_file", index)
        self.assertIn("hash_equals", index)
        self.assertIn("@unlink($upload['tmp_name'])", index)
        self.assertIn("credential-factory-csv", template)
        self.assertIn("FormData", javascript)
        self.assertIn("importFactoryCredentialsCsv", javascript)
        self.assertNotIn("applyconfig", index[index.index("function handleJSON_importFactoryCredentialsCsv"):])

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
