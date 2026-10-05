import { notFound } from "next/navigation";
import { PageHeader, Prose, Section } from "@/components/public/sections";

const POSTS: Record<string, { title: string; minutes: number; body: string[] }> = {
  "vi-sao-agent-phai-biet-tu-choi": {
    title: "Vì sao agent phải biết từ chối kết luận",
    minutes: 6,
    body: [
      "Một hệ thống luôn trả lời sẽ luôn trả lời sai ở đâu đó. Khi dữ liệu không đủ, câu trả lời tự tin là câu trả lời nguy hiểm nhất.",
      "VigiLens đặt “thiếu bằng chứng” ngang hàng với các kết luận khác. Trạng thái này kèm theo danh sách khoảng trống: đã tìm nguồn nào, đã thử truy vấn nào, còn thiếu thành phần nào.",
      "Nhờ vậy người đọc biết chính xác mình đang đứng ở đâu. Nếu muốn đi tiếp, họ có thể yêu cầu tìm thêm ở nguồn khác hoặc mở rộng ngân sách, thay vì nhận một câu kết luận không có căn cứ.",
    ],
  },
  "lech-pham-vi-la-loi-pho-bien-nhat": {
    title: "Lệch phạm vi là lỗi phổ biến nhất khi đọc bằng chứng",
    minutes: 7,
    body: [
      "Một nghiên cứu có thể đúng hoàn toàn nhưng không đúng cho nhóm bạn đang hỏi. Đây là lỗi phổ biến nhất khi đọc bằng chứng nhanh.",
      "Hệ thống tách phạm vi thành bốn trường: quần thể, liều, đường dùng và cửa sổ thời gian. Mỗi bằng chứng được so với nhận định theo từng trường và ghi rõ trường nào lệch.",
      "Khi phát hiện lệch, hệ thống không gộp thành một câu kết luận. Nó đưa ra trạng thái “lệch phạm vi” kèm bảng khác biệt để người đọc quyết định.",
    ],
  },
  "bao-cao-tu-nguyen-khong-co-mau-so": {
    title: "Báo cáo tự nguyện không có mẫu số",
    minutes: 5,
    body: [
      "Báo cáo tự nguyện hữu ích để phát hiện tín hiệu: một biến cố hiếm có thể xuất hiện ở đây trước khi có nghiên cứu.",
      "Nhưng báo cáo tự nguyện không có mẫu số. Không biết có bao nhiêu người đã dùng thuốc, nên không thể tính tỷ lệ. Báo cáo cũng trùng lặp và thường thiếu xác nhận.",
      "Vì vậy hệ thống chỉ dùng FAERS để phát hiện tín hiệu và không bao giờ kết luận “có bằng chứng ủng hộ” khi chỉ có nguồn này.",
    ],
  },
};

export function generateStaticParams() {
  return Object.keys(POSTS).map((slug) => ({ slug }));
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = POSTS[slug];
  if (!post) notFound();

  return (
    <>
      <PageHeader
        breadcrumb={[
          { href: "/", label: "Trang chủ" },
          { href: "/blog", label: "Bài viết" },
          { href: `/blog/${slug}`, label: post.title },
        ]}
        title={post.title}
        description={`${post.minutes} phút đọc`}
      />
      <Section>
        <Prose>
          {post.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </Prose>
      </Section>
    </>
  );
}
