import { PageHeader, Section } from "@/components/public/sections";

export const metadata = { title: "Thuật ngữ" };

const TERMS = [
  { term: "Nhận định", body: "Câu nói về quan hệ giữa một thuốc và một biến cố ở một nhóm người dùng. Đây là thứ hệ thống kiểm chứng, không phải kết luận cuối cùng." },
  { term: "Phạm vi", body: "Tập hợp quần thể, liều, đường dùng và cửa sổ thời gian mà một bằng chứng thực sự nói tới." },
  { term: "Lệch phạm vi", body: "Trường hợp bằng chứng tìm được nằm ngoài phạm vi nhận định, ví dụ nghiên cứu ở người có chức năng thận bình thường trong khi nhận định nói về suy thận." },
  { term: "Trạng thái kết luận", body: "Một trong sáu nhãn: có bằng chứng ủng hộ, có bằng chứng phản bác, thiếu bằng chứng, lệch phạm vi, ngoài phạm vi hệ thống, bắt buộc chuyên viên can thiệp." },
  { term: "Từ chối kết luận", body: "Khi hệ thống chủ động dừng ở trạng thái thiếu bằng chứng thay vì đưa ra kết luận không có căn cứ." },
  { term: "Truy vấn phản bác", body: "Truy vấn đối lập mà hệ thống luôn chạy trước khi kết luận có bằng chứng ủng hộ." },
  { term: "Ngân sách", body: "Giới hạn số bước, số tài liệu, số lượt gọi model và số token cho một cuộc điều tra." },
  { term: "Checkpoint", body: "Điểm dừng bắt buộc để người duyệt xem bằng chứng trước khi hệ thống đi tiếp." },
  { term: "Hồ sơ", body: "Bản Markdown tổng hợp bằng chứng, phạm vi và khoảng trống còn lại. Chỉ xuất được khi đã duyệt và mọi trích dẫn còn khớp nguồn." },
  { term: "Trích dẫn nguyên văn", body: "Đoạn văn bản lấy đúng nguyên văn từ tài liệu nguồn, kèm vị trí bắt đầu và kết thúc để đối chiếu lại." },
  { term: "Khoảng trống dữ liệu", body: "Thành phần chưa có bằng chứng, kèm danh sách cách đã thử tìm." },
  { term: "FAERS", body: "Cơ sở dữ liệu báo cáo biến cố bất lợi tự nguyện của FDA. Không có mẫu số nên không suy ra được tỷ lệ." },
];

export default function GlossaryPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/glossary", label: "Thuật ngữ" }]}
        title="Thuật ngữ dùng trong sản phẩm"
        description="Một thuật ngữ, một nghĩa, dùng thống nhất trên toàn bộ giao diện."
      />
      <Section>
        <dl className="grid gap-4 md:grid-cols-2">
          {TERMS.map((item) => (
            <div key={item.term} className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <dt className="text-[15px] font-semibold text-foreground">{item.term}</dt>
              <dd className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{item.body}</dd>
            </div>
          ))}
        </dl>
      </Section>
    </>
  );
}
