class LineageExtractor:

    def extract_from_report(self, report_data):
        lineage = []

        for page in report_data.get("pages", []):
            for visual in page.get("visuals", []):

                vjson = visual.get("visual", {})
                projections = (
                    vjson.get("query", {})
                    .get("queryState", {})
                    .get("projections", {})
                )

                for role, items in projections.items():
                    for item in items:
                        ref = item.get("queryRef")

                        if ref and "." in ref:
                            table, column = ref.split(".", 1)

                            lineage.append({
                                "page": page["name"],
                                "visual": visual["name"],
                                "table": table,
                                "column": column
                            })

        return lineage