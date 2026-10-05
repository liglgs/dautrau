"""Read-only public source snapshots; no hospital records or model calls."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time
import xml.etree.ElementTree as ET
import httpx

ROOT = Path(__file__).parent / "data-real"
ROOT.mkdir(parents=True, exist_ok=True)
manifest = []
client = httpx.Client(timeout=40, follow_redirects=True)

def collect(key, url, kind, params=None, validate=None):
    row = {"id": key, "requested_url": url, "params": params, "kind": kind,
           "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        response = client.get(url, params=params)
        row.update(status=response.status_code, final_url=str(response.url), content_type=response.headers.get("content-type"))
        response.raise_for_status()
        if validate:
            validate(response)
        suffix = ".json" if "json" in row["content_type"] else ".pdf" if response.content.startswith(b"%PDF") else ".xml" if kind == "pubmed_abstract" or kind == "spl_label" else ".html"
        path = ROOT / (key + suffix)
        path.write_bytes(response.content)
        row.update(file=path.name, bytes=len(response.content), sha256=hashlib.sha256(response.content).hexdigest(), verified_payload=True)
        print(key, "OK", len(response.content), flush=True)
        manifest.append(row)
        return response
    except Exception as exc:
        row.update(verified_payload=False, error=str(exc))
        manifest.append(row)
        print(key, "FAILED", str(exc)[:170], flush=True)
        return None

def pubmed_valid(response):
    assert ET.fromstring(response.content).findall("PubmedArticle"), "No PubmedArticle payload"

for pmid in ["39975698", "40285433", "40988034"]:
    collect("pubmed-" + pmid, "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", "pubmed_abstract", {"db":"pubmed", "id":pmid, "retmode":"xml"}, pubmed_valid)
    time.sleep(0.4)

for drug in ["ciprofloxacin", "pantoprazole"]:
    result = collect("dailymed-index-" + drug, "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json", "label_index", {"drug_name":drug, "pagesize":5, "page":1}, lambda r: r.json()["data"])
    if result:
        labels = result.json()["data"]
        (ROOT / (drug + "-label-selection.json")).write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
        label = labels[0]
        collect("dailymed-label-" + drug, "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/" + label["setid"] + ".xml", "spl_label", validate=lambda r: ET.fromstring(r.content))

collect("fda-fq-warning-2018", "https://www.fda.gov/media/119532/download", "regulatory_notice", validate=lambda r: r.content.startswith(b"%PDF") or (_ for _ in ()).throw(ValueError("Expected PDF")))
collect("vn-adr-2024", "https://magazine.canhgiacduoc.org.vn/Magazine/Details/316", "national_pv_bulletin", validate=lambda r: "2024" in r.text or (_ for _ in ()).throw(ValueError("Wrong page")))
collect("vn-adr-2025", "https://magazine.canhgiacduoc.org.vn/Magazine/Details/335", "national_pv_bulletin", validate=lambda r: "35.430" in r.text or (_ for _ in ()).throw(ValueError("Wrong page")))
collect("dailymed-label-pantoprazole-oral", "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/6faf465b-c3a3-4ae7-9e16-1ba758f6962a.xml", "spl_label", validate=lambda r: ET.fromstring(r.content))
collect("who-umc-causality", "https://cdn.who.int/media/docs/default-source/medicines/pharmacovigilance/whocausality-assessment.pdf?sfvrsn=5d8130bb_2", "case_assessment_guidance", validate=lambda r: r.content.startswith(b"%PDF") or (_ for _ in ()).throw(ValueError("Expected PDF")))
collect("vn-latest-bulletin-index", "https://magazine.canhgiacduoc.org.vn/", "national_pv_bulletin_index", validate=lambda r: "2026" in r.text or (_ for _ in ()).throw(ValueError("Wrong page")))
collect("openfda-event-docs", "https://open.fda.gov/apis/drug/event/", "data_source_documentation")
collect("adr-cognitive-task-study", "https://scholarworks.indianapolis.iu.edu/server/api/core/bitstreams/3b49a2aa-2432-4b51-8bee-2b4a1268e778/content", "workflow_primary_study", validate=lambda r: r.content.startswith(b"%PDF") or (_ for _ in ()).throw(ValueError("Expected PDF")))
(ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("Manifest:", len(manifest), "sources;", sum(r["verified_payload"] for r in manifest), "verified")
