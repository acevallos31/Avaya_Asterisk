import ast
import unittest

from tests.audit.support import RepositoryTextSource


CORE = "usr/bin/issabel-endpointconfig"
AVAYA = "usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"
BASE = "usr/share/issabel/endpoint-classes/class/issabel/BaseEndpoint.py"
EXTENSION = "usr/share/issabel/endpoint-classes/class/issabel/Extension.py"


class CorePipelineContractTests(unittest.TestCase):
    """OCP/DIP: the core must not know Avaya-specific credential details."""

    @classmethod
    def setUpClass(cls):
        cls.repo = RepositoryTextSource()
        cls.core = cls.repo.read(CORE)

    def test_core_keeps_standard_account_pipeline(self):
        self.assertIn("endpoint.setAccountList(endpointList[ip]['accounts'])", self.core)

    def test_core_has_no_avaya_specific_branch(self):
        forbidden = (
            'manufacturer") == "Avaya"',
            "manufacturer') == 'Avaya'",
            'manufacturer"] == "Avaya"',
            "manufacturer'] == 'Avaya'",
        )
        matches = [token for token in forbidden if token in self.core]
        self.assertEqual([], matches, "Core contains vendor-specific Avaya logic: %r" % matches)

    def test_core_does_not_extract_secret_directly_from_endpoint_dict(self):
        forbidden = ("default_secret", ".get(\"secret\"", ".get('secret'")
        matches = [token for token in forbidden if token in self.core]
        self.assertEqual([], matches, "Core bypasses the account/Extension pipeline: %r" % matches)


class AvayaVendorContractTests(unittest.TestCase):
    """SRP/LSP/DIP: Avaya adapts provisioning, not Issabel database internals."""

    @classmethod
    def setUpClass(cls):
        cls.repo = RepositoryTextSource()
        cls.source = cls.repo.read(AVAYA)
        cls.tree = ast.parse(cls.source)

    def _endpoint_init_args(self):
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "Endpoint":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        return [arg.arg for arg in item.args.args]
        self.fail("Endpoint.__init__ was not found in Avaya.py")

    def test_constructor_preserves_base_endpoint_contract(self):
        self.assertEqual(
            ["self", "amipool", "dbpool", "serverip", "ip", "mac"],
            self._endpoint_init_args(),
        )

    def test_vendor_does_not_open_its_own_mysql_connections(self):
        self.assertNotIn("MySQLdb.connect", self.source)

    def test_vendor_does_not_depend_on_google_dns_to_find_server_ip(self):
        self.assertNotIn("8.8.8.8", self.source)

    def test_stock_foundation_classes_are_present(self):
        self.assertTrue(self.repo.exists(BASE))
        self.assertTrue(self.repo.exists(EXTENSION))


if __name__ == "__main__":
    unittest.main()
