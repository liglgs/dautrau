import { PageHeader, Section } from "@/components/public/sections";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui";

export const metadata = { title: "Liên hệ" };

export default function ContactPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/contact", label: "Liên hệ" }]}
        title="Liên hệ"
        description="Bản MVP chưa có kênh liên hệ tự động. Dưới đây là các đầu mối theo loại yêu cầu."
      />
      <Section>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { title: "Câu hỏi chuyên môn", body: "Trao đổi về cách đọc kết quả, phạm vi bằng chứng và quy trình duyệt hồ sơ." },
            { title: "Báo lỗi dữ liệu", body: "Báo tài liệu sai nguồn, trích dẫn lệch hoặc hash không khớp." },
            { title: "An toàn thông tin", body: "Báo lo ngại về dữ liệu, quyền truy cập hoặc token." },
          ].map((item) => (
            <Card key={item.title}>
              <CardHeader>
                <CardTitle>{item.title}</CardTitle>
              </CardHeader>
              <CardBody className="space-y-2 text-[13px] text-muted-foreground">
                <p>{item.body}</p>
                <p className="mono">lien-he@demo.vigilens</p>
              </CardBody>
            </Card>
          ))}
        </div>
        <p className="mt-4 text-[13px] text-muted-foreground">
          Địa chỉ email trong bản minh họa không hoạt động. Khi triển khai thật, thay bằng đầu mối chính thức của đơn vị.
        </p>
      </Section>
    </>
  );
}
