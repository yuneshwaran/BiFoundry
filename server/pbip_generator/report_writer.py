import json
import os
import base64
from copy import deepcopy


class ReportWriter:
    DEFAULT_REPORT_NAME = "MyProject"
    DEFAULT_REPORT_VERSION = "4.0"
    PBIR_SCHEMA_URL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"
    REPORT_VERSION_SCHEMA_URL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"
    REPORT_JSON_SCHEMA_URL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json"
    PAGES_JSON_SCHEMA_URL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
    PAGE_JSON_SCHEMA_URL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
    RESERVED_PAGE_FILENAMES = {"page.json"}
    RESERVED_VISUAL_FILENAMES = {"visual.json"}
    RESERVED_REPORT_DEFINITION_FILENAMES = {"report.json", "version.json", "pages.json"}

    def __init__(self, base_path):
        self.base_path = base_path

    def write(self, report, project_name=None, dataset_reference=None):
        project_name = project_name or report.get("projectName") or self.DEFAULT_REPORT_NAME
        report_folder_name = self._resolve_report_folder_name(report, project_name)
        semantic_model_folder = self._resolve_semantic_model_folder_name(report, project_name)

        report_path = os.path.join(self.base_path, report_folder_name)
        definition_path = os.path.join(report_path, "definition")
        pages_root = os.path.join(definition_path, "pages")
        static_resources_path = os.path.join(report_path, "StaticResources")

        os.makedirs(pages_root, exist_ok=True)

        definition_pbir = self._build_definition_pbir(
            report=report,
            semantic_model_folder=semantic_model_folder,
            dataset_reference=dataset_reference,
        )
        self._write_json_file(os.path.join(report_path, "definition.pbir"), definition_pbir)

        report_json = self._extract_json_payload(
            report,
            candidate_keys=("report", "reportJson", "report_json", "raw_report"),
            nested_paths=(
                ("definition", "report"),
                ("definition", "report.json"),
                ("raw", "definition", "report"),
                ("raw", "definition", "report.json"),
            ),
        )
        if report_json is None:
            report_json = self._build_default_report_json()
        self._write_json_file(os.path.join(definition_path, "report.json"), report_json)

        version_json = self._extract_json_payload(
            report,
            candidate_keys=("version", "versionJson", "version_json"),
            nested_paths=(
                ("definition", "version"),
                ("definition", "version.json"),
                ("raw", "definition", "version"),
                ("raw", "definition", "version.json"),
            ),
        )
        if version_json is None:
            version_json = self._build_default_version_json()
        self._write_json_file(os.path.join(definition_path, "version.json"), version_json)

        pages = self._extract_pages(report)
        pages_json = self._build_pages_metadata(report, pages)
        self._write_json_file(os.path.join(pages_root, "pages.json"), pages_json)
        self._write_additional_json_assets(
            definition_path,
            self._extract_report_definition_files(report),
            skip_filenames=self.RESERVED_REPORT_DEFINITION_FILENAMES,
        )
        self._write_additional_json_assets(
            static_resources_path,
            self._extract_static_resource_files(report),
        )
        self._write_support_assets(
            report_path,
            self._extract_support_files(report),
        )

        for page in pages:
            self._write_page(pages_root, page)

    def _write_page(self, pages_root, page):
        page_name = self._resolve_page_name(page)
        page_path = os.path.join(pages_root, page_name)
        visuals_path = os.path.join(page_path, "visuals")

        os.makedirs(visuals_path, exist_ok=True)

        page_json = self._extract_page_json(page)
        self._write_json_file(os.path.join(page_path, "page.json"), page_json)
        self._write_additional_json_assets(
            page_path,
            self._extract_page_files(page),
            skip_filenames=self.RESERVED_PAGE_FILENAMES,
        )

        for visual in self._extract_visuals(page):
            self._write_visual(visuals_path, visual)

    def _write_visual(self, visuals_path, visual):
        visual_name = self._resolve_visual_name(visual)
        visual_path = os.path.join(visuals_path, visual_name)
        os.makedirs(visual_path, exist_ok=True)

        visual_json = self._extract_visual_json(visual)
        self._write_json_file(os.path.join(visual_path, "visual.json"), visual_json)
        self._write_additional_json_assets(
            visual_path,
            self._extract_visual_files(visual),
            skip_filenames=self.RESERVED_VISUAL_FILENAMES,
        )

    def _build_definition_pbir(self, report, semantic_model_folder, dataset_reference=None):
        existing = self._extract_json_payload(
            report,
            candidate_keys=("definitionPbir", "definition_pbir", "pbir"),
            nested_paths=(
                ("definition.pbir",),
                ("raw", "definition.pbir"),
            ),
        )
        if isinstance(existing, dict):
            return deepcopy(existing)

        reference = dataset_reference
        if reference is None:
            reference = self._extract_dataset_reference(report)

        if reference is None:
            reference = {
                "byPath": {
                    "path": f"../{semantic_model_folder}"
                }
            }

        return {
            "$schema": self.PBIR_SCHEMA_URL,
            "version": report.get("pbirVersion", self.DEFAULT_REPORT_VERSION),
            "datasetReference": deepcopy(reference),
        }

    def _extract_dataset_reference(self, report):
        candidate = self._deep_get(report, ("datasetReference",))
        if isinstance(candidate, dict):
            return candidate

        for path in (
            ("definitionPbir", "datasetReference"),
            ("definition_pbir", "datasetReference"),
            ("pbir", "datasetReference"),
            ("definition.pbir", "datasetReference"),
            ("raw", "definition.pbir", "datasetReference"),
        ):
            candidate = self._deep_get(report, path)
            if isinstance(candidate, dict):
                return candidate

        return None

    def _build_pages_metadata(self, report, pages):
        existing = self._extract_json_payload(
            report,
            candidate_keys=("pagesMetadata", "pagesJson", "pages_json"),
            nested_paths=(
                ("definition", "pages"),
                ("definition", "pages.json"),
                ("raw", "definition", "pages"),
                ("raw", "definition", "pages.json"),
            ),
        )
        if isinstance(existing, dict):
            return deepcopy(existing)

        page_order = [self._resolve_page_name(page) for page in pages]
        active_page_name = report.get("activePageName")

        if not active_page_name and pages:
            active_page_name = self._resolve_page_name(pages[0])

        payload = {"pageOrder": page_order}
        if active_page_name:
            payload["activePageName"] = active_page_name

        payload["$schema"] = self.PAGES_JSON_SCHEMA_URL
        return payload

    def _build_default_version_json(self):
        return {
            "$schema": self.REPORT_VERSION_SCHEMA_URL,
            "version": "2.0.0",
        }

    def _build_default_report_json(self):
        return {
            "$schema": self.REPORT_JSON_SCHEMA_URL,
            "themeCollection": {
                "baseTheme": {
                    "name": "CY26SU04",
                    "reportVersionAtImport": {
                        "visual": "2.8.0",
                        "report": "3.2.0",
                        "page": "2.3.1",
                    },
                    "type": "SharedResources",
                }
            },
            "objects": {
                "section": [
                    {
                        "properties": {
                            "verticalAlignment": {
                                "expr": {
                                    "Literal": {
                                        "Value": "'Top'"
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "resourcePackages": [
                {
                    "name": "SharedResources",
                    "type": "SharedResources",
                    "items": [
                        {
                            "name": "CY26SU04",
                            "path": "BaseThemes/CY26SU04.json",
                            "type": "BaseTheme",
                        }
                    ],
                }
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "AllowSummarized",
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
                "useDefaultAggregateDisplayName": True,
            },
        }

    def _extract_page_json(self, page):
        raw_page = self._extract_json_payload(
            page,
            candidate_keys=("page", "pageJson", "page_json", "raw"),
            nested_paths=(
                ("files", "page.json"),
                ("raw", "page.json"),
            ),
        )
        if isinstance(raw_page, dict):
            return deepcopy(raw_page)

        fallback = {
            key: deepcopy(value)
            for key, value in page.items()
            if key not in {"visuals", "files"}
        }
        fallback.setdefault("$schema", self.PAGE_JSON_SCHEMA_URL)
        fallback.setdefault("name", self._resolve_page_name(page))
        fallback.setdefault("displayName", fallback.get("name"))
        fallback.setdefault("displayOption", "FitToPage")
        fallback.setdefault("height", 720)
        fallback.setdefault("width", 1280)
        fallback.setdefault(
            "objects",
            {
                "outspacePane": [
                    {
                        "properties": {
                            "width": {
                                "expr": {
                                    "Literal": {
                                        "Value": "192L"
                                    }
                                }
                            }
                        }
                    }
                ]
            },
        )
        return fallback

    def _extract_page_files(self, page):
        return self._extract_files_payload(
            page,
            candidate_keys=("files", "pageFiles", "page_files"),
            nested_paths=(
                ("raw", "files"),
                ("raw", "page_files"),
            ),
        )

    def _extract_visual_json(self, visual):
        raw_visual = self._extract_json_payload(
            visual,
            candidate_keys=("visual", "visualJson", "visual_json", "raw"),
            nested_paths=(
                ("files", "visual.json"),
                ("raw", "visual.json"),
            ),
        )
        if isinstance(raw_visual, dict):
            return deepcopy(raw_visual)

        return {
            key: deepcopy(value)
            for key, value in visual.items()
            if key not in {"files"}
        }

    def _extract_visual_files(self, visual):
        return self._extract_files_payload(
            visual,
            candidate_keys=("files", "visualFiles", "visual_files"),
            nested_paths=(
                ("raw", "files"),
                ("raw", "visual_files"),
            ),
        )

    def _extract_pages(self, report):
        pages = report.get("pages", [])
        if not isinstance(pages, list):
            return []

        return [
            page for page in pages
            if isinstance(page, dict) and self._looks_like_page_entry(page)
        ]

    def _extract_visuals(self, page):
        visuals = page.get("visuals", [])
        return visuals if isinstance(visuals, list) else []

    def _resolve_report_folder_name(self, report, project_name):
        return report.get("reportFolderName") or f"{project_name}.Report"

    def _resolve_semantic_model_folder_name(self, report, project_name):
        return report.get("semanticModelFolderName") or f"{project_name}.SemanticModel"

    def _resolve_page_name(self, page):
        return page.get("name") or page.get("id")

    def _resolve_visual_name(self, visual):
        return visual.get("name") or visual.get("id")

    def _extract_json_payload(self, data, candidate_keys=(), nested_paths=()):
        for key in candidate_keys:
            value = data.get(key)
            if isinstance(value, dict):
                return value

        for path in nested_paths:
            value = self._deep_get(data, path)
            if isinstance(value, dict):
                return value

        return None

    def _extract_files_payload(self, data, candidate_keys=(), nested_paths=()):
        for key in candidate_keys:
            value = data.get(key)
            if isinstance(value, dict):
                return value

        for path in nested_paths:
            value = self._deep_get(data, path)
            if isinstance(value, dict):
                return value

        return {}

    def _extract_report_definition_files(self, report):
        return self._extract_files_payload(
            report,
            candidate_keys=("definitionFiles", "definition_files"),
            nested_paths=(
                ("definition", "files"),
                ("raw", "definition", "files"),
                ("raw", "definition_files"),
            ),
        )

    def _extract_static_resource_files(self, report):
        return self._extract_files_payload(
            report,
            candidate_keys=("staticResources", "static_resources"),
            nested_paths=(
                ("raw", "staticResources"),
                ("raw", "static_resources"),
            ),
        )

    def _extract_support_files(self, report):
        return self._extract_files_payload(
            report,
            candidate_keys=("supportFiles", "support_files"),
            nested_paths=(
                ("raw", "supportFiles"),
                ("raw", "support_files"),
            ),
        )

    def _deep_get(self, data, path):
        current = data
        for segment in path:
            if not isinstance(current, dict) or segment not in current:
                return None
            current = current[segment]
        return current

    def _write_json_file(self, path, payload):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)

    def _write_additional_json_assets(self, root_path, files_payload, skip_filenames=None):
        skip_filenames = skip_filenames or set()

        for relative_name in sorted(files_payload):
            if relative_name in skip_filenames or not relative_name.endswith(".json"):
                continue

            payload = files_payload[relative_name]
            if not isinstance(payload, (dict, list)):
                continue

            target_path = os.path.normpath(os.path.join(root_path, relative_name))
            if not self._is_safe_child_path(root_path, target_path):
                continue

            self._write_json_file(target_path, deepcopy(payload))

    def _write_support_assets(self, root_path, files_payload):
        for relative_name in sorted(files_payload):
            asset = files_payload[relative_name]
            if not isinstance(asset, dict):
                continue

            target_path = os.path.normpath(os.path.join(root_path, relative_name))
            if not self._is_safe_child_path(root_path, target_path):
                continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            kind = asset.get("kind")
            content = asset.get("content")

            if kind == "json" and isinstance(content, (dict, list)):
                self._write_json_file(target_path, deepcopy(content))
            elif kind == "text" and isinstance(content, str):
                with open(target_path, "w", encoding="utf-8") as file_handle:
                    file_handle.write(content)
            elif kind == "base64" and isinstance(content, str):
                with open(target_path, "wb") as file_handle:
                    file_handle.write(base64.b64decode(content))

    def _looks_like_page_entry(self, page):
        page_name = page.get("name") or page.get("id")
        return isinstance(page_name, str) and not page_name.endswith(".json")

    def _is_safe_child_path(self, root_path, target_path):
        root_abs = os.path.abspath(root_path)
        target_abs = os.path.abspath(target_path)
        return os.path.commonpath([root_abs, target_abs]) == root_abs
