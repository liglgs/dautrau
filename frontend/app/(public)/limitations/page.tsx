import { PageHeader, Prose, Section } from "@/components/public/sections";

export const metadata = { title: "Giới hạn & minh bạch" };

export default function LimitationsPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/limitations", label: "Giới hạn" }]}
        title="Giới hạn & cam kết minh bạch"
        description="Đây là danh sách những điều hệ thống không làm, và những điều người đọc phải tự đánh giá."
      />
      <Section>
        <Prose>
          <h2 className="font-display text-[22px] text-foreground">Hệ thống không kết luận nhân quả</h2>
          <p>
            Việc một bài báo mô tả biến cố ở người dùng thuốc không chứng minh thuốc gây ra biến cố. Hệ thống trình bày
            bằng chứng theo phạm vi và để người đọc tự đánh giá.
          </p>

          <h2 className="font-display text-[22px] text-foreground">Hệ thống không tính tỷ lệ mắc</h2>
          <p>
            Báo cáo tự nguyện không có mẫu số. Vì vậy hệ thống không bao giờ đưa ra con số tỷ lệ, nguy cơ tương đối hay
            số ca trên mỗi nghìn người dùng.
          </p>

          <h2 className="font-display text-[22px] text-foreground">Màu sắc chỉ nói về nhận định</h2>
          <p>
            Màu xanh nghĩa là nhận định đang được điều tra có bằng chứng ủng hộ trong phạm vi nêu ra. Màu đỏ nghĩa là
            nhận định bị bằng chứng phản bác. Không màu nào nói thuốc an toàn hay nguy hiểm.
          </p>

          <h2 className="font-display text-[22px] text-foreground">Thiếu bằng chứng là một kết quả</h2>
          <p>
            “Thiếu bằng chứng — Agent từ chối kết luận” không phải lỗi hệ thống. Đó là cách hệ thống nói rằng nó đã tìm ở
            đâu, đã thử cách nào và còn thiếu thành phần nào.
          </p>

          <h2 className="font-display text-[22px] text-foreground">Người duyệt chịu trách nhiệm cuối cùng</h2>
          <p>
            Mọi hồ sơ đều phải được dược sĩ lâm sàng duyệt trước khi xuất. Hệ thống không có cơ chế tự động duyệt và không
            đưa khuyến cáo điều trị.
          </p>

          <h2 className="font-display text-[22px] text-foreground">Giới hạn của bản MVP</h2>
          <p>
            Bản MVP dùng hai token vai trò dùng chung, chưa có tài khoản riêng, chưa có hủy cuộc điều tra, và một số phản
            hồi API chưa khai báo schema đầy đủ. Dữ liệu minh họa trong bản demo không dùng cho quyết định lâm sàng.
          </p>
        </Prose>
      </Section>
    </>
  );
}
