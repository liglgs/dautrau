import Link from "next/link";
import { CircleHelp, GitBranch, Layers, Scale, ShieldCheck, Sparkles } from "lucide-react";
import { HeroDemo } from "@/components/public/hero-demo";
import { FeatureGrid, Section } from "@/components/public/sections";
import { AssessmentBadge } from "@/components/pv/badges";

const LOOP = [
  {
    title: "Phân rã nhận định",
    body: "Nhận định được tách thành hoạt chất, biến cố, quần thể, liều, đường dùng và cửa sổ thời gian. Phần chưa nêu được đánh dấu là “Chưa giới hạn”.",
  },
  {
    title: "Lập kế hoạch và tìm theo ngân sách",
    body: "Agent chọn nguồn và truy vấn theo thứ tự ưu tiên, mỗi bước đều ghi lý do. Ngân sách bước/tài liệu/token hiển thị trực tiếp.",
  },
  {
    title: "Đổi chiến lược khi bế tắc",
    body: "Không có kết quả với biệt dược thì chuyển sang tên hoạt chất quốc tế; thiếu dữ liệu về liều thì đổi nguồn sang nhãn thuốc.",
  },
  {
    title: "Chủ động tìm bằng chứng phản bác",
    body: "Trước khi kết luận, agent luôn chạy một truy vấn đối lập. Kết luận “ủng hộ” chỉ hợp lệ khi đã thử chiều ngược và có nguồn thứ hai.",
  },
  {
    title: "Từ chối kết luận khi chưa đủ căn cứ",
    body: "Thiếu bằng chứng là một trạng thái hạng nhất, được trình bày trang trọng kèm danh sách khoảng trống đã thử.",
  },
  {
    title: "Reviewer quyết định cuối",
    body: "Agent dừng ở checkpoint. Dược sĩ lâm sàng duyệt, từ chối, sửa bằng chứng hoặc yêu cầu tìm thêm; mọi thao tác vào audit trail.",
  },
];

const STATUSES = [
  "supported_for_scope",
  "contradicted_for_scope",
  "insufficient_evidence",
  "scope_mismatch",
  "out_of_scope",
  "requires_human_review",
] as const;

export default function HomePage() {
  return (
    <>
      <section className="border-b border-border bg-card">
        <div className="mx-auto w-full max-w-[1200px] px-5 py-14 sm:py-20">
          <HeroDemo />
        </div>
      </section>

      <Section
        title="Vòng lặp điều tra thích ứng"
        description="Sáu bước lặp lại cho tới khi bằng chứng bão hoà hoặc hết ngân sách. Mỗi bước đều để lại dấu vết đọc được."
      >
        <FeatureGrid
          items={LOOP.map((item, index) => ({
            icon: index === 3 ? <Scale className="h-4 w-4" aria-hidden /> : index === 2 ? <GitBranch className="h-4 w-4" aria-hidden /> : <Layers className="h-4 w-4" aria-hidden />,
            title: item.title,
            body: item.body,
          }))}
        />
      </Section>

      <Section
        title="Sáu trạng thái kết luận, không có trạng thái “chắc chắn”"
        description="Màu sắc chỉ nói về nhận định đang được điều tra: xanh là được bằng chứng ủng hộ, đỏ là bị phản bác. Màu không nói thuốc an toàn hay nguy hiểm."
      >
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((status) => (
            <AssessmentBadge key={status} status={status} size="md" />
          ))}
        </div>
      </Section>

      <Section title="Ba nguồn dữ liệu, ba giới hạn khác nhau">
        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              name: "PubMed",
              gives: "Nghiên cứu, tổng quan, báo cáo ca có bối cảnh phương pháp.",
              limits: "Chất lượng thiết kế rất khác nhau; báo cáo ca không cho biết tỷ lệ.",
            },
            {
              name: "DailyMed",
              gives: "Nhãn thuốc do cơ quan quản lý công bố: cảnh báo, liều, chống chỉ định.",
              limits: "Là văn bản quy định, không phải bằng chứng dịch tễ.",
            },
            {
              name: "openFDA FAERS",
              gives: "Mẫu báo cáo tự nguyện, hữu ích để phát hiện tín hiệu.",
              limits: "Không có mẫu số, không suy ra được tỷ lệ mắc, không xác lập nhân quả.",
            },
          ].map((source) => (
            <div key={source.name} className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <h3 className="text-[15px] font-semibold text-foreground">{source.name}</h3>
              <p className="mt-2 text-[14px] leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">Cho biết: </span>
                {source.gives}
              </p>
              <p className="mt-2 text-[14px] leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">Không cho biết: </span>
                {source.limits}
              </p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-[14px] text-muted-foreground">
          <Link href="/data-sources" className="underline">
            Xem chi tiết cách hệ thống dùng từng nguồn
          </Link>
          .
        </p>
      </Section>

      <Section title="Giới hạn của hệ thống, nói thẳng">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
            <h3 className="flex items-center gap-2 text-[15px] font-semibold text-foreground">
              <ShieldCheck className="h-4 w-4 text-support" aria-hidden /> Hệ thống làm được
            </h3>
            <ul className="mt-2 space-y-1.5 text-[14px] leading-relaxed text-muted-foreground">
              <li>Tìm, đối chiếu và trích dẫn nguyên văn đoạn bằng chứng.</li>
              <li>Phát hiện lệch phạm vi giữa nhận định và bằng chứng.</li>
              <li>Ghi nhận mâu thuẫn giữa các nguồn để người đọc phân xử.</li>
            </ul>
          </div>
          <div className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
            <h3 className="flex items-center gap-2 text-[15px] font-semibold text-foreground">
              <CircleHelp className="h-4 w-4 text-caution" aria-hidden /> Hệ thống không làm được
            </h3>
            <ul className="mt-2 space-y-1.5 text-[14px] leading-relaxed text-muted-foreground">
              <li>Không kết luận quan hệ nhân quả giữa thuốc và biến cố.</li>
              <li>Không tính tỷ lệ mắc từ báo cáo tự nguyện.</li>
              <li>Không tự duyệt hồ sơ và không đưa khuyến cáo điều trị.</li>
            </ul>
          </div>
        </div>
        <p className="mt-4 text-[14px] text-muted-foreground">
          <Link href="/limitations" className="underline">
            Đọc cam kết minh bạch đầy đủ
          </Link>
          .
        </p>
      </Section>

      <section className="border-t border-border bg-card">
        <div className="mx-auto flex w-full max-w-[1200px] flex-wrap items-center justify-between gap-4 px-5 py-10">
          <div>
            <h2 className="font-display text-[22px] text-foreground">Bắt đầu bằng một nhận định bạn đang phải kiểm chứng</h2>
            <p className="mt-1 text-[14px] text-muted-foreground">
              Nhập nhận định, chọn nguồn và ngân sách. Hệ thống sẽ cho biết nó tìm ở đâu, tìm thấy gì và còn thiếu gì.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href="/app/investigations/new"
              className="inline-flex h-10 items-center gap-2 rounded-[var(--radius-control)] bg-primary px-4 text-[14px] font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Sparkles className="h-4 w-4" aria-hidden /> Tạo cuộc điều tra
            </Link>
            <Link
              href="/examples"
              className="inline-flex h-10 items-center rounded-[var(--radius-control)] border border-input px-4 text-[14px] font-medium text-foreground hover:bg-muted"
            >
              Xem ca mẫu
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
