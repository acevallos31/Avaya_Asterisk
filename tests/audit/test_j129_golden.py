import unittest

from tests.audit.support import RepositoryTextSource


DEPLOY_ROOT = "deploy/j129"
AVAYA = DEPLOY_ROOT + "/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
J129_TEMPLATE = DEPLOY_ROOT + "/usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl"
GLOBAL_TEMPLATE = DEPLOY_ROOT + "/usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl"
REFERENCE_AVAYA = (
    "audit/production-reference/avaya_files_audit/files/usr/share/issabel/"
    "endpoint-classes/class/issabel/vendor/Avaya.py"
)
REFERENCE_GLOBAL = (
    "audit/production-reference/avaya_files_audit/files/usr/share/issabel/"
    "endpoint-classes/tpl/Avaya_global_SIP.tpl"
)


class J129ProductionReferenceTests(unittest.TestCase):
    """Protege el comportamiento J129 observado en la implementación histórica."""

    @classmethod
    def setUpClass(cls):
        repo = RepositoryTextSource()
        cls.reference_vendor = repo.read(REFERENCE_AVAYA)
        cls.reference_global = repo.read(REFERENCE_GLOBAL)

    def test_reference_uses_mac_specific_settings_file(self):
        self.assertIn("GET $MACADDR.txt", self.reference_global)

    def test_reference_contains_j129_forced_sip_credentials(self):
        for parameter in (
            "FORCE_SIP_USERNAME",
            "FORCE_SIP_PASSWORD",
            "FORCE_SIP_EXTENSION",
        ):
            self.assertIn(parameter, self.reference_vendor)

    def test_reference_normalizes_mac_for_per_phone_filename(self):
        self.assertIn('.lower().replace(":", "")', self.reference_vendor)
        self.assertIn('/tftpboot/{mac_sin_separadores}.txt', self.reference_vendor)


class J129TargetGoldenContractTests(unittest.TestCase):
    """Contrato objetivo para el overlay J129 nativo de Issabel."""

    @classmethod
    def setUpClass(cls):
        repo = RepositoryTextSource()
        cls.vendor = repo.read(AVAYA)
        cls.template = repo.read(J129_TEMPLATE)
        cls.global_template = repo.read(GLOBAL_TEMPLATE)

    def test_j129_template_uses_issabel_sip_account_objects(self):
        self.assertIn("for extension in sip", self.template)
        self.assertIn("extension.extension", self.template)
        self.assertIn("extension.secret", self.template)
        self.assertIn("extension.description", self.template)

    def test_j129_template_emits_required_force_sip_parameters(self):
        self.assertIn("FORCE_SIP_USERNAME", self.template)
        self.assertIn("FORCE_SIP_PASSWORD", self.template)
        self.assertIn("FORCE_SIP_EXTENSION", self.template)

    def test_j129_template_is_avaya_set_syntax_not_generic_ini(self):
        forbidden_sections = ("[GENERAL]", "[NETWORK]", "[PROVISIONING]")
        found = [section for section in forbidden_sections if section in self.template]
        self.assertEqual([], found)
        self.assertIn("SET SIPDOMAIN", self.template)

    def test_global_template_does_not_embed_endpoint_credentials(self):
        forbidden = (
            "SIPUSERNAME {{extension.extension}}",
            "SIPPASSWORD {{extension.secret}}",
            "DISPLAY_NAME {{extension.description}}",
            "AUTHNAME {{extension.account}}",
        )
        found = [token for token in forbidden if token in self.global_template]
        self.assertEqual(
            [],
            found,
            "Global J129 provisioning must not contain per-endpoint SIP credentials: %r" % found,
        )
        self.assertIn("GET $MACADDR.txt", self.global_template)

    def test_vendor_prepares_standard_issabel_template_variables(self):
        self.assertIn("_prepareVarList", self.vendor)
        self.assertIn("_writeTemplate", self.vendor)

    def test_golden_fixture_uses_only_fake_credentials(self):
        golden = {
            "mac": "C8:1F:EA:AA:BB:CC",
            "phone_ip": "192.0.2.100",
            "server_ip": "192.0.2.10",
            "extension": "4200",
            "secret": "TEST-SIP-SECRET-NOT-REAL",
        }
        expected_lines = (
            'SET FORCE_SIP_USERNAME "4200"',
            'SET FORCE_SIP_PASSWORD "TEST-SIP-SECRET-NOT-REAL"',
            'SET FORCE_SIP_EXTENSION "4200"',
        )

        self.assertTrue(golden["mac"].startswith("C8:1F:EA"))
        self.assertEqual("c81feaaabbcc", golden["mac"].replace(":", "").lower())
        self.assertEqual(3, len(expected_lines))
        self.assertNotIn("default_secret", "\n".join(expected_lines))


if __name__ == "__main__":
    unittest.main()
