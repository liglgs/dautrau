import { PageHeader, Prose, Section } from "@/components/public/sections";

export const metadata = { title: "Quyền riêng tư" };

export default function PrivacyPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/privacy", label: "Quyền riêng tư" }]}
        title="Quyền riêng tư"
        description="Bản MVP không thu thập thông tin định danh bệnh nhân và không gửi dữ liệu ra ngoài hệ thống."
      />
      <Section>
        <Prose>
          <h2 className="font-display text-[22px] text-foreground">Dữ liệu hệ thống nhận</h2>
          <p>
            Chỉ nhận định ở mức quần thể: hoạt chất, biến cố, quần thể, liều, đường dùng, cửa sổ thời gian. Không có trường
            nào dành cho tên, mã bệnh án hay ngày sinh bệnh nhân.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Dữ liệu hệ thống lưu</h2>
          <p>
            Nội dung nhận định, tài liệu đã đọc, trích dẫn, quyết định duyệt và nhật ký kiểm toán. Nhật ký chỉ ghi thêm để
            truy vết.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Chia sẻ ra bên ngoài</h2>
          <p>
            Hệ thống gọi ba nguồn công khai (PubMed, DailyMed, openFDA) bằng truy vấn chứa hoạt chất và biến cố. Truy vấn
            không chứa thông tin định danh bệnh nhân.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Bản minh họa</h2>
          <p>
            Bản demo chạy hoàn toàn trên dữ liệu mẫu trong trình duyệt. Không có dữ liệu nào được gửi tới máy chủ khi bạn
            đang ở chế độ minh họa.
          </p>
        </Prose>
      </Section>
    </>
  );
}
