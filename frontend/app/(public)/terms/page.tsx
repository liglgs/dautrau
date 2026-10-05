import { PageHeader, Prose, Section } from "@/components/public/sections";

export const metadata = { title: "Điều khoản sử dụng" };

export default function TermsPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/terms", label: "Điều khoản" }]}
        title="Điều khoản sử dụng"
        description="Điều kiện sử dụng bản MVP và giới hạn trách nhiệm."
      />
      <Section>
        <Prose>
          <h2 className="font-display text-[22px] text-foreground">Không dùng thay thế đánh giá chuyên môn</h2>
          <p>
            Kết quả của hệ thống là tài liệu tham khảo cho người có chuyên môn. Không dùng kết quả này làm căn cứ duy nhất
            cho bất kỳ quyết định điều trị nào.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Không dùng dữ liệu minh họa cho quyết định</h2>
          <p>
            Dữ liệu trong bản demo là dữ liệu mẫu, có thể không phản ánh thực tế. Mọi mã tài liệu trong bản demo đều là mã
            minh họa, không phải mã thật của PubMed, DailyMed hay openFDA.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Trách nhiệm của người dùng</h2>
          <p>
            Không nhập thông tin định danh bệnh nhân. Không dùng hệ thống để đưa ra khuyến cáo điều trị cho cá nhân. Kiểm
            tra lại trích dẫn nguyên văn trước khi dùng bất kỳ kết luận nào.
          </p>
          <h2 className="font-display text-[22px] text-foreground">Thay đổi</h2>
          <p>
            Điều khoản này thuộc bản MVP và sẽ được cập nhật khi hệ thống bổ sung xác thực người dùng và kênh liên hệ chính
            thức.
          </p>
        </Prose>
      </Section>
    </>
  );
}
