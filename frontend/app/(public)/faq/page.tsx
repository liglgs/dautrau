import { PageHeader, Section } from "@/components/public/sections";

export const metadata = { title: "Câu hỏi thường gặp" };

const FAQ = [
  { q: "VigiLens có kết luận thuốc có gây ra biến cố không?", a: "Không. Hệ thống chỉ trình bày bằng chứng theo phạm vi và ghi rõ khi chưa đủ căn cứ. Quan hệ nhân quả phải do người có chuyên môn đánh giá." },
  { q: "Vì sao “thiếu bằng chứng” lại là kết quả tốt?", a: "Vì nó cho biết hệ thống đã tìm ở đâu, đã thử cách nào và còn thiếu gì. Một câu trả lời như vậy hữu ích hơn một kết luận không có căn cứ." },
  { q: "Số liệu từ FAERS dùng để làm gì?", a: "Chỉ để phát hiện tín hiệu cần kiểm chứng thêm. Báo cáo tự nguyện không có mẫu số nên hệ thống không tính tỷ lệ mắc từ nguồn này." },
  { q: "Ai duyệt hồ sơ cuối cùng?", a: "Dược sĩ lâm sàng. Hệ thống dừng ở checkpoint và không có cơ chế tự động duyệt." },
  { q: "Màu xanh có nghĩa thuốc an toàn không?", a: "Không. Màu chỉ nói về nhận định đang được điều tra: xanh là được bằng chứng ủng hộ trong phạm vi nêu ra, đỏ là bị phản bác." },
  { q: "Tôi có thể dùng dữ liệu trong bản demo cho quyết định lâm sàng không?", a: "Không. Toàn bộ dữ liệu trong bản minh họa là dữ liệu mẫu, không dùng cho quyết định lâm sàng." },
  { q: "Hệ thống có lưu thông tin bệnh nhân không?", a: "Không. Hệ thống chỉ nhận nhận định ở mức quần thể và không có trường nào cho thông tin định danh bệnh nhân." },
  { q: "Có thể xóa hoặc sửa một bước agent đã chạy không?", a: "Không. Dòng suy luận và nhật ký kiểm toán chỉ ghi thêm, để người đọc sau truy vết được." },
];

export default function FaqPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/faq", label: "Câu hỏi thường gặp" }]}
        title="Câu hỏi thường gặp"
        description="Trả lời thẳng, kể cả khi câu trả lời là “hệ thống không làm việc đó”."
      />
      <Section>
        <div className="max-w-[80ch] divide-y divide-border">
          {FAQ.map((item) => (
            <details key={item.q} className="group py-4">
              <summary className="cursor-pointer list-none text-[16px] font-medium text-foreground">
                {item.q}
              </summary>
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">{item.a}</p>
            </details>
          ))}
        </div>
      </Section>
    </>
  );
}
