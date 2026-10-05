import type {
  AgentStep,
  AuditEntry,
  DocumentRecord,
  EvidenceItem,
  Gap,
  IngestionJob,
  Investigation,
  EvalRun,
} from "@/lib/types";

/** Toàn bộ dữ liệu dưới đây là DỮ LIỆU MINH HỌA TỔNG HỢP. Định danh dạng DEMO-xxxx. */

const now = Date.now();
const iso = (minutesAgo: number) => new Date(now - minutesAgo * 60_000).toISOString();

export const DEMO_DOCUMENTS: DocumentRecord[] = [
  {
    id: "DOC-0001",
    source: "pubmed",
    title: "Nghiên cứu đoàn hệ (minh họa): metformin ở bệnh nhân suy thận mức độ trung bình",
    origin: "auto",
    text:
      "Bối cảnh. Metformin được dùng rộng rãi cho đái tháo đường týp 2. Ở bệnh nhân suy thận, đào thải giảm " +
      "và nồng độ thuốc có thể tăng. Phương pháp. Chúng tôi theo dõi 1.204 bệnh nhân (eGFR 30–44 mL/ph/1,73 m²) " +
      "dùng metformin liều trung bình 1.000 mg/ngày trong 24 tháng. Kết quả. Có 6 ca nhiễm toan lactic được ghi nhận, " +
      "tất cả đều có yếu tố thúc đẩy cấp tính (nhiễm trùng, mất nước, dùng thuốc cản quang). " +
      "Kết luận. Dữ liệu quan sát cho thấy cần theo dõi chức năng thận định kỳ; nghiên cứu không đủ mạnh để " +
      "kết luận về liều cao. Hạn chế. Thiết kế quan sát, cỡ mẫu nhỏ ở nhóm suy thận nặng.",
    sha256: "9f2c1a7d4b8e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcd",
    hashStatus: "verified",
    retrievedAt: iso(52),
    url: "https://pubmed.ncbi.nlm.nih.gov/DEMO-0001/",
    meta: { journal: "Tạp chí minh họa", year: "2023", doi: "10.0000/demo.0001", type: "cohort" },
  },
  {
    id: "DOC-0002",
    source: "dailymed",
    title: "Nhãn thuốc minh họa — metformin (mục 5: cảnh báo và thận trọng)",
    origin: "auto",
    text:
      "5.1 Nhiễm toan lactic. Đã có báo cáo về nhiễm toan lactic ở bệnh nhân dùng metformin, chủ yếu ở người " +
      "suy thận hoặc có yếu tố thúc đẩy. 5.2 Suy thận. Đánh giá chức năng thận trước khi bắt đầu và định kỳ. " +
      "Không khuyến cáo khởi trị khi eGFR dưới 45 mL/ph/1,73 m². 5.3 Liều. Không vượt quá 1.000 mg/ngày ở " +
      "bệnh nhân eGFR 30–44 mL/ph/1,73 m². Nội dung minh họa, không phải nhãn thuốc thật.",
    sha256: "1b2c3d4e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcdef01",
    hashStatus: "verified",
    retrievedAt: iso(51),
    url: "https://dailymed.nlm.nih.gov/DEMO-0002",
    meta: { section: "5", labelVersion: "DEMO-2024-01" },
  },
  {
    id: "DOC-0003",
    source: "faers",
    title: "Bộ đếm báo cáo tự nguyện minh họa (FAERS DEMO) — metformin / lactic acidosis",
    origin: "auto",
    text:
      "Bộ đếm báo cáo minh họa: 412 báo cáo có nhắc tới metformin và nhiễm toan lactic trong khoảng thời gian giả lập. " +
      "Báo cáo tự nguyện KHÔNG cho biết tỷ lệ mắc, không chứng minh quan hệ nhân quả, và không có mẫu số người phơi nhiễm.",
    sha256: "2c3d4e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcdef0123",
    hashStatus: "unchecked",
    retrievedAt: iso(50),
    url: "https://open.fda.gov/DEMO-0003",
    meta: { count: "412", window: "DEMO-2020..DEMO-2024" },
  },
  {
    id: "DOC-0004",
    source: "pubmed",
    title: "Tổng quan hệ thống (minh họa): liều metformin và biến cố bất lợi",
    origin: "auto",
    text:
      "Tổng quan minh họa 18 nghiên cứu. Ở nhóm dùng liều trên 2.000 mg/ngày, tỷ lệ biến cố được báo cáo cao hơn " +
      "so với liều 1.000 mg/ngày. Các nghiên cứu đều ở bệnh nhân chức năng thận bình thường. " +
      "Bằng chứng ở bệnh nhân suy thận mức độ 3b còn thiếu.",
    sha256: "3d4e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcdef012345",
    hashStatus: "verified",
    retrievedAt: iso(48),
    url: "https://pubmed.ncbi.nlm.nih.gov/DEMO-0004/",
    meta: { journal: "Tạp chí minh họa", year: "2022", doi: "10.0000/demo.0004", type: "review" },
  },
  {
    id: "DOC-0005",
    source: "pubmed",
    title: "Báo cáo ca (minh họa): nhiễm toan lactic ở bệnh nhân dùng liều cao",
    origin: "auto",
    text:
      "Bệnh nhân nam 68 tuổi, eGFR 38 mL/ph/1,73 m², dùng metformin 2.500 mg/ngày, nhập viện vì toan chuyển hóa. " +
      "Báo cáo ca không thể dùng để suy ra tỷ lệ mắc và không xác lập quan hệ nhân quả.",
    sha256: "4e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcdef01234567",
    hashStatus: "mismatch",
    retrievedAt: iso(47),
    url: "https://pubmed.ncbi.nlm.nih.gov/DEMO-0005/",
    meta: { journal: "Tạp chí minh họa", year: "2021", type: "case_report" },
  },
  {
    id: "DOC-0006",
    source: "dailymed",
    title: "Nhãn thuốc minh họa — telmisartan (phù mạch)",
    origin: "auto",
    text:
      "Phù mạch đã được báo cáo khi dùng telmisartan, thường ở người lớn và không phụ thuộc liều trong các ca được " +
      "báo cáo. Ngừng thuốc ngay khi nghi ngờ phù mạch. Nội dung minh họa.",
    sha256: "5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcdef0123456789",
    hashStatus: "verified",
    retrievedAt: iso(120),
    url: "https://dailymed.nlm.nih.gov/DEMO-0006",
    meta: { section: "5", labelVersion: "DEMO-2024-02" },
  },
];

export const DEMO_INVESTIGATIONS: Investigation[] = [
  {
    id: "INV-0001",
    claim: {
      drug: "metformin",
      adverseEvent: "nhiễm toan lactic",
      population: "suy thận giai đoạn 3b (eGFR 30–44)",
      dose: { op: ">=", value: 2000, unit: "mg/ngày" },
      route: "đường uống",
      timeWindow: "24 tháng",
      rawText: "Metformin gây nhiễm toan lactic ở bệnh nhân suy thận giai đoạn 3b với liều ≥2.000 mg/ngày.",
    },
    sources: ["pubmed", "dailymed", "faers"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 6, docs: 7, tokens: 41_820, elapsedMs: 214_000 },
    runStatus: "completed",
    assessment: {
      status: "supported_for_scope",
      rationale:
        "Có bằng chứng ủng hộ trong phạm vi hẹp hơn nhận định (liều trung bình), đã tìm chiều phản bác và có nguồn thứ hai.",
      coverage: {
        drug: "verified",
        adverseEvent: "verified",
        population: "partial",
        dose: "partial",
        route: "verified",
        timeWindow: "not_specified",
      },
    },
    reviewState: "approved",
    reviewedBy: "DS. Trần Minh",
    reviewedAt: iso(300),
    version: 3,
    createdBy: "investigator@demo",
    createdAt: iso(420),
  },
  {
    id: "INV-0002",
    claim: { drug: "thuốc A (minh họa)", adverseEvent: "viêm gan", population: "người trưởng thành", dose: { op: "=", value: 50, unit: "mg/ngày" } },
    sources: ["pubmed", "dailymed"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 5, docs: 4, tokens: 22_400, elapsedMs: 160_000 },
    runStatus: "completed",
    assessment: {
      status: "contradicted_for_scope",
      rationale: "Bằng chứng phản bác trong đúng phạm vi: các nghiên cứu đối chứng không cho thấy tín hiệu tăng men gan ở liều 50 mg/ngày.",
      coverage: { drug: "verified", adverseEvent: "verified", population: "verified", dose: "verified", route: "not_specified", timeWindow: "missing" },
    },
    reviewState: "approved",
    reviewedBy: "DS. Trần Minh",
    reviewedAt: iso(600),
    version: 2,
    createdBy: "investigator@demo",
    createdAt: iso(700),
  },
  {
    id: "INV-0003",
    claim: { drug: "thuốc B (minh họa)", adverseEvent: "kéo dài khoảng QT", population: "người ≥65 tuổi", route: "đường uống" },
    sources: ["pubmed", "dailymed", "faers"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 7, docs: 9, tokens: 55_100, elapsedMs: 260_000 },
    runStatus: "completed",
    assessment: {
      status: "supported_for_scope",
      rationale: "Có bằng chứng ủng hộ trong phạm vi ở nhóm ≥65 tuổi; cần theo dõi điện tâm đồ khi dùng đồng thời thuốc kéo dài QT.",
      coverage: { drug: "verified", adverseEvent: "verified", population: "verified", dose: "not_specified", route: "verified", timeWindow: "partial" },
    },
    reviewState: "needs_rereview",
    reviewedBy: "DS. Trần Minh",
    reviewedAt: iso(200),
    invalidatedReason: "Reviewer đã sửa trích dẫn của E2 sau lần duyệt trước.",
    version: 4,
    createdBy: "investigator@demo",
    createdAt: iso(880),
  },
  {
    id: "INV-0004",
    claim: { drug: "thuốc C (minh họa)", adverseEvent: "hạ đường huyết", population: "trẻ em" },
    sources: ["pubmed", "faers"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 8, docs: 12, tokens: 61_000, elapsedMs: 300_000 },
    runStatus: "waiting_for_review",
    checkpoint: "dossier",
    assessment: {
      status: "insufficient_evidence",
      rationale:
        "Chưa đủ bằng chứng để kết luận: chỉ có báo cáo ca và dữ liệu tự nguyện, không có nghiên cứu có nhóm đối chứng ở trẻ em.",
      coverage: { drug: "verified", adverseEvent: "partial", population: "missing", dose: "missing", route: "not_specified", timeWindow: "missing" },
    },
    reviewState: "not_reviewed",
    version: 1,
    createdBy: "investigator@demo",
    createdAt: iso(90),
  },
  {
    id: "INV-0005",
    claim: {
      drug: "thuốc D (minh họa)",
      adverseEvent: "xuất huyết tiêu hóa",
      population: "mọi bệnh nhân",
      dose: { op: "=", value: 20, unit: "mg/ngày" },
    },
    sources: ["pubmed", "dailymed"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 6, docs: 8, tokens: 38_900, elapsedMs: 190_000 },
    runStatus: "waiting_for_review",
    assessment: {
      status: "scope_mismatch",
      rationale:
        "Bằng chứng tìm được nằm ngoài phạm vi nhận định: nghiên cứu dùng 100 mg/ngày ở người ≥65 tuổi, trong khi nhận định nói 20 mg/ngày cho mọi bệnh nhân.",
      coverage: { drug: "verified", adverseEvent: "verified", population: "partial", dose: "missing", route: "not_specified", timeWindow: "missing" },
    },
    reviewState: "not_reviewed",
    version: 1,
    createdBy: "investigator@demo",
    createdAt: iso(70),
  },
  {
    id: "INV-0006",
    claim: { drug: "thuốc E (minh họa)", adverseEvent: "rụng tóc" },
    sources: ["dailymed", "faers"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 4, docs: 3, tokens: 15_300, elapsedMs: 95_000 },
    runStatus: "completed",
    assessment: {
      status: "out_of_scope",
      rationale: "Biến cố không thuộc nhóm được hệ thống hỗ trợ điều tra theo nhãn thuốc; đề nghị chuyển chuyên viên.",
      coverage: { drug: "verified", adverseEvent: "not_specified", population: "not_specified", dose: "not_specified", route: "not_specified", timeWindow: "not_specified" },
    },
    reviewState: "approved",
    reviewedBy: "DS. Trần Minh",
    reviewedAt: iso(1000),
    version: 2,
    createdBy: "investigator@demo",
    createdAt: iso(1200),
  },
  {
    id: "INV-0007",
    claim: {
      drug: "Glucophage",
      adverseEvent: "nhiễm toan lactic",
      population: "suy thận giai đoạn 3b",
      rawText: "Glucophage gây nhiễm toan lactic ở bệnh nhân suy thận giai đoạn 3b.",
    },
    sources: ["pubmed", "dailymed", "faers"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 5, docs: 5, tokens: 34_600, elapsedMs: 132_000 },
    runStatus: "running",
    reviewState: "not_reviewed",
    version: 2,
    createdBy: "investigator@demo",
    createdAt: iso(12),
  },
  {
    id: "INV-0008",
    claim: { drug: "thuốc F (minh họa)", adverseEvent: "đau cơ", population: "phụ nữ mang thai" },
    sources: ["pubmed", "dailymed", "faers"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 8, docs: 14, tokens: 70_200, elapsedMs: 355_000 },
    runStatus: "completed",
    assessment: {
      status: "requires_human_review",
      rationale: "Có tín hiệu nhưng dữ liệu ở phụ nữ mang thai quá thưa; bắt buộc chuyên viên can thiệp trước khi dùng cho bất kỳ kết luận nào.",
      coverage: { drug: "verified", adverseEvent: "partial", population: "missing", dose: "missing", route: "missing", timeWindow: "missing" },
    },
    reviewState: "not_reviewed",
    version: 1,
    createdBy: "investigator@demo",
    createdAt: iso(1500),
  },
  {
    id: "INV-0009",
    claim: { drug: "thuốc G (minh họa)", adverseEvent: "phản ứng da nặng", population: "người lớn" },
    sources: ["pubmed", "dailymed"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 3, docs: 2, tokens: 9_800, elapsedMs: 61_000 },
    runStatus: "failed",
    reviewState: "not_reviewed",
    version: 1,
    createdBy: "investigator@demo",
    createdAt: iso(2600),
  },
  {
    id: "INV-0010",
    claim: { drug: "telmisartan", adverseEvent: "phù mạch", population: "người lớn" },
    sources: ["dailymed", "pubmed"],
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 4, docs: 2, tokens: 18_500, elapsedMs: 104_000 },
    runStatus: "completed",
    assessment: {
      status: "supported_for_scope",
      rationale: "Nhãn thuốc và y văn cùng ủng hộ trong phạm vi người lớn; đã thử truy vấn phản bác và không tìm thấy bằng chứng đối lập.",
      coverage: { drug: "verified", adverseEvent: "verified", population: "verified", dose: "not_specified", route: "not_specified", timeWindow: "not_specified" },
    },
    reviewState: "approved",
    reviewedBy: "DS. Trần Minh",
    reviewedAt: iso(1800),
    version: 2,
    createdBy: "investigator@demo",
    createdAt: iso(2000),
  },
];

export const DEMO_EVIDENCE: Record<string, EvidenceItem[]> = {
  "INV-0007": [
    {
      id: "E1",
      label: "E1",
      docId: "DOC-0001",
      source: "pubmed",
      title: "Nghiên cứu đoàn hệ (minh họa) ở bệnh nhân suy thận mức độ trung bình",
      year: 2023,
      externalId: "DEMO-0001",
      stance: "supporting",
      scope: "partial",
      scopeDiffs: [{ field: "dose", claim: "≥2.000 mg/ngày", evidence: "1.000 mg/ngày" }],
      studyPopulation: "eGFR 30–44 mL/ph/1,73 m² (n = 1.204)",
      dose: "1.000 mg/ngày",
      designNote: "Đoàn hệ quan sát, có yếu tố thúc đẩy cấp tính ở mọi ca.",
      quotes: [{ start: 210, end: 318, text: "Có 6 ca nhiễm toan lactic được ghi nhận, tất cả đều có yếu tố thúc đẩy cấp tính" }],
      foundAtStep: 3,
    },
    {
      id: "E2",
      label: "E2",
      docId: "DOC-0002",
      source: "dailymed",
      title: "Nhãn thuốc minh họa — metformin, mục 5 (cảnh báo và thận trọng)",
      externalId: "DEMO-0002",
      stance: "supporting",
      scope: "mismatched",
      scopeDiffs: [{ field: "dose", claim: "≥2.000 mg/ngày", evidence: "không vượt quá 1.000 mg/ngày khi eGFR 30–44" }],
      studyPopulation: "bệnh nhân suy thận (theo nhãn)",
      dose: "tối đa 1.000 mg/ngày khi eGFR 30–44",
      designNote: "Nhãn thuốc minh họa, không phải nhãn thật.",
      quotes: [
        { start: 300, end: 366, text: "Không vượt quá 1.000 mg/ngày ở bệnh nhân eGFR 30–44 mL/ph/1,73 m²" },
      ],
      foundAtStep: 4,
    },
    {
      id: "E3",
      label: "E3",
      docId: "DOC-0003",
      source: "faers",
      title: "Bộ đếm báo cáo tự nguyện minh họa (FAERS DEMO)",
      externalId: "DEMO-0003",
      stance: "uncertain",
      scope: "partial",
      studyPopulation: "không xác định (báo cáo tự nguyện)",
      designNote: "Báo cáo tự nguyện: không có mẫu số, không suy ra được tỷ lệ mắc.",
      quotes: [
        {
          start: 0,
          end: 105,
          text: "Bộ đếm báo cáo minh họa: 412 báo cáo có nhắc tới metformin và nhiễm toan lactic",
        },
      ],
      foundAtStep: 5,
    },
    {
      id: "E4",
      label: "E4",
      docId: "DOC-0004",
      source: "pubmed",
      title: "Tổng quan hệ thống (minh họa): liều metformin và biến cố bất lợi",
      year: 2022,
      externalId: "DEMO-0004",
      stance: "contradicting",
      scope: "mismatched",
      scopeDiffs: [
        { field: "population", claim: "suy thận giai đoạn 3b", evidence: "chức năng thận bình thường" },
        { field: "dose", claim: "≥2.000 mg/ngày", evidence: "so sánh liều >2.000 mg/ngày với 1.000 mg/ngày" },
      ],
      studyPopulation: "bệnh nhân chức năng thận bình thường",
      designNote: "Bằng chứng phản bác một phần: tín hiệu chủ yếu ở nhóm liều cao, không ở nhóm suy thận.",
      quotes: [
        {
          start: 0,
          end: 120,
          text: "Ở nhóm dùng liều trên 2.000 mg/ngày, tỷ lệ biến cố được báo cáo cao hơn so với liều 1.000 mg/ngày",
        },
      ],
      foundAtStep: 6,
    },
  ],
};

export const DEMO_GAPS: Record<string, Gap[]> = {
  "INV-0007": [
    {
      id: "GAP-1",
      description: "Chưa có nghiên cứu ở bệnh nhân suy thận 3b dùng liều ≥2.000 mg/ngày.",
      tried: ["pubmed: metformin 2000 mg renal impairment lactic acidosis", "pubmed: metformin dose lactic acidosis"],
      relatedField: "dose",
    },
    {
      id: "GAP-2",
      description: "Cửa sổ thời gian của nhận định chưa được nêu, nên không đối chiếu được thời gian theo dõi.",
      tried: ["dailymed: metformin time to onset"],
      relatedField: "timeWindow",
    },
  ],
};

export const DEMO_AUDIT: Record<string, AuditEntry[]> = {
  "INV-0007": [
    { id: "AUD-1", at: iso(12), actor: { name: "investigator@demo", kind: "human" }, action: "Tạo cuộc điều tra", target: "INV-0007" },
    { id: "AUD-2", at: iso(11), actor: { name: "agent", kind: "ai" }, action: "Chuẩn hoá nhận định", target: "Glucophage → metformin" },
    { id: "AUD-3", at: iso(10), actor: { name: "agent", kind: "ai" }, action: "Đổi truy vấn", target: "Micardis → telmisartan", reason: "Biệt dược không cho kết quả" },
    { id: "AUD-4", at: iso(9), actor: { name: "system", kind: "system" }, action: "Cập nhật ngân sách", target: "5/8 bước" },
    { id: "AUD-5", at: iso(8), actor: { name: "agent", kind: "ai" }, action: "Ghi nhận mâu thuẫn", target: "E1 ↔ E4" },
  ],
  "INV-0001": [
    { id: "AUD-10", at: iso(420), actor: { name: "investigator@demo", kind: "human" }, action: "Tạo cuộc điều tra" },
    { id: "AUD-11", at: iso(300), actor: { name: "DS. Trần Minh", kind: "human" }, action: "Duyệt hồ sơ", reason: "Đã kiểm tra trích dẫn E1–E4", target: "v2" },
    { id: "AUD-12", at: iso(310), actor: { name: "DS. Trần Minh", kind: "human" }, action: "Sửa trích dẫn E2", reason: "Trích dẫn lệch so với nhãn", target: "E2" },
  ],
};

export const DEMO_INGESTION: IngestionJob[] = [
  {
    id: "ING-0001",
    kind: "identifier",
    source: "pubmed",
    total: 120,
    ok: 118,
    failed: 2,
    stage: "done",
    status: "partial",
    createdBy: "admin@demo",
    createdAt: iso(240),
  },
  {
    id: "ING-0002",
    kind: "csv",
    source: "faers",
    total: 500,
    ok: 500,
    failed: 0,
    stage: "indexing",
    status: "running",
    createdBy: "admin@demo",
    createdAt: iso(30),
  },
  {
    id: "ING-0003",
    kind: "file",
    source: "dailymed",
    total: 40,
    ok: 40,
    failed: 0,
    stage: "done",
    status: "completed",
    createdBy: "admin@demo",
    createdAt: iso(600),
  },
];

export const DEMO_EVAL_RUNS: EvalRun[] = [
  {
    id: "EVAL-0001",
    goldSet: "gold-set-24-ca",
    agentVersion: "agent-0.9.3",
    baseline: false,
    metrics: { accuracy: 0.83, abstainRate: 0.21, scopeMismatchRecall: 0.91, citationPrecision: 0.97 },
    confusion: [
      [8, 1, 0, 0],
      [1, 4, 1, 0],
      [0, 1, 5, 0],
      [0, 0, 1, 1],
    ],
    createdAt: iso(1440),
  },
  {
    id: "EVAL-0002",
    goldSet: "gold-set-24-ca",
    agentVersion: "baseline-rag",
    baseline: true,
    metrics: { accuracy: 0.58, abstainRate: 0.0, scopeMismatchRecall: 0.32, citationPrecision: 0.71 },
    confusion: [
      [5, 3, 1, 0],
      [2, 2, 2, 0],
      [1, 2, 3, 0],
      [0, 1, 2, 0],
    ],
    createdAt: iso(1440),
  },
];

export const DEMO_TIMELINE: Record<string, AgentStep[]> = {
  "INV-0001": [
    { index: 1, type: "search", source: "pubmed", query: "metformin lactic acidosis", rationale: "Bắt đầu bằng truy vấn rộng theo hoạt chất.", resultSummary: "4 tài liệu", docsFound: 4, newDocs: 4, tokens: 3200, durationMs: 18_000, startedAt: iso(410), status: "done" },
    { index: 2, type: "replan", source: "pubmed", prevQuery: "metformin lactic acidosis", query: "metformin renal impairment lactic acidosis dose", rationale: "Kết quả đầu chưa nêu liều; thêm từ khoá liều và suy thận.", resultSummary: "2 tài liệu mới", docsFound: 2, newDocs: 2, tokens: 2900, durationMs: 15_000, startedAt: iso(400), status: "done" },
    { index: 3, type: "read", source: "pubmed", rationale: "Đọc toàn văn để lấy đoạn trích làm bằng chứng.", resultSummary: "Trích 2 đoạn", docsFound: 2, newDocs: 0, tokens: 8600, durationMs: 42_000, startedAt: iso(395), status: "done" },
    { index: 4, type: "source_switch", source: "dailymed", query: "metformin label lactic acidosis", rationale: "Cần nguồn quy định (nhãn) để đối chiếu liều.", resultSummary: "1 nhãn thuốc", docsFound: 1, newDocs: 1, tokens: 3100, durationMs: 12_000, startedAt: iso(390), status: "done" },
    { index: 5, type: "contradiction_found", rationale: "Nhãn giới hạn liều thấp hơn nhận định ⇒ ghi nhận lệch phạm vi.", resultSummary: "1 lệch phạm vi", tokens: 1200, durationMs: 4_000, startedAt: iso(388), status: "done" },
    { index: 6, type: "conclude", rationale: "Đã tìm chiều phản bác, có nguồn thứ hai ⇒ kết luận trong phạm vi hẹp hơn.", resultSummary: "supported_for_scope", tokens: 2400, durationMs: 9_000, startedAt: iso(386), status: "done" },
  ],
  "INV-0007": [
    { index: 1, type: "search", source: "pubmed", query: "Glucophage lactic acidosis", rationale: "Bắt đầu bằng đúng tên trong nhận định.", resultSummary: "0 tài liệu", docsFound: 0, newDocs: 0, tokens: 1800, durationMs: 9_000, startedAt: iso(11), status: "done" },
    { index: 2, type: "replan", source: "pubmed", prevQuery: "Glucophage lactic acidosis", query: "metformin lactic acidosis renal impairment", rationale: "Biệt dược không có kết quả ⇒ đổi sang tên hoạt chất quốc tế.", resultSummary: "3 tài liệu", docsFound: 3, newDocs: 3, tokens: 3600, durationMs: 21_000, startedAt: iso(10), status: "done" },
    { index: 3, type: "read", source: "pubmed", rationale: "Đọc và trích đoạn nói về nhóm suy thận.", resultSummary: "Trích E1", docsFound: 1, newDocs: 1, tokens: 9200, durationMs: 46_000, startedAt: iso(9), status: "done" },
    { index: 4, type: "source_switch", source: "dailymed", query: "metformin label renal", rationale: "Cần nhãn thuốc để đối chiếu liều theo mức lọc cầu thận.", resultSummary: "1 nhãn, trích E2", docsFound: 1, newDocs: 1, tokens: 4100, durationMs: 16_000, startedAt: iso(7), status: "done" },
    { index: 5, type: "search", source: "faers", query: "metformin lactic acidosis reports", rationale: "Kiểm tra mẫu báo cáo tự nguyện (chỉ để tham chiếu, không suy ra tỷ lệ).", resultSummary: "1 bộ đếm, trích E3", docsFound: 1, newDocs: 1, tokens: 2600, durationMs: 11_000, startedAt: iso(4), status: "running" },
  ],
  "INV-0004": [
    { index: 1, type: "search", source: "pubmed", query: "thuốc C hypoglycemia children", rationale: "Truy vấn theo quần thể trẻ em.", resultSummary: "2 tài liệu", docsFound: 2, newDocs: 2, tokens: 2400, durationMs: 12_000, startedAt: iso(88), status: "done" },
    { index: 2, type: "gap_identified", rationale: "Không có nghiên cứu có nhóm đối chứng ở trẻ em.", resultSummary: "GAP: population", tokens: 900, durationMs: 3_000, startedAt: iso(80), status: "done" },
    { index: 3, type: "abstain", rationale: "Chỉ có báo cáo ca và dữ liệu tự nguyện ⇒ từ chối kết luận.", resultSummary: "insufficient_evidence", tokens: 1500, durationMs: 5_000, startedAt: iso(75), status: "done" },
  ],
};

export const DEMO_DOSSIER_MD = `# Hồ sơ điều tra INV-0001

- Nhận định: Metformin gây nhiễm toan lactic ở bệnh nhân suy thận giai đoạn 3b với liều ≥2.000 mg/ngày.
- Kết luận trong phạm vi: **Có bằng chứng ủng hộ trong phạm vi** (phạm vi hẹp hơn nhận định về liều).
- Phiên bản: v3 · Người duyệt: DS. Trần Minh · Duyệt lúc: ${iso(300)}

## Nhận định đã chuẩn hoá

| Thành phần | Giá trị | Trạng thái kiểm chứng |
|---|---|---|
| Hoạt chất | metformin | đã xác minh |
| Biến cố | nhiễm toan lactic | đã xác minh |
| Quần thể | suy thận giai đoạn 3b | khớp một phần |
| Liều | ≥2.000 mg/ngày | khớp một phần |
| Đường dùng | đường uống | đã xác minh |
| Cửa sổ thời gian | chưa nêu | chưa xác định |

## Bằng chứng đã truy xuất

- [E1] PubMed DEMO-0001 (2023) — ủng hộ, khớp một phần. Trích: "Có 6 ca nhiễm toan lactic được ghi nhận, tất cả đều có yếu tố thúc đẩy cấp tính".
- [E2] DailyMed DEMO-0002 — ủng hộ, lệch phạm vi về liều. Trích: "Không vượt quá 1.000 mg/ngày ở bệnh nhân eGFR 30–44 mL/ph/1,73 m²".
- [E3] openFDA FAERS DEMO-0003 — chưa chắc chắn. Báo cáo tự nguyện, không suy ra được tỷ lệ mắc.

## Mâu thuẫn và cách xử lý

E1 (nhóm suy thận 3b, 1.000 mg/ngày) và E4 (nhóm chức năng thận bình thường, >2.000 mg/ngày) khác nhau về quần thể và liều.
Hồ sơ ghi nhận khác biệt thay vì gộp thành một kết luận chung.

## Khoảng trống

- Chưa có nghiên cứu ở bệnh nhân suy thận 3b dùng liều ≥2.000 mg/ngày.
- Cửa sổ thời gian chưa được nêu trong nhận định.

## Giới hạn

Đây là dữ liệu minh họa. Kết quả không thay thế phán đoán chuyên môn và không phải khuyến cáo điều trị.
`;

