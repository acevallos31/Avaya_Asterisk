import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "var/www/html/modules/endpoint_configurator/dialogs/summary/index.php"
TEMPLATE = ROOT / "var/www/html/modules/endpoint_configurator/themes/default/reporte_endpoints.tpl"


class EndpointMainAccountStatusTests(unittest.TestCase):
    def test_summary_dialog_is_read_only_and_auto_loadable(self):
        text = SUMMARY.read_text(encoding="utf-8")
        self.assertIn("class Dialog_Summary", text)
        self.assertIn("static function templateContent", text)
        self.assertIn("handleJSON_loadAll", text)
        self.assertIn("SELECT ea.id_endpoint, ea.tech, ea.account", text)
        self.assertIn("sip show peers", text)
        self.assertIn("iax2 show peers", text)
        self.assertIn("pjsip show contacts", text)
        self.assertNotIn("UPDATE endpoint", text)
        self.assertNotIn("DELETE FROM endpoint", text)
        self.assertNotIn("applyconfig", text)

    def test_main_table_renders_account_registration_column(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("endpoint-account-summary-header", text)
        self.assertIn("endpoint-account-summary-id", text)
        self.assertIn("endpoint-account-summary-body", text)
        self.assertIn("action: 'summary_loadAll'", text)
        self.assertIn("summaryLabels.not_assigned", text)
        self.assertIn("summaryLabels.registered", text)
        self.assertIn("summaryLabels.not_registered", text)
        self.assertIn("summaryLabels.registration_unknown", text)
        self.assertIn('colspan="8"', text)


if __name__ == "__main__":
    unittest.main()
