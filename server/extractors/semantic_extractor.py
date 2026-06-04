import json
import os
import base64
import re


class SemanticExtractor:

    def __init__(self, path):
        self.path = path

    def extract(self):
        return {
            "model": self._read_model(),
            "queries": self._read_unapplied(),
            "definitionPbism": self._read_json(os.path.join(self.path, "definition.pbism")),
            "definitionFiles": self._read_text_tree(os.path.join(self.path, "definition"), (".tmdl",)),
            "supportFiles": self._read_asset_tree((".pbi", ".platform")),
        }

    def _read_model(self):
        path = os.path.join(self.path, "model.bim")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    def _read_unapplied(self):
        path = os.path.join(self.path, ".pbi", "unappliedChanges.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    def _read_json(self, path):
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    def _read_text_tree(self, root_path, suffixes):
        files = {}

        if not os.path.isdir(root_path):
            return files

        for current_root, _, filenames in os.walk(root_path):
            for filename in filenames:
                if suffixes and not filename.endswith(suffixes):
                    continue

                full_path = os.path.join(current_root, filename)
                relative_path = os.path.relpath(full_path, root_path).replace("\\", "/")
                with open(full_path, "r", encoding="utf-8") as file_handle:
                    files[relative_path] = file_handle.read()

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


def extract_tables_and_relationships(model_json):
    tables = []
    relationships = []

    for table in model_json.get("model", {}).get("tables", []):
        tables.append(table)

    for relationship in model_json.get("model", {}).get("relationships", []):
        relationships.append(relationship)

    if not tables:
        definition_files = model_json.get("definitionFiles", {})
        if isinstance(definition_files, dict):
            for path_key in sorted(definition_files):
                if not path_key.startswith("tables/") or not path_key.endswith(".tmdl"):
                    continue
                parsed = _parse_table_tmdl(definition_files[path_key], path_key)
                if parsed:
                    tables.append(parsed)

    if not relationships:
        definition_files = model_json.get("definitionFiles", {})
        if isinstance(definition_files, dict):
            for path_key in sorted(definition_files):
                if not path_key.endswith("relationships.tmdl"):
                    continue
                relationships.extend(_parse_relationships_tmdl(definition_files[path_key]))

    return tables, relationships


def _indent_level(raw_line):
    return (len(raw_line) - len(raw_line.lstrip(" "))) // 2


def _parse_scalar(value):
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value.strip('"')


def _parse_table_tmdl(content, path_key):
    table = {"columns": [], "measures": [], "source": "tmdl", "path": path_key}
    current_item = None
    current_kind = None

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        indent = _indent_level(raw_line)
        if not stripped:
            continue

        if indent == 0 and stripped.startswith("table "):
            table["name"] = stripped.split(" ", 1)[1].strip()
            current_item = None
            current_kind = None
            continue

        for prefix, item_kind in (
            ("column ", "column"),
            ("calculatedColumn ", "calculated_column"),
            ("measure ", "measure"),
        ):
            if indent == 1 and stripped.startswith(prefix):
                item = {"name": stripped.split(" ", 1)[1].strip()}
                current_item = item
                current_kind = item_kind
                if item_kind == "measure":
                    table["measures"].append(item)
                else:
                    item["type"] = item_kind
                    table["columns"].append(item)
                break
        else:
            if current_item is not None and indent >= 2 and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = _parse_scalar(value.strip())
                if key.lower() == "datatype":
                    current_item["dataType"] = value
                elif key.lower() == "sourcecolumn":
                    current_item["sourceColumn"] = value
                elif key.lower() == "ishidden":
                    current_item["isHidden"] = bool(value)
                elif key.lower() == "displayfolder":
                    current_item["displayFolder"] = value
                elif key.lower() in {"expression", "formatstring"}:
                    current_item[key] = value
                else:
                    current_item[key] = value
                continue

            if current_item is None and indent >= 1 and ":" in stripped:
                key, value = stripped.split(":", 1)
                table[key.strip()] = _parse_scalar(value.strip())

    return table if table.get("name") else None


def _parse_relationships_tmdl(content):
    relationships = []
    current = None
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        indent = _indent_level(raw_line)
        if not stripped:
            continue

        if indent == 0 and stripped.startswith("relationship "):
            if current:
                relationships.append(current)
            current = {"name": stripped.split(" ", 1)[1].strip(), "source": "tmdl"}
            continue

        if current is not None and indent >= 1 and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "fromColumn":
                current["fromColumn"] = _normalize_tmdl_reference(value, "column")
            elif key == "toColumn":
                current["toColumn"] = _normalize_tmdl_reference(value, "column")
            elif key == "fromTable":
                current["fromTable"] = _normalize_tmdl_reference(value, "table")
            elif key == "toTable":
                current["toTable"] = _normalize_tmdl_reference(value, "table")
            elif key == "isActive":
                current["isActive"] = _parse_scalar(value)
            else:
                current[key] = _parse_scalar(value)

    if current:
        relationships.append(current)
    return [item for item in relationships if item.get("fromColumn") or item.get("fromTable")]


def _normalize_tmdl_reference(value, reference_kind):
    text = value.strip().strip('"')
    if reference_kind == "table":
        return text
    match = re.match(r"([^.\[]+)\[([^\]]+)\]", text)
    if match:
        return match.group(2)
    return text
