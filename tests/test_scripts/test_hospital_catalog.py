"""Offline regression tests for the hospital drug catalog importer."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.elt.hospital_catalog import (
    CatalogValidationError,
    DailyMedProduct,
    import_hospital_catalog,
    map_dailymed,
)

FIXTURE = Path("data/dictionaries/hospital-drug-catalog.synthetic.csv")


def test_synthetic_catalog_is_labelled_at_file_and_record_level() -> None:
    records = import_hospital_catalog(FIXTURE)

    assert len(records) == 3
    assert all(record.is_synthetic for record in records)
    assert [record.hospital_code for record in records] == ["SYN-BV-001", "SYN-BV-002", "SYN-BV-003"]


def test_synthetic_file_rejects_an_unlabelled_record(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "# synthetic: true\n"
        "hospital_code,brand_name,active_ingredient,strength,dosage_form,route,manufacturer,synthetic_label\n"
        "X,Brand,ingredient,1 mg,tablet,oral,Maker,\n",
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError, match="synthetic_label=SYNTHETIC"):
        import_hospital_catalog(path)


def test_catalog_rejects_missing_required_value_and_duplicate_code(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "hospital_code,brand_name,active_ingredient,strength,dosage_form,route,manufacturer,synthetic_label\n"
        "X,Brand,ingredient,1 mg,tablet,oral,Maker,\n"
        "X,,ingredient,1 mg,tablet,oral,Maker,\n",
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError, match="thiếu: brand_name"):
        import_hospital_catalog(path)


def test_dailymed_mapping_requires_ingredient_strength_form_and_route() -> None:
    intravenous_pantoprazole, ear_ciprofloxacin, oral_pantoprazole = import_hospital_catalog(FIXTURE)
    products = [
        DailyMedProduct(
            setid="oral-panto", version=7, active_ingredient="pantoprazole", strength="40 mg",
            dosage_form="tablet", route="oral", published_date="2026-09-29", effective_time="2024-09-19",
            retrieved_at="2026-10-06T00:00:00+00:00",
        ),
        DailyMedProduct(
            setid="oral-cipro", version=3, active_ingredient="ciprofloxacin", strength="500 mg",
            dosage_form="tablet", route="oral",
        ),
    ]

    intravenous_mapping = map_dailymed(intravenous_pantoprazole, products)[0]
    ear_mapping = map_dailymed(ear_ciprofloxacin, products)[0]
    assert intravenous_mapping.status == "unknown"
    assert {"dosage_form", "route"} <= set(intravenous_mapping.mismatch_fields)
    assert ear_mapping.status == "unknown"
    assert {"strength", "dosage_form", "route"} <= set(ear_mapping.mismatch_fields)

    mapping = map_dailymed(oral_pantoprazole, products)[0]
    assert mapping.status == "candidate"
    assert mapping.approved is False
    assert mapping.provenance["published_date"] == "2026-09-29"
    assert mapping.provenance["effective_time"] == "2024-09-19"
