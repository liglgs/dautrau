import { PageHeader, Section } from "@/components/public/sections";
import { SourceChip } from "@/components/pv/badges";

export const metadata = { title: "Nguồn dữ liệu" };

const SOURCES = [
  {
    id: "pubmed" as const,
    name: "PubMed",
    use: "Tìm nghiên cứu, tổng quan hệ thống và báo cáo ca theo hoạt chất và biến cố.",
    gives: ["Bối cảnh phương pháp của từng nghiên cứu", "Quần thể và liều trong từng nghiên cứu", "Trích dẫn nguyên văn để đối chiếu"],
    limits: ["Chất lượng thiết kế rất khác nhau", "Báo cáo ca không cho biết tỷ lệ mắc", "Không phải mọi biến cố hiếm đều được công bố"],
  },
  {
    id: "dailymed" as const,
    name: "DailyMed",
    use: "Đọc nhãn thuốc do cơ quan quản lý công bố: cảnh báo, liều, chống chỉ định, thận trọng.",
    gives: ["Ngưỡng liều theo chức năng thận hoặc gan", "Cảnh báo đã được cơ quan quản lý thông qua", "Đối chiếu khi y văn không nêu liều"],
    limits: ["Là văn bản quy định, không phải bằng chứng dịch tễ", "Nội dung theo phiên bản nhãn tại thời điểm lấy", "Không thay thế đánh giá lâm sàng"],
  },
  {
    id: "faers" as const,
    name: "openFDA FAERS",
    use: "Đếm báo cáo tự nguyện theo hoạt chất và biến cố để phát hiện tín hiệu.",
    gives: ["Tín hiệu cần kiểm chứng thêm", "Số lượng báo cáo theo thời gian", "Chất lượng báo cáo để đánh giá độ tin cậy"],
    limits: ["Không có mẫu số nên không suy ra được tỷ lệ", "Báo cáo trùng lặp và thiếu xác nhận", "Không xác lập quan hệ nhân quả"],
  },
];

export default function DataSourcesPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/data-sources", label: "Nguồn dữ liệu" }]}
        title="Ba nguồn dữ liệu, ba giới hạn khác nhau"
        description="Hệ thống nói rõ nguồn nào cho biết điều gì và nguồn nào không thể cho biết điều gì."
      />
      {SOURCES.map((source) => (
        <Section key={source.id} title={source.name}>
          <div className="mb-4 flex items-center gap-2">
            <SourceChip source={source.id} />
            <p className="text-[14px] text-muted-foreground">{source.use}</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <h3 className="text-[14px] font-semibold text-support-fg">Cho biết</h3>
              <ul className="mt-2 space-y-1.5 text-[14px] leading-relaxed text-muted-foreground">
                {source.gives.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <h3 className="text-[14px] font-semibold text-caution-fg">Không cho biết</h3>
              <ul className="mt-2 space-y-1.5 text-[14px] leading-relaxed text-muted-foreground">
                {source.limits.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </Section>
      ))}
      <Section title="Quy tắc phối hợp giữa các nguồn">
        <ul className="max-w-[72ch] space-y-2 text-[15px] leading-relaxed text-muted-foreground">
          <li>Chỉ có FAERS thì hệ thống không bao giờ kết luận “có bằng chứng ủng hộ”.</li>
          <li>Kết luận “có bằng chứng ủng hộ” cần ít nhất hai nguồn độc lập.</li>
          <li>Khi hai nguồn khác nhau, hệ thống ghi nhận mâu thuẫn theo từng trường thay vì gộp thành một câu.</li>
        </ul>
      </Section>
    </>
  );
}
