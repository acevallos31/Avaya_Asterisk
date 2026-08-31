import unittest

from tests.audit.support import RepositoryTextSource


AVAYA = "usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
J129_TEMPLATE = "usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl"
GLOBAL_TEMPLATE = "usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl"


class J129ProductionReferenceTests(unittest.TestCase):
    """Protect behavior that is known to be useful from the historical implementation.

    These tests do not endorse the current architecture. They only prevent a refactor
    from accidentally deleting the J129 provisioning semantics that made the phones
    work.
    """

    @classmethod
    def setUpClass(cls):
        repo = RepositoryTextSource()
        cls.vendor = repo.read(AVAYA)
        cls.global_template = repo.read(GLOBAL_TEMPLATE)

    def test_reference_uses_mac_specific_settings_file(self):
        self.assertIn("GET $MACADDR.txt", self.global_template)

    def test_reference_contains_j129_forced_sip_credentials(self):
        for parameter in (
            "FORCE_SIP_USERNAME",
            "FORCE_SIP_PASSWORD",
            "FORCE_SIP_EXTENSION",
        ):
            self.assertIn(parameter, self.vendor)

    def test_reference_normalizes_mac_for_per_phone_filename(self):
        self.assertIn('.lower().replace(":", "")', self.vendor)
        self.assertIn('/tftpboot/{mac_sin_separadores}.txt', self.vendor)


class J129TargetGoldenContractTests(unittest.TestCase):
    """Target contract for the Issabel-native J129 refactor.

    Some assertions are expected to fail before the refactor. This is intentional:
    they define the desired architecture before production logic is changed.
    """

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
