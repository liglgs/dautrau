import type { Case, Store, User } from "../types";
export const users: User[] = [
  { id: "reviewer", name: "Linh · Người rà soát", role: "reviewer" },
  { id: "clinician", name: "Minh · Bác sĩ duyệt", role: "clinician" },
  { id: "clinician2", name: "An · Bác sĩ nhận bàn giao", role: "clinician" },
  { id: "responder", name: "Hà · Người phản hồi", role: "responder" },
  { id: "admin", name: "Quản trị demo", role: "admin" },
];
export function seed(): Store {
  const cases: Case[] = [1, 2, 3].map((n) => {
    const id = `SIM-00${n}`;
    const time = "2026-09-01T08:00:00+07:00";
    const s1 = `${id}-S1`,
      s2 = `${id}-S2`;
    const text =
      n === 1
        ? "Người bệnh khai đang dùng Thuốc B: 1 viên/lần, 1 lần/ngày. Dữ liệu mô phỏng."
        : "Đơn cũ: Thuốc A, 1 viên/lần. Chưa rõ người bệnh còn dùng. Ghi chú mô phỏng: tiếng Việt 🧪.";
    const order = "Y lệnh: Thuốc B, 1 viên/lần, 1 lần/ngày. Dữ liệu mô phỏng.";
    return {
      id,
      patient_id: `P-${id}`,
      encounter_id: `E-${id}`,
      reconciliation_at: time,
      visible_at: time,
      lifecycle: "draft",
      revision: 1,
      assigned: ["reviewer", "clinician", "clinician2"],
      scenario: n === 1 ? "matched" : n === 2 ? "verification" : "late",
      run: null,
      extraction_pending: false,
      sources: [
        {
          source_id: s1,
          version: 1,
          kind: n === 1 ? "medication_history" : "prior_prescription",
          filename: "history.txt",
          author_role: "reviewer",
          event_time: null,
          recorded_at: time,
          available_at: time,
          text,
        },
        {
          source_id: s2,
          version: 1,
          kind: "admission_order",
          filename: "order.txt",
          author_role: "clinician",
          event_time: time,
          recorded_at: time,
          available_at: time,
          text: order,
        },
      ],
      evidence: [
        {
          id: `${id}-E1`,
          source_id: s1,
          version: 1,
          quote: text,
          context: text,
        },
        {
          id: `${id}-E2`,
          source_id: s2,
          version: 1,
          quote: order,
          context: order,
        },
      ],
      assertions: [
        {
          id: `${id}-A1`,
          revision: 1,
          name: n === 1 ? "Thuốc B" : "Thuốc A",
          product: n === 1 ? "MED-B" : null,
          dose: "1 viên/lần",
          frequency: n === 1 ? "1 lần/ngày" : null,
          side: "history",
          assertion_type: n === 1 ? "patient_reported_taking" : "prescribed",
          evidence_ids: [`${id}-E1`],
        },
        {
          id: `${id}-A2`,
          revision: 1,
          name: "Thuốc B",
          product: "MED-B",
          dose: "1 viên/lần",
          frequency: "1 lần/ngày",
          side: "order",
          assertion_type: "ordered",
          evidence_ids: [`${id}-E2`],
        },
      ],
      issues:
        n === 1
          ? []
          : [
              {
                id: `${id}-I1`,
                revision: 1,
                title: "Xác minh trạng thái dùng Thuốc A",
                type: "information_gap",
                work_status: "new",
                evidence_status: "unknown",
                evidence_ids: [`${id}-E1`],
                history: [],
              },
            ],
      audit: ["Đã nạp hồ sơ mô phỏng"],
    };
  });
  const dispatches = cases.map((c, i) => ({
    id: `DISP-00${i + 1}`,
    case_id: c.id,
    patient_id: c.patient_id,
    assigned_reviewer: "reviewer",
    assigned_clinician: i === 2 ? "clinician2" : "clinician",
    priority: i === 0 ? ("normal" as const) : i === 1 ? ("high" as const) : ("urgent" as const),
    status: i === 0 ? ("in_progress" as const) : i === 1 ? ("assigned" as const) : ("escalated" as const),
    notes: i === 0 ? "Ca khớp dữ liệu - theo dõi rà soát" : i === 1 ? "Có đơn cũ Thuốc A chưa rõ tình trạng sử dụng" : "Nguồn bổ sung đến muộn sau khi đã lập nháp",
    updated_at: c.reconciliation_at,
  }));
  const chatMessages = [
    {
      id: "MSG-001",
      case_id: "SIM-001",
      sender: "agent" as const,
      text: "Xin chào! Tôi là Trợ lý AI MedReview (VMEC-03). Tôi đã phân tích ca SIM-001 (Bệnh nhân P-SIM-001). Cả 2 nguồn tiền sử và y lệnh đều thống nhất sử dụng Thuốc B (1 viên/lần, 1 lần/ngày). Hồ sơ không phát hiện chênh lệch hay khoảng trống thông tin nào.",
      timestamp: "2026-09-01T08:05:00+07:00",
      citations: [
        {
          source_id: "SIM-001-S1",
          version: 1,
          quote: "Người bệnh khai đang dùng Thuốc B: 1 viên/lần, 1 lần/ngày. Dữ liệu mô phỏng.",
        },
        {
          source_id: "SIM-001-S2",
          version: 1,
          quote: "Y lệnh: Thuốc B, 1 viên/lần, 1 lần/ngày. Dữ liệu mô phỏng.",
        },
      ],
      reasoning: [
        "Đọc văn bản trích xuất từ 2 nguồn history.txt và order.txt",
        "Đối chiếu tên hoạt chất/biệt dược: Thuốc B khớp hoàn toàn",
        "Đối chiếu liều và tần suất: 1 viên/lần, 1 lần/ngày khớp",
        "Kết luận: Ca khớp (matched), sẵn sàng tạo bản nháp trình duyệt",
      ],
    },
    {
      id: "MSG-002",
      case_id: "SIM-002",
      sender: "agent" as const,
      text: "Cảnh báo ca SIM-002: Đơn cũ có ghi nhận Thuốc A (1 viên/lần), tuy nhiên chưa rõ bệnh nhân có còn tiếp tục dùng tại thời điểm nhập viện hay không. Trong khi đó, y lệnh nhập viện chỉ có Thuốc B. Tôi đã tự động gắn nhãn 'information_gap' và đề xuất mở nhiệm vụ xác minh gửi kíp điều dưỡng tiếp nhận.",
      timestamp: "2026-09-01T08:10:00+07:00",
      citations: [
        {
          source_id: "SIM-002-S1",
          version: 1,
          quote: "Đơn cũ: Thuốc A, 1 viên/lần. Chưa rõ người bệnh còn dùng. Ghi chú mô phỏng: tiếng Việt 🧪.",
        },
      ],
      reasoning: [
        "Phát hiện Thuốc A trong đơn cũ nhưng không có y lệnh nhập viện",
        "Từ khóa 'Chưa rõ người bệnh còn dùng' kích hoạt quy tắc bảo vệ: không tự ý suy diễn",
        "Tạo vấn đề I1 (information_gap) và chuẩn bị phiếu xác minh",
      ],
    },
  ];
  return { cases, tasks: [], handoffs: [], reviews: [], receipts: {}, dispatches, chatMessages };
}
