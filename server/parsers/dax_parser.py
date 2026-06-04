class DAXExtractor:

    def extract_measures(self, model_json):
        measures = []

        for t in model_json.get("model", {}).get("tables", []):
            for m in t.get("measures", []):
                measures.append(m)

        return measures