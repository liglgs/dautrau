import { NumberedSteps, PageHeader, Prose, Section } from "@/components/public/sections";

export const metadata = { title: "Cách hệ thống hoạt động" };

export default function HowItWorksPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/how-it-works", label: "Cách hoạt động" }]}
        title="Cách hệ thống hoạt động"
        description="Sáu bước lặp lại cho tới khi bằng chứng bão hoà hoặc hết ngân sách. Mỗi bước đều để lại dấu vết đọc được."
      />
      <Section>
        <NumberedSteps
          steps={[
            {
              title: "Phân rã nhận định thành các thành phần kiểm chứng được",
              body: "Hoạt chất, biến cố bất lợi, quần thể, liều, đường dùng và cửa sổ thời gian. Thành phần nào nhận định không nêu thì hệ thống ghi rõ “Chưa giới hạn” thay vì tự suy diễn.",
            },
            {
              title: "Lập kế hoạch truy xuất theo ngân sách",
              body: "Agent chọn nguồn, thứ tự truy vấn và số bước tối đa. Ngân sách bước, tài liệu, lượt gọi model và token đều bị chặn cứng ở phía máy chủ.",
            },
            {
              title: "Đổi chiến lược khi bế tắc",
              body: "Không có kết quả với biệt dược thì chuyển sang tên hoạt chất quốc tế. Thiếu dữ liệu về liều thì đổi từ y văn sang nhãn thuốc. Mỗi lần đổi đều ghi lý do.",
            },
            {
              title: "Chủ động tìm bằng chứng phản bác",
              body: "Trước khi kết luận “có bằng chứng ủng hộ”, agent luôn chạy một truy vấn đối lập và yêu cầu ít nhất hai nguồn độc lập.",
            },
            {
              title: "Từ chối kết luận khi chưa đủ căn cứ",
              body: "Khi phạm vi còn thiếu hoặc dữ liệu chỉ có một nguồn tự nguyện, agent dừng ở trạng thái “Thiếu bằng chứng” kèm danh sách khoảng trống đã thử.",
            },
            {
              title: "Chuyển cho người duyệt",
              body: "Agent dừng ở checkpoint. Dược sĩ lâm sàng xem bằng chứng, đối chiếu nguyên văn trong trình xem nguồn, rồi duyệt, sửa, yêu cầu tìm thêm hoặc từ chối.",
            },
          ]}
        />
      </Section>
      <Section title="Điều gì bị chặn tự động">
        <Prose>
          <p>
            Hệ thống chặn ở tầng ngôn ngữ: không hiển thị câu khẳng định quan hệ nhân quả giữa thuốc và biến cố, không hiển
            thị kết luận về mức độ an toàn, và không tính tỷ lệ mắc từ báo cáo tự nguyện.
          </p>
          <p>
            Hệ thống cũng chặn ở tầng hồ sơ: hồ sơ chỉ xuất được khi đã duyệt và mọi trích dẫn còn khớp nguyên văn tài liệu
            nguồn. Nếu bằng chứng thay đổi sau khi duyệt, hồ sơ bị đánh dấu cần duyệt lại.
          </p>
        </Prose>
      </Section>
    </>
  );
}
