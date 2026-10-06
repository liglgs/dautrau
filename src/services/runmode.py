"""RT-01: khoá tổ hợp chế độ chạy sai và nói thẳng đang dùng nguồn/mô hình thật hay phát lại.

Vì sao cần: ``MVP_SOURCE_MODE`` và ``MVP_EVIDENCE_MODE`` là hai công tắc độc lập. Một số tổ hợp
chạy được nhưng cho ra kết quả **trông như thật** trong khi một nửa đường ống là dữ liệu mẫu —
ví dụ bật nguồn thật để tải tài liệu PubMed rồi vẫn gắn bằng chứng fixture lên chúng. Đó là loại
sai sót tệ nhất với công cụ này, vì người đọc hồ sơ không có cách nào nhận ra.

Module này làm hai việc:

* :func:`validate_run_mode` — chặn tổ hợp sai ngay lúc khởi động, kèm thông báo nói rõ phải sửa
  biến môi trường nào;
* :func:`resolve_run_mode` — mô tả trung thực chế độ đang chạy, để nhật ký, API và giao diện nói
  cùng một câu: nguồn nào thật, bằng chứng nào thật, có gọi mô hình hay không.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.services.errors import invalid_state

if TYPE_CHECKING:  # pragma: no cover - chỉ để tránh vòng nhập lúc chạy
    from src.config import Settings

#: Giá trị hợp lệ của ``MVP_SOURCE_MODE`` (khớp ``Settings.mvp_source_mode``).
SOURCE_FIXTURE = "fixture"
SOURCE_LIVE = "live"
SOURCE_WAREHOUSE = "warehouse"

#: Giá trị hợp lệ của ``MVP_EVIDENCE_MODE`` (khớp ``Settings.mvp_evidence_mode``).
EVIDENCE_FIXTURE = "fixture"
EVIDENCE_PERSON3_DEMO = "person3_demo"
EVIDENCE_PERSON3 = "person3"

#: Giá trị hợp lệ của ``MVP_PUBMED_MODE`` (khớp ``Settings.mvp_pubmed_mode``).
PUBMED_API = "api"
PUBMED_LOCAL = "local"

#: Nguồn thật: đọc mạng (``live``) hoặc đọc kho ELT thật (``warehouse``).
REAL_SOURCES = frozenset({SOURCE_LIVE, SOURCE_WAREHOUSE})

#: Chế độ bằng chứng có gọi mô hình để trích đoạn, thay vì đọc fixture/phát lại.
MODEL_BACKED_EVIDENCE = frozenset({EVIDENCE_PERSON3})

_SOURCE_LABELS = {
    SOURCE_FIXTURE: "nguồn mẫu (fixture)",
    SOURCE_LIVE: "nguồn thật (PubMed/DailyMed/openFDA)",
    SOURCE_WAREHOUSE: "kho dữ liệu ELT thật",
}

#: Nhãn riêng cho ``live`` khi PubMed đọc corpus đã nhập thay vì gọi mạng. Gọi chung là "qua mạng"
#: ở trường hợp này là nói sai: không có yêu cầu HTTP nào ra ngoài.
_SOURCE_LIVE_LOCAL_PUBMED = "nguồn thật, riêng PubMed đọc corpus đã nhập (không gọi mạng)"

_EVIDENCE_LABELS = {
    EVIDENCE_FIXTURE: "bằng chứng mẫu (fixture)",
    EVIDENCE_PERSON3_DEMO: "bằng chứng phát lại (kịch bản demo)",
    EVIDENCE_PERSON3: "bằng chứng do mô hình trích từ nguồn thật",
}


class RunMode(BaseModel):
    """Mô tả trung thực chế độ đang chạy, để không ai phải đoán kết quả này là thật hay mẫu."""

    model_config = ConfigDict(extra="forbid")

    source_mode: str
    evidence_mode: str
    pubmed_mode: str
    #: ``True`` khi nguồn tài liệu đến từ mạng hoặc kho ELT thật.
    sources_are_real: bool
    #: ``True`` khi bằng chứng do mô hình trích từ tài liệu thật (không phải fixture/phát lại).
    evidence_is_real: bool
    #: ``True`` khi có gọi mô hình ngôn ngữ thật trong lượt chạy.
    model_is_real: bool
    #: ``True`` khi bất kỳ phần nào của kết quả là dữ liệu mẫu hoặc phát lại.
    synthetic: bool
    #: Câu mô tả một dòng, dùng cho nhật ký và giao diện.
    label: str
    #: Cảnh báo không chặn chạy nhưng phải hiện cho người đọc: chế độ bằng chứng cần mô hình nhưng
    #: chưa có khoá, hoặc PubMed đang đọc corpus đã nhập thay vì gọi mạng.
    warnings: list[str] = Field(default_factory=list)

    def as_event_payload(self) -> dict[str, object]:
        """Payload gọn để ghi vào nhật ký sự kiện của một lượt điều tra."""
        return {
            "source_mode": self.source_mode,
            "evidence_mode": self.evidence_mode,
            "pubmed_mode": self.pubmed_mode,
            "synthetic": self.synthetic,
            "label": self.label,
        }


def _forbidden(combination: str, message: str, remedy: str):
    """Dựng lỗi ``invalid_state`` kèm tổ hợp bị chặn và cách sửa."""
    return invalid_state(
        message,
        {"combination": combination, "remedy": remedy},
    )


def validate_run_mode(settings: Settings) -> None:
    """Chặn tổ hợp chế độ cho ra kết quả trông như thật nhưng thật ra là dữ liệu mẫu.

    Gọi ở chỗ khởi tạo store/runner để lỗi hiện ngay lúc dựng app, không đợi tới request đầu tiên.
    """
    source = settings.mvp_source_mode
    evidence = settings.mvp_evidence_mode

    if source in REAL_SOURCES and evidence == EVIDENCE_FIXTURE:
        raise _forbidden(
            f"{source}+{evidence}",
            "Tổ hợp MVP_SOURCE_MODE="
            f"{source} với MVP_EVIDENCE_MODE=fixture bị chặn: hệ thống sẽ tải tài liệu thật rồi "
            "gắn bằng chứng mẫu lên chúng, nên hồ sơ trông như thật nhưng bằng chứng là dữ liệu mẫu.",
            "Đặt MVP_EVIDENCE_MODE=person3 để trích bằng chứng thật, hoặc đặt "
            "MVP_SOURCE_MODE=fixture nếu chỉ muốn chạy bản demo.",
        )

    if evidence == EVIDENCE_PERSON3 and source not in REAL_SOURCES:
        raise _forbidden(
            f"{source}+{evidence}",
            f"Tổ hợp MVP_EVIDENCE_MODE=person3 với MVP_SOURCE_MODE={source} bị chặn: không có "
            "tài liệu thật nào để trích bằng chứng.",
            "Đặt MVP_SOURCE_MODE=live hoặc MVP_SOURCE_MODE=warehouse.",
        )

    if evidence == EVIDENCE_PERSON3_DEMO and source in REAL_SOURCES:
        raise _forbidden(
            f"{source}+{evidence}",
            f"Tổ hợp MVP_EVIDENCE_MODE=person3_demo với MVP_SOURCE_MODE={source} bị chặn: kịch "
            "bản demo sẽ gắn bằng chứng phát lại lên tài liệu tải từ nguồn thật.",
            "Đặt MVP_SOURCE_MODE=fixture cho bản demo, hoặc MVP_EVIDENCE_MODE=person3 để chạy thật.",
        )


def _has_model_key(settings: Settings) -> bool:
    """Có khoá mô hình nào chưa — không có thì bước trích bằng chứng không thể chạy thật."""
    return bool(settings.openai_api_key.strip() or settings.gemini_keys)


def resolve_run_mode(settings: Settings) -> RunMode:
    """Mô tả chế độ đang chạy; không ném lỗi (dùng cho nhật ký, API và giao diện)."""
    source = settings.mvp_source_mode
    evidence = settings.mvp_evidence_mode

    sources_are_real = source in REAL_SOURCES
    evidence_is_real = evidence in MODEL_BACKED_EVIDENCE and sources_are_real
    model_is_real = evidence in MODEL_BACKED_EVIDENCE

    warnings: list[str] = []
    # Hai tổ hợp ``person3 + nguồn mẫu`` và ``nguồn thật + fixture`` từng có nhánh cảnh báo ở đây,
    # nhưng ``validate_run_mode`` đã ném lỗi trước đó nên chúng không bao giờ chạy tới. Giữ lại chỉ
    # tạo cảm giác đã kiểm tra mà thực ra không.
    if model_is_real and not _has_model_key(settings):
        # Nhãn nói "mô hình trích từ nguồn thật" trong khi không có khoá nào: kết quả sẽ là phát lại.
        warnings.append(
            "Chưa cấu hình khoá mô hình (OPENAI_API_KEY/GEMINI_API_KEY): bước trích bằng chứng "
            "không gọi được mô hình thật, nên kết quả sẽ là phát lại."
        )
    if source == SOURCE_LIVE and settings.mvp_pubmed_mode == PUBMED_LOCAL:
        warnings.append(
            "MVP_PUBMED_MODE=local: PubMed đọc corpus đã nhập trên máy, không gọi mạng. "
            "Tài liệu vẫn là bản thật đã nhập, nhưng không phải kết quả tìm kiếm trực tiếp."
        )

    if source == SOURCE_LIVE and settings.mvp_pubmed_mode == PUBMED_LOCAL:
        source_label = _SOURCE_LIVE_LOCAL_PUBMED
    else:
        source_label = _SOURCE_LABELS.get(source, source)

    synthetic = not (sources_are_real and evidence_is_real)
    label = (
        f"{source_label} · {_EVIDENCE_LABELS.get(evidence, evidence)}"
        + ("" if model_is_real else " · không gọi mô hình")
    )
    return RunMode(
        source_mode=source,
        evidence_mode=evidence,
        pubmed_mode=settings.mvp_pubmed_mode,
        sources_are_real=sources_are_real,
        evidence_is_real=evidence_is_real,
        model_is_real=model_is_real,
        synthetic=synthetic,
        label=label,
        warnings=warnings,
    )


def get_run_mode() -> dict[str, object]:
    """Chế độ chạy hiện tại, để API trả cho giao diện biết kết quả này là thật hay mẫu."""
    from src.config import get_settings

    return resolve_run_mode(get_settings()).model_dump()


def describe_run_mode(settings: Settings) -> str:
    """Một dòng cho nhật ký khởi động, nói rõ lượt chạy này là thật hay mẫu."""
    mode = resolve_run_mode(settings)
    tag = "DỮ LIỆU MẪU/PHÁT LẠI" if mode.synthetic else "DỮ LIỆU THẬT"
    return f"Chế độ chạy: {tag} — {mode.label}"
