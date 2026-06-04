class MExtractor:

    def extract_queries(self, unapplied):
        return unapplied.get("queries", [])