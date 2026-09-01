import ast
import unittest
from pathlib import Path

from tests.audit.support import RepositoryTextSource


DEPLOY_ROOT = "deploy/j129"
AVAYA = DEPLOY_ROOT + "/usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py"


class DeploymentBoundaryTests(unittest.TestCase):
    """OCP/SRP: el despliegue J129 debe ser un overlay, no un fork del core Issabel."""

    @classmethod
    def setUpClass(cls):
        cls.repo = RepositoryTextSource()
        cls.root = Path(__file__).resolve().parents[2] / DEPLOY_ROOT

    def test_overlay_does_not_ship_issabel_core_executable(self):
        self.assertFalse((self.root / "usr/bin/issabel-endpointconfig").exists())

    def test_overlay_does_not_ship_foundation_classes(self):
        forbidden = (
            self.root / "usr/share/issabel/endpoint-classes/class/issabel/BaseEndpoint.py",
            self.root / "usr/share/issabel/endpoint-classes/class/issabel/Extension.py",
        )
        self.assertEqual([], [str(path) for path in forbidden if path.exists()])

    def test_overlay_does_not_ship_legacy_php_vendor_path(self):
        legacy = self.root / "var/www/html/modules/endpoint_configurator/phonesrv/vendor/Avaya.class.php"
        self.assertFalse(legacy.exists())


class AvayaVendorContractTests(unittest.TestCase):
    """SRP/LSP/DIP: Avaya adapta provisionamiento usando el contrato estándar."""

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

    def test_vendor_uses_standard_account_template_pipeline(self):
        self.assertIn("_prepareVarList", self.source)
        self.assertIn("_writeTemplate", self.source)
        self.assertIn("self._accounts", self.source)

    def test_vendor_implements_standard_model_probe(self):
        self.assertIn("def probeModel(self):", self.source)
        self.assertIn("self._saveModel(\"J129\")", self.source)

    def test_j129_probe_is_restricted_to_known_j129_oui(self):
        self.assertIn("C8:1F:EA", self.source)
        self.assertIn("self._mac", self.source)

    def test_vendor_does_not_hardcode_database_model_id(self):
        self.assertNotIn("147", self.source)


if __name__ == "__main__":
    unittest.main()
