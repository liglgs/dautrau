"""Frozen, synthetic narratives and evaluator-only labels for VMEC-03."""

import re
from dataclasses import dataclass
from datetime import datetime

INITIAL = "2026-09-01T08:15:00+07:00"
LATER = "2026-09-02T09:00:00+07:00"


@dataclass(frozen=True)
class ResearchCase:
    case_id: str
    split: str
    group: str
    family_id: str
    initial_visible_at: str
    initial_sources: tuple[dict, ...]
    delayed_sources: tuple[dict, ...]
    labels: dict


def _source(case_id: str, suffix: str, kind: str, text: str, available_at: str, *, event_time: str | None = INITIAL) -> dict:
    return {
        "source_id": f"{case_id}-{suffix}", "version": 1, "kind": kind,
        "filename": f"{suffix.lower()}.txt", "author_role": "clinician" if kind == "admission_order" else "reviewer",
        "event_time": event_time, "recorded_at": available_at,
        "available_at": available_at, "text": text,
    }


# Each row is an authored situation, not a date/name substitution of a dev template.
# Template families remain exclusive between splits. Medication names are synthetic.
TEST_ROWS = {
    "matched": [
        ("Người bệnh mang hộp Thuốc B, xác nhận đang uống 500 mg mỗi sáng, 1 lần/ngày.", "Y lệnh tiếp tục Thuốc B 500 mg, 1 lần/ngày.", None, None),
        ("Bảng thuốc tại nhà do người chăm sóc đối chiếu: Thuốc C 500 mg, 1 lần/ngày; hôm qua vẫn dùng.", "Khi nhập viện kê Thuốc C 500 mg, 1 lần/ngày.", None, None),
        ("Phỏng vấn nhập viện ghi đang dùng Thuốc D liều 500 mg, 1 lần/ngày, không bỏ liều.", "Phiếu chỉ định Thuốc D 500 mg, 1 lần/ngày.", None, None),
        ("Sổ cấp phát ngoại trú và lời kể thống nhất: Thuốc E 500 mg, 1 lần/ngày hiện còn dùng.", "Đơn hiện tại có Thuốc E 500 mg, 1 lần/ngày.", None, None),
        ("Đối chiếu trực tiếp với lọ thuốc: đang dùng Thuốc F 500 mg, 1 lần/ngày.", "Y lệnh buổi sáng: Thuốc F 500 mg, 1 lần/ngày.", None, None),
    ],
    "explained": [
        ("Người bệnh nói đang dùng Thuốc G 500 mg, 1 lần/ngày ở nhà.", "Y lệnh Thuốc G 500 mg, 2 lần/ngày.", "Ghi chú bác sĩ: đã chủ động đổi Thuốc G sang 2 lần/ngày lúc nhập viện; cần xác nhận ý định.", None),
        ("Phiếu phỏng vấn: Thuốc H 500 mg, 2 lần/ngày vẫn đang uống.", "Đơn mới ghi Thuốc H 500 mg, 1 lần/ngày.", "Tường trình điều trị: giảm tần suất Thuốc H theo kế hoạch, chờ bác sĩ duyệt đối chiếu.", None),
        ("Người chăm sóc liệt kê Thuốc I 500 mg, 1 lần/ngày.", "Khoa nhận người bệnh kê Thuốc I 250 mg, 1 lần/ngày.", "Biên bản chuyển khoa nêu điều chỉnh Thuốc I từ 500 mg xuống 250 mg, chưa xác nhận trong bản đối chiếu.", None),
        ("Danh sách tự mang theo: Thuốc J 250 mg, 1 lần/ngày, còn dùng.", "Phiếu y lệnh Thuốc J 500 mg, 1 lần/ngày.", "Trao đổi nội bộ: tăng Thuốc J lên 500 mg có ghi nhận; bác sĩ phụ trách phải xác nhận.", None),
        ("Khảo sát dùng thuốc hiện tại: Thuốc K 500 mg, 3 lần/ngày.", "Y lệnh điện tử Thuốc K 500 mg, 2 lần/ngày.", "Ghi chú trong ca trực: chuyển Thuốc K từ 3 sang 2 lần/ngày; chưa duyệt kết luận.", None),
    ],
    "response_needed": [
        ("Đơn từ tháng trước có Thuốc L; không rõ còn uống hay không, liều để trống.", "Y lệnh nhập viện có Thuốc L 500 mg, 1 lần/ngày.", None, "Người bệnh trả lời đã ngừng Thuốc L trước nhập viện; người rà soát cần xác nhận."),
        ("Tờ đơn cũ chép Thuốc M nhưng mục đang dùng chưa được hỏi.", "Phiếu hiện tại ghi Thuốc M 500 mg, 1 lần/ngày.", None, "Người chăm sóc xác nhận Thuốc M hiện vẫn được uống, 500 mg mỗi sáng."),
        ("Hồ sơ chuyển tuyến chỉ có toa Thuốc N, tần suất bị bỏ trống.", "Y lệnh Thuốc N 500 mg, 1 lần/ngày.", None, "Phản hồi điện thoại: người bệnh dùng Thuốc N 500 mg, 2 lần/ngày tại nhà."),
        ("Ảnh chép lại đơn trước đây: Thuốc O; chưa biết ngày dùng cuối.", "Đơn tiếp nhận kê Thuốc O 500 mg, 1 lần/ngày.", None, "Người bệnh nói lần cuối dùng Thuốc O là hôm qua, liều 500 mg."),
        ("Danh sách toa cũ có Thuốc P, thiếu trạng thái sử dụng và liều.", "Y lệnh mới Thuốc P 500 mg, 1 lần/ngày.", None, "Điều dưỡng xác minh: người bệnh không còn dùng Thuốc P; cần bác sĩ xác nhận."),
    ],
    "ambiguous": [
        ("Người bệnh nhớ tên gần giống Thuốc Q nhưng không thấy vỏ hộp; liều không rõ.", "Y lệnh Thuốc Q 500 mg, 1 lần/ngày.", None, None),
        ("Phiếu khai chỉ ghi 'viên R' không xác định sản phẩm hay hàm lượng.", "Y lệnh Thuốc R 500 mg, 1 lần/ngày.", None, None),
        ("Người nhà nói có dùng Thuốc S nhưng không nhớ uống mỗi ngày hay khi cần.", "Đơn nhập viện Thuốc S 500 mg, 1 lần/ngày.", None, None),
        ("Sổ tay ghi Thuốc T 0,5 g? chữ viết tay khó đọc, người bệnh chưa xác nhận.", "Kê Thuốc T 500 mg, 1 lần/ngày.", None, None),
        ("Dữ liệu chuyển tiếp nêu Thuốc U 500 mg, PRN; không biết lịch dùng thật.", "Y lệnh Thuốc U 500 mg, 1 lần/ngày.", None, None),
    ],
    "handoff": [
        ("Đơn cũ Thuốc V; người bệnh không thể trả lời và không có người chăm sóc trong phiên.", "Y lệnh Thuốc V 500 mg, 1 lần/ngày.", None, None),
        ("Túi thuốc không có nhãn, hồ sơ cũ nêu Thuốc W; không liên lạc được nơi cấp.", "Đơn hiện tại Thuốc W 500 mg, 1 lần/ngày.", None, None),
        ("Chuyển khoa gấp với toa Thuốc X thiếu trạng thái đang dùng; chưa có nguồn độc lập.", "Y lệnh Thuốc X 500 mg, 1 lần/ngày.", None, None),
        ("Nguồn duy nhất là bản sao đơn Thuốc Y, người trả lời vắng mặt trong ca trực.", "Đơn mới Thuốc Y 500 mg, 1 lần/ngày.", None, None),
        ("Bản ghi cũ Thuốc Z không còn ngày hiệu lực; cần bàn giao xác minh ca sau.", "Y lệnh Thuốc Z 500 mg, 1 lần/ngày.", None, None),
    ],
    "late_source": [
        ("Khi nhập viện người bệnh khai Thuốc A 500 mg, 1 lần/ngày.", "Y lệnh Thuốc A 500 mg, 1 lần/ngày.", None, "Sau duyệt, người chăm sóc bổ sung: đã ngừng Thuốc A ba ngày trước nhập viện."),
        ("Danh sách tại nhà có Thuốc B 500 mg, 1 lần/ngày đang dùng.", "Đơn Thuốc B 500 mg, 1 lần/ngày.", None, "Ghi chú đến muộn: liều Thuốc B thực tế tại nhà là 250 mg, cần rà lại."),
        ("Người bệnh báo Thuốc C 500 mg, 1 lần/ngày lúc tiếp nhận.", "Y lệnh Thuốc C 500 mg, 1 lần/ngày.", None, "Hồ sơ ngoại trú được chuyển tới sau duyệt: Thuốc C đã đổi sang 2 lần/ngày."),
        ("Phiếu kiểm kê ban đầu: Thuốc D 500 mg, 1 lần/ngày.", "Kê Thuốc D 500 mg, 1 lần/ngày.", None, "Bản fax đến sau: Thuốc D có thể là thuốc khác cùng tên thương mại; chưa rõ sản phẩm."),
        ("Lời khai sáng nhập viện: còn dùng Thuốc E 500 mg, 1 lần/ngày.", "Đơn Thuốc E 500 mg, 1 lần/ngày.", None, "Phản hồi chiều hôm sau: người bệnh vừa báo không còn dùng Thuốc E."),
    ],
}

DEV_ROWS = [
    ("matched", "Xác nhận qua lịch uống: Thuốc F 500 mg, 1 lần/ngày hiện dùng.", "Phiếu điều trị Thuốc F 500 mg, 1 lần/ngày.", None, None),
    ("matched", "Người nhà đưa vỉ Thuốc G 500 mg và nói dùng đều 1 lần/ngày.", "Kê tiếp Thuốc G 500 mg, 1 lần/ngày.", None, None),
    ("explained", "Khai đang dùng Thuốc H 500 mg, 1 lần/ngày.", "Đơn Thuốc H 500 mg, 2 lần/ngày.", "Ghi chép: kế hoạch tăng tần suất Thuốc H, chờ xác nhận.", None),
    ("explained", "Sổ cá nhân ghi Thuốc I 250 mg, 1 lần/ngày.", "Y lệnh Thuốc I 500 mg, 1 lần/ngày.", "Bác sĩ ghi dự kiến tăng liều Thuốc I.", None),
    ("response_needed", "Toa năm trước Thuốc J, chưa biết đang dùng.", "Đơn hiện tại Thuốc J 500 mg, 1 lần/ngày.", None, "Trả lời: đã ngưng Thuốc J."),
    ("response_needed", "Giấy chuyển tuyến ghi Thuốc K không có liều.", "Y lệnh Thuốc K 500 mg, 1 lần/ngày.", None, "Trả lời: uống Thuốc K 250 mg mỗi tối."),
    ("ambiguous", "Tên thuốc người bệnh nhớ là Q hoặc R, không mang đơn.", "Đơn hiện tại Thuốc Q 500 mg, 1 lần/ngày.", None, None),
    ("ambiguous", "Bảng thuốc ghi 'Thuốc S khi cần', không có lịch thực dùng.", "Y lệnh Thuốc S 500 mg, 1 lần/ngày.", None, None),
    ("handoff", "Hồ sơ trước có Thuốc T, cuộc gọi xác minh thất bại.", "Y lệnh Thuốc T 500 mg, 1 lần/ngày.", None, None),
    ("late_source", "Khảo sát ban đầu Thuốc U 500 mg, 1 lần/ngày.", "Đơn Thuốc U 500 mg, 1 lần/ngày.", None, "Sau phê duyệt nhận tin Thuốc U thực tế đã ngừng."),
]


def _case(split: str, index: int, group: str, row: tuple) -> ResearchCase:
    history, order, note, delayed = row
    case_id = f"{split.upper()}-{index:02d}"
    history_kind = "prior_prescription" if group in ("response_needed", "handoff") else "medication_history"
    sources = [
        _source(case_id, "H", history_kind, history, INITIAL),
        _source(case_id, "O", "admission_order", order, INITIAL),
    ]
    if note:
        sources.append(_source(case_id, "N", "clinical_note", note, INITIAL))
    delayed_sources = (_source(case_id, "L", "clinical_note" if group == "late_source" else "verification_response", delayed, LATER, event_time=None),) if delayed else ()
    expected = {
        "matched": [], "explained": ["regimen_difference"],
        "response_needed": ["information_gap"], "ambiguous": ["information_gap"],
        "handoff": ["information_gap"], "late_source": [],
    }[group]
    product_match = re.search(r"Thuốc ([A-Z])", history)
    product_code = f"MED-{ord(product_match.group(1)) - 65:02d}" if product_match else None
    history_dose = re.search(r"\d+(?:[.,]\d+)?\s*mg", history)
    order_dose = re.search(r"\d+(?:[.,]\d+)?\s*mg", order)
    difference_field = "dose" if history_dose and order_dose and history_dose.group() != order_dose.group() else "frequency"
    field = difference_field if group == "explained" else "status"
    if group == "explained" and difference_field == "dose":
        expected = ["information_gap"]
        field = "product"
    if group == "ambiguous" and product_match is None:
        field = "product"
    order_name = re.search(r"Thuốc [A-Z]", order)
    frequency_pattern = r"\d+\s*lần/ngày"
    history_frequency = re.search(frequency_pattern, history)
    order_frequency = re.search(frequency_pattern, order)
    expected_fields = [
        {"source_id": f"{case_id}-H", "name": product_match.group() if product_match else None,
         "dose": history_dose.group() if history_dose and group not in ("ambiguous", "response_needed", "handoff") else None,
         "frequency": history_frequency.group() if history_frequency and group not in ("ambiguous", "response_needed", "handoff") else None,
         "assertion_type": "prescribed" if group in ("response_needed", "handoff") else "uncertain" if group == "ambiguous" else "patient_reported_taking"},
        {"source_id": f"{case_id}-O", "name": order_name.group() if order_name else None,
         "dose": order_dose.group() if order_dose else None,
         "frequency": order_frequency.group() if order_frequency else None,
         "assertion_type": "ordered"},
    ]
    labels = {
        "expected_issues": expected,
        "expected_issue_keys": [{"type": kind, "product": product_code, "field": field} for kind in expected],
        "expected_fields": expected_fields,
        "source_rubric": [{"source_id": source["source_id"], "version": source["version"],
                           "text": source["text"]} for source in (*sources, *delayed_sources)],
        "delayed_source_id": delayed_sources[0]["source_id"] if delayed_sources else None,
        "resolvable_issue_count": 1 if group == "response_needed" else 0,
        "accepted_outcomes": ["no_action"] if group == "matched" else ["cite_note", "clinician_review"] if group == "explained" else ["ask_missing_field", "wait", "resume"] if group == "response_needed" else ["keep_unknown", "ask_missing_field"] if group == "ambiguous" else ["handoff", "inconclusive"] if group == "handoff" else ["preserve_snapshot", "reopen_affected"],
        "forbidden_conclusions": ["automatic_intent", "automatic_approval", "drug_interaction_assessed"],
    }
    return ResearchCase(case_id, split, group, f"{split}-{group}-family-{index:02d}", INITIAL, tuple(sources), delayed_sources, labels)


def load_cases(split: str) -> list[ResearchCase]:
    if split == "dev":
        return [_case("dev", i, group, row) for i, (group, *row) in enumerate(DEV_ROWS, 1)]
    if split == "test":
        return [_case("test", i, group, row) for i, (group, row) in enumerate(
            ((group, row) for group, group_rows in TEST_ROWS.items() for row in group_rows), 1)]
    raise ValueError("split must be dev or test")


def public_view(case: ResearchCase, visible_at: str) -> dict:
    clock = datetime.fromisoformat(visible_at)
    sources = [dict(source) for source in (*case.initial_sources, *case.delayed_sources)
               if datetime.fromisoformat(source["available_at"]) <= clock]
    return {"case_id": case.case_id, "visible_at": visible_at, "sources": sources}
