import json
import os
import base64


class ReportExtractor:

    def __init__(self, path):
        self.path = path

    def extract(self):
        definition_path = os.path.join(self.path, "definition")
        pages_root = os.path.join(definition_path, "pages")

        return {
            "definitionPbir": self._read_json(os.path.join(self.path, "definition.pbir")),
            "report": self._read_json(os.path.join(definition_path, "report.json")),
            "versionJson": self._read_json(os.path.join(definition_path, "version.json")),
            "pagesMetadata": self._read_json(os.path.join(pages_root, "pages.json")),
            "staticResources": self._read_json_tree(os.path.join(self.path, "StaticResources")),
            "supportFiles": self._read_asset_tree((".pbi", ".platform")),
            "pages": self._read_pages(pages_root),
        }

    def _read_pages(self, base):
        pages = []
        if not os.path.isdir(base):
            return pages
        for page_name in sorted(os.listdir(base)):
            if page_name.endswith(".json"):
                continue

            page_path = os.path.join(base, page_name)
            if not os.path.isdir(page_path):
                continue

            page = {
                "name": page_name,
                "page": self._read_json(os.path.join(page_path, "page.json")),
                "visuals": self._read_visuals(page_path),
            }
            pages.append(page)

        return pages

    def _read_visuals(self, page_path):
        visuals = []
        visuals_path = os.path.join(page_path, "visuals")

        if not os.path.isdir(visuals_path):
            return visuals

        for visual_name in sorted(os.listdir(visuals_path)):
            visual_path = os.path.join(visuals_path, visual_name)
            if not os.path.isdir(visual_path):
                continue

            visuals.append({
                "name": visual_name,
                "visual": self._read_json(os.path.join(visual_path, "visual.json")),
            })

        return visuals

    def _read_json(self, path):
        if not os.path.exists(path):
            return {}

        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    def _read_json_tree(self, root_path):
        files = {}

        if not os.path.isdir(root_path):
            return files

        for current_root, _, filenames in os.walk(root_path):
            for filename in filenames:
                if not filename.endswith(".json"):
                    continue

                full_path = os.path.join(current_root, filename)
                relative_path = os.path.relpath(full_path, root_path).replace("\\", "/")
                files[relative_path] = self._read_json(full_path)

        return files

    def _read_asset_tree(self, folder_names):
        assets = {}

        for folder_name in folder_names:
            root_path = os.path.join(self.path, folder_name)
            if not os.path.exists(root_path):
                continue

            for current_root, _, filenames in os.walk(root_path):
                for filename in filenames:
                    full_path = os.path.join(current_root, filename)
                    relative_path = os.path.relpath(full_path, self.path).replace("\\", "/")
                    assets[relative_path] = self._read_asset(full_path)

        return assets

    def _read_asset(self, path):
        if path.endswith(".json"):
            return {
                "kind": "json",
                "content": self._read_json(path),
            }

        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                return {
                    "kind": "text",
                    "content": file_handle.read(),
                }
        except UnicodeDecodeError:
            with open(path, "rb") as file_handle:
                return {
                    "kind": "base64",
                    "content": base64.b64encode(file_handle.read()).decode("ascii"),
                }
