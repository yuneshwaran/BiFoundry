import base64
import json
import os


class SemanticModelWriter:
    DEFAULT_PROJECT_NAME = "MyProject"
    PBISM_SCHEMA_URL = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json"

    def __init__(self, base_path):
        self.base_path = base_path

    def write(self, dataset, project_name=None):
        project_name = project_name or dataset.get("projectName") or self.DEFAULT_PROJECT_NAME
        path = os.path.join(self.base_path, f"{project_name}.SemanticModel")
        os.makedirs(path, exist_ok=True)

        raw_dataset = dataset.get("raw") if isinstance(dataset.get("raw"), dict) else dataset
        semantic_format = self._detect_semantic_format(raw_dataset)
        definition_files = raw_dataset.get("definitionFiles", {})
        has_definition_files = isinstance(definition_files, dict) and bool(definition_files)
        model = raw_dataset.get("model", {})
        has_model = isinstance(model, dict) and bool(model)

        definition_pbism = raw_dataset.get("definitionPbism")
        if not isinstance(definition_pbism, dict) or not definition_pbism:
            definition_pbism = {"version": "1.0"}

        self._write_json(os.path.join(path, "definition.pbism"), definition_pbism)

        if has_definition_files:
            self._write_text_assets(os.path.join(path, "definition"), definition_files)

        support_files = raw_dataset.get("supportFiles", {})
        if isinstance(support_files, dict) and support_files:
            self._write_support_assets(path, support_files)

        model_bim_path = os.path.join(path, "model.bim")
        if semantic_format == "tmsl":
            model = self._resolve_model_bim(raw_dataset)
            if isinstance(model, dict) and model:
                self._write_json(model_bim_path, model)
        elif os.path.exists(model_bim_path):
            os.remove(model_bim_path)

        if semantic_format == "tmdl" and not has_definition_files:
            raise RuntimeError(
                "Cannot reconstruct a TMDL semantic model without definition files. "
                "Re-run extraction from a valid PBIP source so the definition/ folder is stored."
            )

        if semantic_format == "tmsl" and not has_model:
            raise RuntimeError(
                "Cannot reconstruct a TMSL semantic model without model.bim content. "
                "Re-run extraction from a valid PBIP source so the model definition is stored."
            )

    def _resolve_model_bim(self, raw_dataset):
        model = raw_dataset.get("model", {})
        if isinstance(model, dict) and model:
            return self._normalize_model_bim(model, raw_dataset)

        definition_files = raw_dataset.get("definitionFiles", {})
        if isinstance(definition_files, dict) and definition_files:
            return self._build_model_bim_from_tmdl(definition_files)

        return {}

    def _normalize_model_bim(self, model, raw_dataset):
        model_name = raw_dataset.get("name") or model.get("name") or "Model"
        compatibility_level = raw_dataset.get("compatibilityLevel") or model.get("compatibilityLevel") or 1600
        normalized_model = self._strip_database_metadata(model)

        model_tables = model.get("tables")
        if isinstance(model_tables, list):
            normalized_model["tables"] = [self._ensure_table_partitions(table) for table in model_tables]

        model_relationships = model.get("relationships")
        if isinstance(model_relationships, list):
            normalized_model["relationships"] = model_relationships

        if not normalized_model.get("tables"):
            definition_files = raw_dataset.get("definitionFiles", {})
            if isinstance(definition_files, dict) and definition_files:
                rebuilt = self._build_model_bim_from_tmdl(definition_files)
                if isinstance(rebuilt, dict):
                    return rebuilt

        if "tables" not in normalized_model:
            normalized_model["tables"] = []
        else:
            normalized_model["tables"] = [self._ensure_table_partitions(table) for table in normalized_model["tables"]]

        return {
            "name": model_name,
            "compatibilityLevel": compatibility_level,
            "model": normalized_model,
        }

    def _strip_database_metadata(self, model):
        return {
            key: value
            for key, value in model.items()
            if key not in {"name", "compatibilityLevel", "tables", "relationships", "cultures", "annotations", "perspectives"}
        }

    def _detect_semantic_format(self, raw_dataset):
        definition_files = raw_dataset.get("definitionFiles", {})
        if isinstance(definition_files, dict) and definition_files:
            return "tmdl"

        model = raw_dataset.get("model", {})
        if isinstance(model, dict) and model:
            return "tmsl"

        definition_pbism = raw_dataset.get("definitionPbism", {})
        if isinstance(definition_pbism, dict):
            version = str(definition_pbism.get("version", ""))
            if version.startswith("1."):
                return "tmsl"

        return "unknown"

    def _build_model_bim_from_tmdl(self, definition_files):
        compatibility_level = 1600
        database_text = definition_files.get("database.tmdl", "")
        for line in database_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("compatibilityLevel:"):
                compatibility_level = self._parse_int(stripped.split(":", 1)[1].strip(), 1600)

        model_text = definition_files.get("model.tmdl", "")
        model_name = "Model"
        model_payload = {"tables": []}
        model_annotations = []

        for line in model_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("model "):
                model_name = stripped.split(" ", 1)[1].strip()
                continue
            if stripped.startswith("annotation "):
                annotation = self._parse_annotation(stripped)
                if annotation:
                    model_annotations.append(annotation)
                continue
            if ":" in stripped and not stripped.startswith("ref "):
                key, value = stripped.split(":", 1)
                model_payload[key.strip()] = self._parse_scalar(value.strip())

        if model_annotations:
            model_payload["annotations"] = model_annotations

        table_files = {
            key: value for key, value in definition_files.items()
            if key.startswith("tables/") and key.endswith(".tmdl")
        }
        model_payload["tables"] = [
            self._ensure_table_partitions(self._parse_table_tmdl(table_files[path_key]))
            for path_key in sorted(table_files)
        ]

        model_payload = self._strip_database_metadata(model_payload)

        return {
            "name": model_name,
            "compatibilityLevel": compatibility_level,
            "model": model_payload,
        }

    def _ensure_table_partitions(self, table):
        if not isinstance(table, dict):
            return table

        partitions = table.get("partitions")
        if isinstance(partitions, list) and partitions:
            return table
        
        columns = table.get("columns") or []
        table_name = table.get("name") or "Table"
        
        expression = self._build_empty_table_expression(table_name, columns)
        assert expression

        partition = {
            "name": f"{table_name}_Partition",
            "mode": "import",
            "source": {
                "type": "m",
                "expression": expression,
            },
        }

        next_table = dict(table)
        next_table["partitions"] = [partition]
        return next_table

    def _build_empty_table_expression(self, table_name, columns):
        type_sig = self._build_m_type_signature(columns)
        lines = [
            "let",
            f'    Source = #table(type table [{type_sig}], {{}})',
            "in",
            "    Source",
        ]
        return "\n".join(lines)

    def _build_m_type_signature(self, columns):
        parts = []
        for column in columns or []:
            name = column.get("name")
            if not name:
                continue
            data_type = column.get("dataType") or column.get("data_type") or column.get("type")
            parts.append(f"{self._escape_m_identifier(name)} = {self._map_data_type_to_m(data_type)}")

        if not parts:
            return "Dummy = type any"

        return ", ".join(parts)

    def _escape_m_identifier(self, value):
        text = str(value).replace('"', '""')
        if text and text[0].isalpha() and all(char.isalnum() or char == "_" for char in text):
            return text
        return f'#"{text}"'

    def _map_data_type_to_m(self, data_type):
        normalized = str(data_type or "").lower()
        if normalized in {"int64", "int", "integer", "whole number"}:
            return "Int64.Type"
        if normalized in {"double", "decimal", "currency", "number", "numeric"}:
            return "type number"
        if normalized in {"boolean", "bool"}:
            return "type logical"
        if normalized in {"date"}:
            return "type date"
        if normalized in {"datetime", "datetimezone", "time"}:
            return "type datetime"
        return "type text"

    def _parse_table_tmdl(self, content):
        table = {"columns": [], "partitions": []}
        table_annotations = []
        current_column = None
        current_partition = None
        partition_source_lines = []
        in_partition_source = False

        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            indent = self._indent_level(raw_line)

            if not stripped:
                if in_partition_source:
                    partition_source_lines.append("")
                continue

            if indent == 0 and stripped.startswith("table "):
                table["name"] = stripped.split(" ", 1)[1].strip()
                current_column = None
                current_partition = None
                in_partition_source = False
                continue

            if indent == 1 and stripped.startswith("column "):
                current_column = {"name": stripped.split(" ", 1)[1].strip()}
                table["columns"].append(current_column)
                current_partition = None
                in_partition_source = False
                continue

            if indent == 1 and stripped.startswith("partition "):
                partition_header = stripped.split(" ", 1)[1].strip()
                partition_name, _, source_type = partition_header.partition("=")
                current_partition = {
                    "name": partition_name.strip(),
                    "source": {
                        "type": (source_type.strip() or "m"),
                    },
                }
                table["partitions"].append(current_partition)
                current_column = None
                partition_source_lines = []
                in_partition_source = False
                continue

            if stripped.startswith("annotation "):
                annotation = self._parse_annotation(stripped)
                if not annotation:
                    continue
                if current_partition is not None and indent >= 2:
                    current_partition.setdefault("annotations", []).append(annotation)
                elif current_column is not None and indent >= 2:
                    current_column.setdefault("annotations", []).append(annotation)
                else:
                    table_annotations.append(annotation)
                continue

            if current_partition is not None:
                if indent == 2 and stripped.startswith("source ="):
                    in_partition_source = True
                    partition_source_lines = []
                    continue

                if in_partition_source:
                    if indent >= 3:
                        partition_source_lines.append(stripped)
                        continue
                    current_partition["source"]["expression"] = "\n".join(partition_source_lines).rstrip()
                    in_partition_source = False

                if indent >= 2 and ":" in stripped:
                    key, value = stripped.split(":", 1)
                    current_partition[key.strip()] = self._parse_scalar(value.strip())
                    continue

            if current_column is not None and indent >= 2 and ":" in stripped:
                key, value = stripped.split(":", 1)
                current_column[key.strip()] = self._parse_scalar(value.strip())
                continue

            if current_partition is None and current_column is None and indent >= 1 and ":" in stripped:
                key, value = stripped.split(":", 1)
                table[key.strip()] = self._parse_scalar(value.strip())

        if current_partition is not None and in_partition_source:
            current_partition["source"]["expression"] = "\n".join(partition_source_lines).rstrip()

        if table_annotations:
            table["annotations"] = table_annotations

        return table

    def _parse_annotation(self, stripped_line):
        body = stripped_line[len("annotation "):]
        if "=" not in body:
            return None
        name, value = body.split("=", 1)
        return {
            "name": name.strip(),
            "value": value.strip(),
        }

    def _parse_scalar(self, value):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            return value

    def _parse_int(self, value, default):
        try:
            return int(value)
        except ValueError:
            return default

    def _indent_level(self, raw_line):
        expanded = raw_line.replace("\t", "    ")
        return (len(expanded) - len(expanded.lstrip(" "))) // 4

    def _write_json(self, path, payload):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)

    def _write_text_assets(self, root_path, files_payload):
        for relative_name in sorted(files_payload):
            content = files_payload[relative_name]
            if not isinstance(content, str):
                continue

            target_path = os.path.normpath(os.path.join(root_path, relative_name))
            if not self._is_safe_child_path(root_path, target_path):
                continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as file_handle:
                file_handle.write(content)

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
                self._write_json(target_path, content)
            elif kind == "text" and isinstance(content, str):
                with open(target_path, "w", encoding="utf-8") as file_handle:
                    file_handle.write(content)
            elif kind == "base64" and isinstance(content, str):
                with open(target_path, "wb") as file_handle:
                    file_handle.write(base64.b64decode(content))

    def _is_safe_child_path(self, root_path, target_path):
        root_abs = os.path.abspath(root_path)
        target_abs = os.path.abspath(target_path)
        return os.path.commonpath([root_abs, target_abs]) == root_abs
