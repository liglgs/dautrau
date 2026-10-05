import { PageHeader, Prose, Section } from "@/components/public/sections";
import { BRAND } from "@/lib/brand";

export const metadata = { title: "Về dự án" };

export default function AboutPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/about", label: "Về dự án" }]}
        title="Về dự án"
        description={BRAND.description}
      />
      <Section>
        <Prose>
          <h2 className="font-display text-[22px] text-foreground">Bài toán</h2>
          <p>
            Khi một nhận định về an toàn thuốc xuất hiện, người đọc thường chỉ nhận được một câu tóm tắt không kèm phạm vi.
            Câu tóm tắt đó dễ bị dùng sai: nghiên cứu ở người có chức năng thận bình thường bị áp cho bệnh nhân suy thận,
            hoặc một báo cáo tự nguyện bị đọc như bằng chứng về tỷ lệ mắc.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Cách tiếp cận</h2>
          <p>
            Hệ thống điều tra nhận định thành các thành phần kiểm chứng được, tìm bằng chứng theo ngân sách, chủ động tìm
            chiều phản bác, và từ chối kết luận khi chưa đủ căn cứ. Mọi câu kết luận đều gắn với trích dẫn nguyên văn và
            phạm vi cụ thể.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Đối tượng sử dụng</h2>
          <p>
            Dược sĩ lâm sàng, điều tra viên an toàn thuốc và đơn vị quản lý chất lượng. Người duyệt cuối cùng luôn là người
            có chuyên môn, không phải hệ thống.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Trạng thái</h2>
          <p>
            Đây là bản MVP. Phần lõi đã chạy đầu-cuối: nhận nhận định, chuẩn hoá, truy xuất theo ngân sách, đánh giá theo
            phạm vi, dừng ở checkpoint, và xuất hồ sơ chỉ khi đã duyệt.
          </p>
          <p className="text-[14px] text-muted-foreground">{BRAND.demoNotice}</p>
        </Prose>
      </Section>
    </>
  );
}
