import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from pbip_generator.report_writer import ReportWriter
from visuals import (
    VisualBuildContext,
    build_visual,
    get_visual_definition,
    list_visual_definitions,
    validate_visual_bindings,
)


class VisualRegistryTests(unittest.TestCase):
    def setUp(self):
        self.fields = {
            "Sales_Table.SaleID": {
                "table": "Sales_Table",
                "name": "SaleID",
                "kind": "column",
            },
            "Sales_Table.Quantity": {
                "table": "Sales_Table",
                "name": "Quantity",
                "kind": "column",
            },
            "Sales_Table.Total Sales": {
                "table": "Sales_Table",
                "name": "Total Sales",
                "kind": "measure",
            },
        }
        self.visual = {
            "id": 15,
            "template_key": "tableEx",
            "name": "Sales Table",
            "x": 2,
            "y": 1,
            "w": 5,
            "h": 4,
            "visual_order": 2,
            "bindings": {
                "Values": [
                    self.fields["Sales_Table.SaleID"],
                    self.fields["Sales_Table.Quantity"],
                    self.fields["Sales_Table.Total Sales"],
                ]
            },
        }

    def test_registry_exposes_only_table(self):
        templates = list_visual_definitions()

        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["id"], "tableEx")
        self.assertEqual(templates[0]["template_key"], "tableEx")
        self.assertEqual(templates[0]["slot_definitions"][0]["role"], "Values")

    def test_table_builder_emits_pbir_projections_and_pixel_position(self):
        payload = build_visual(
            "tableEx",
            self.visual,
            VisualBuildContext(page_width=1280, page_height=720),
        )

        self.assertEqual(payload["name"], "visual_15")
        self.assertAlmostEqual(payload["position"]["x"], 1280 / 12 * 2)
        self.assertEqual(payload["position"]["y"], 90)
        self.assertAlmostEqual(payload["position"]["width"], 1280 / 12 * 5)
        self.assertEqual(payload["position"]["height"], 360)

        projections = payload["visual"]["query"]["queryState"]["Values"]["projections"]
        self.assertEqual(projections[0]["field"]["Column"]["Property"], "SaleID")
        self.assertEqual(projections[1]["field"]["Column"]["Property"], "Quantity")
        self.assertEqual(projections[2]["field"]["Measure"]["Property"], "Total Sales")
        self.assertEqual(projections[2]["queryRef"], "Sales_Table.Total Sales")

    def test_validation_rejects_missing_and_unknown_values(self):
        definition = get_visual_definition("tableEx")
        missing = validate_visual_bindings(definition, {**self.visual, "bindings": {}}, self.fields)
        unknown = validate_visual_bindings(
            definition,
            {
                **self.visual,
                "bindings": {
                    "Values": [
                        {
                            "table": "Sales_Table",
                            "name": "Missing",
                            "kind": "column",
                        }
                    ]
                },
            },
            self.fields,
        )

        self.assertEqual(missing, ["Missing required binding 'Values'."])
        self.assertIn("Sales_Table.Missing", unknown[0])

    def test_report_writer_packages_generated_visual_json(self):
        visual_json = build_visual(
            "tableEx",
            self.visual,
            VisualBuildContext(page_width=1280, page_height=720),
        )
        report = {
            "projectName": "Sales",
            "reportFolderName": "Sales.Report",
            "definitionPbir": {
                "version": "4.0",
                "datasetReference": {"byConnection": {"connectionString": "semantic-model"}},
            },
            "pages": [
                {
                    "name": "Page",
                    "page": {
                        "name": "Page",
                        "displayName": "Page",
                        "width": 1280,
                        "height": 720,
                    },
                    "visuals": [
                        {
                            "name": visual_json["name"],
                            "visual": visual_json,
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            ReportWriter(temp_dir).write(report, project_name="Sales")
            archive_path = Path(temp_dir) / "Sales.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for path in Path(temp_dir).rglob("*"):
                    if path.is_file() and path != archive_path:
                        archive.write(path, path.relative_to(temp_dir))

            with zipfile.ZipFile(archive_path) as archive:
                visual_path = "Sales.Report/definition/pages/Page/visuals/visual_15/visual.json"
                payload = json.loads(archive.read(visual_path))

        self.assertEqual(payload["visual"]["visualType"], "tableEx")
        self.assertNotIn("query", payload)
        self.assertEqual(
            len(payload["visual"]["query"]["queryState"]["Values"]["projections"]),
            3,
        )


if __name__ == "__main__":
    unittest.main()
