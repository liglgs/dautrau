from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, time
import xml.etree.ElementTree as ET
import httpx

root = Path(__file__).parent / "data-real"
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
for pmid in ["41943791", "31486525", "35615486", "35799184"]:
    manifest = [item for item in manifest if item["id"] != "pubmed-" + pmid]
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db":"pubmed", "id":pmid, "retmode":"xml"}
    response = httpx.get(url, params=params, timeout=40)
    response.raise_for_status()
    assert ET.fromstring(response.content).findall("PubmedArticle")
    path = root / ("pubmed-" + pmid + ".xml")
    path.write_bytes(response.content)
    manifest.append({"id":"pubmed-" + pmid, "requested_url":url, "params":params, "final_url":str(response.url), "kind":"hospital_workflow_primary_survey", "retrieved_at_utc":datetime.now(timezone.utc).isoformat(), "status":response.status_code, "file":path.name, "bytes":len(response.content), "sha256":hashlib.sha256(response.content).hexdigest(), "verified_payload":True, "coverage":"PubMed metadata and abstract only; not full paper or respondent-level data"})
    time.sleep(0.4)

n = {"h":"urn:hl7-org:v3"}
metadata=[]
for path in root.glob("dailymed-label-*.xml"):
    doc=ET.parse(path).getroot()
    sections=[]
    for section in doc.findall(".//h:section",n):
        title=section.findtext("h:title",default="",namespaces=n)
        if "hypomagnesemia" in title.lower() or "aortic" in title.lower():
            text=section.find("h:text",n)
            sections.append({"title":title, "text":" ".join(text.itertext()), "section_id":section.attrib.get("ID")})
    metadata.append({"file":path.name, "setid":doc.find("h:setId",n).attrib["root"], "version":doc.find("h:versionNumber",n).attrib["value"], "effective_time":doc.find("h:effectiveTime",n).attrib["value"], "title":doc.findtext("h:title",namespaces=n), "sections":sections})
(root / "label-metadata-and-sections.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
(root / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
verified=[x for x in manifest if x["verified_payload"]]
for item in verified:
    assert hashlib.sha256((root/item["file"]).read_bytes()).hexdigest()==item["sha256"], item["id"]
print(len(verified),"verified public source snapshots;",len(manifest)-len(verified),"failed source(s)")
print([(x['file'],x['version'],x['effective_time']) for x in metadata])
