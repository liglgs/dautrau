"""Nhập CSV danh mục thuốc bệnh viện và lập ứng viên DailyMed, hoàn toàn offline.

Module này không ghi vào kho dùng chung và không tự phê duyệt mapping.  Danh mục
thật chỉ được nhập sau khi bệnh viện cấp quyền; fixture kèm repo là synthetic và
mọi bản ghi synthetic phải tự gắn nhãn.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = (
    "hospital_code",
    "brand_name",
    "active_ingredient",
    "strength",
    "dosage_form",
    "route",
    "manufacturer",
    "synthetic_label",
)
SYNTHETIC_FILE_MARKER = "# synthetic: true"
SYNTHETIC_RECORD_MARKER = "SYNTHETIC"


class CatalogValidationError(ValueError):
    """CSV không đủ trường hoặc không tuân thủ nhãn synthetic bắt buộc."""


@dataclass(frozen=True)
class HospitalDrugRecord:
    hospital_code: str
    brand_name: str
    active_ingredient: str
    strength: str
    dosage_form: str
    route: str
    manufacturer: str
    synthetic_label: str = ""

    @property
    def is_synthetic(self) -> bool:
        return self.synthetic_label == SYNTHETIC_RECORD_MARKER


@dataclass(frozen=True)
class DailyMedProduct:
    """Thông tin sản phẩm tối thiểu để đối chiếu, lấy từ snapshot DailyMed đã cho phép."""

    setid: str
    version: int
    active_ingredient: str
    strength: str
    dosage_form: str
    route: str
    published_date: str | None = None
    effective_time: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True)
class DailyMedMapping:
    hospital_code: str
    setid: str | None
    version: int | None
    status: str
    approved: bool
    mismatch_fields: tuple[str, ...]
    provenance: dict[str, str | int | None]


def _value(value: str) -> str:
    return " ".join((value or "").strip().split())


def _normalise(value: str) -> str:
    text = unicodedata.normalize("NFKD", _value(value)).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", text)


def _read_rows(path: Path) -> tuple[bool, list[dict[str, str]]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        raise CatalogValidationError("CSV rỗng")
    synthetic_file = lines[0].strip().casefold() == SYNTHETIC_FILE_MARKER
    csv_lines = lines[1:] if lines[0].lstrip().startswith("#") else lines
    reader = csv.DictReader(csv_lines)
    if reader.fieldnames is None:
        raise CatalogValidationError("CSV thiếu hàng tiêu đề")
    actual = tuple(field.strip() for field in reader.fieldnames)
    if actual != REQUIRED_COLUMNS:
        raise CatalogValidationError(f"Cột CSV phải đúng thứ tự: {', '.join(REQUIRED_COLUMNS)}")
    return synthetic_file, list(reader)


def import_hospital_catalog(path: str | Path) -> list[HospitalDrugRecord]:
    """Đọc và kiểm tra catalog; không truy cập mạng, database, hoặc dữ liệu bệnh nhân."""

    file_path = Path(path)
    synthetic_file, rows = _read_rows(file_path)
    if not rows:
        raise CatalogValidationError("CSV không có bản ghi")

    records: list[HospitalDrugRecord] = []
    seen_codes: set[str] = set()
    for number, row in enumerate(rows, start=2 + int(synthetic_file)):
        record = HospitalDrugRecord(**{column: _value(row.get(column, "")) for column in REQUIRED_COLUMNS})
        missing = [column for column in REQUIRED_COLUMNS[:-1] if not getattr(record, column)]
        if missing:
            raise CatalogValidationError(f"Dòng {number} thiếu: {', '.join(missing)}")
        if record.hospital_code in seen_codes:
            raise CatalogValidationError(f"Dòng {number} trùng hospital_code: {record.hospital_code}")
        seen_codes.add(record.hospital_code)
        if synthetic_file and not record.is_synthetic:
            raise CatalogValidationError(f"Dòng {number} synthetic phải có synthetic_label=SYNTHETIC")
        if not synthetic_file and record.is_synthetic:
            raise CatalogValidationError("Bản ghi SYNTHETIC yêu cầu tệp có dòng '# synthetic: true'")
        records.append(record)
    return records


def map_dailymed(record: HospitalDrugRecord, products: list[DailyMedProduct]) -> list[DailyMedMapping]:
    """Trả ứng viên khi *cả bốn* thuộc tính sản phẩm trùng khớp.

    Không có đường lùi theo hoạt chất đơn lẻ: hàm lượng, dạng bào chế hoặc đường dùng
    khác nhau đều là ``unknown``. ``approved`` luôn False vì quyết định này cần dược
    sĩ xác nhận và DailyMed không xác nhận sản phẩm lưu hành tại bệnh viện/Vietnam.
    """

    expected = {
        "active_ingredient": _normalise(record.active_ingredient),
        "strength": _normalise(record.strength),
        "dosage_form": _normalise(record.dosage_form),
        "route": _normalise(record.route),
    }
    mappings: list[DailyMedMapping] = []
    for product in products:
        actual = {
            "active_ingredient": _normalise(product.active_ingredient),
            "strength": _normalise(product.strength),
            "dosage_form": _normalise(product.dosage_form),
            "route": _normalise(product.route),
        }
        mismatches = tuple(field for field in expected if expected[field] != actual[field])
        if not mismatches:
            mappings.append(
                DailyMedMapping(
                    hospital_code=record.hospital_code,
                    setid=product.setid,
                    version=product.version,
                    status="candidate",
                    approved=False,
                    mismatch_fields=(),
                    provenance={
                        "source": "dailymed",
                        "setid": product.setid,
                        "version": product.version,
                        "published_date": product.published_date,
                        "effective_time": product.effective_time,
                        "retrieved_at": product.retrieved_at,
                    },
                )
            )
    if mappings:
        return mappings
    related = [
        product for product in products
        if _normalise(product.active_ingredient) == expected["active_ingredient"]
    ]
    if related:
        return [
            DailyMedMapping(
                hospital_code=record.hospital_code,
                setid=product.setid,
                version=product.version,
                status="unknown",
                approved=False,
                mismatch_fields=tuple(
                    field for field, value in {
                        "active_ingredient": _normalise(product.active_ingredient),
                        "strength": _normalise(product.strength),
                        "dosage_form": _normalise(product.dosage_form),
                        "route": _normalise(product.route),
                    }.items() if expected[field] != value
                ),
                provenance={
                    "source": "dailymed",
                    "setid": product.setid,
                    "version": product.version,
                    "published_date": product.published_date,
                    "effective_time": product.effective_time,
                    "retrieved_at": product.retrieved_at,
                    "reason": "no_exact_product_match",
                },
            )
            for product in related
        ]
    return [DailyMedMapping(
        hospital_code=record.hospital_code,
        setid=None,
        version=None,
        status="unknown",
        approved=False,
        mismatch_fields=("active_ingredient",),
        provenance={"source": "dailymed", "reason": "no_matching_ingredient"},
    )]
