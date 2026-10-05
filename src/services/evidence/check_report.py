"""Separate pipeline failures from correctly rejected model quotations."""


def summarize_checks(results):
    return {
        "documents_checked": len(results),
        "valid_quotes": sum(r["valid_quotes"] for r in results),
        "excluded_quotes": sum(r["excluded_quotes"] for r in results),
        "processing_failures": [r["doc_id"] for r in results
            if r.get("error") or r.get("citation_errors") or r.get("dossier_errors")],
        "documents_with_excluded_quotes": [r["doc_id"] for r in results if r["excluded_quotes"]],
        "documents_without_quotes": [r["doc_id"] for r in results
            if r["valid_quotes"] == 0 and r["excluded_quotes"] == 0 and not r.get("error")],
        "clinical_metrics_measured": False,
    }
