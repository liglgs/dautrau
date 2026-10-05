from src.services.sources.base import SourceAdapter
from src.services.sources.parser import document, safe_xml, text_of
from src.services.sources.transport import SourceError

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


class PubMedAdapter(SourceAdapter):
    name = "pubmed"

    def fetch(self, action, meter):
        raw = self.get(
            BASE + "esearch.fcgi",
            {"db": "pubmed", "term": action.query, "retmode": "json", "retmax": self.max_documents},
            meter,
        )
        search = self.json(raw)["esearchresult"]
        if search.get("errorlist") or search.get("ERROR"):
            raise SourceError("invalid_query: PubMed rejected query")
        ids = list(dict.fromkeys(search["idlist"]))[: self.max_documents]
        if not ids:
            return []
        if any(not str(pmid).isdigit() for pmid in ids):
            raise SourceError("parse_error: invalid PMID")
        raw = self.get(BASE + "efetch.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}, meter)
        root = safe_xml(raw)
        results = []
        for article in root.findall("PubmedArticle"):
            pmid = article.find("./MedlineCitation/PMID")
            if pmid is None or pmid.text not in ids:
                raise SourceError("parse_error: missing or unexpected PMID")
            title = text_of(article.find("./MedlineCitation/Article/ArticleTitle"))
            sections = [
                (item.get("Label", "Abstract"), text_of(item))
                for item in article.findall("./MedlineCitation/Article/Abstract/AbstractText")
            ]
            doi = [
                item.text
                for item in article.findall("./PubmedData/ArticleIdList/ArticleId")
                if item.get("IdType") == "doi"
            ]
            metadata = {
                "content_level": "abstract_only" if sections else "metadata_only",
                "doi": doi,
                "publication_types": [text_of(n) for n in article.findall(".//PublicationType")],
                "publication_date": text_of(article.find(".//PubDate")),
                "query_translation": search.get("querytranslation"),
                "warnings": [] if sections else ["missing_abstract"],
            }
            results.append(
                self.snapshot(
                    document(
                        self.name,
                        pmid.text,
                        int(pmid.get("Version", "1")),
                        title,
                        f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}/",
                        raw,
                        sections,
                        metadata,
                    ),
                    raw,
                )
            )
        if not results:
            raise SourceError("parse_error: fetch returned no requested articles")
        return results
