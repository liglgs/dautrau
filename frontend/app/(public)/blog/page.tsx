import Link from "next/link";
import { PageHeader, Section } from "@/components/public/sections";

export const metadata = { title: "Bài viết" };

const POSTS = [
  {
    slug: "vi-sao-agent-phai-biet-tu-choi",
    title: "Vì sao agent phải biết từ chối kết luận",
    excerpt: "Một hệ thống luôn trả lời sẽ luôn trả lời sai ở đâu đó. Từ chối kết luận là cách giữ cho phần đã trả lời còn đáng tin.",
    minutes: 6,
  },
  {
    slug: "lech-pham-vi-la-loi-pho-bien-nhat",
    title: "Lệch phạm vi là lỗi phổ biến nhất khi đọc bằng chứng",
    excerpt: "Bằng chứng đúng nhưng không đúng cho nhóm bạn đang hỏi. Cách hệ thống tách phạm vi thành từng trường để so.",
    minutes: 7,
  },
  {
    slug: "bao-cao-tu-nguyen-khong-co-mau-so",
    title: "Báo cáo tự nguyện không có mẫu số",
    excerpt: "Vì sao không thể suy ra tỷ lệ mắc từ FAERS, và dùng nguồn này đúng cách thì được gì.",
    minutes: 5,
  },
];

export default function BlogPage() {
  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/blog", label: "Bài viết" }]}
        title="Bài viết"
        description="Ghi chú về phương pháp điều tra bằng chứng và những cái bẫy khi đọc kết quả."
      />
      <Section>
        <ul className="space-y-3">
          {POSTS.map((post) => (
            <li key={post.slug} className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <Link href={`/blog/${post.slug}`} className="font-display text-[19px] text-foreground hover:underline">
                {post.title}
              </Link>
              <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{post.excerpt}</p>
              <p className="mt-2 text-[12px] text-muted-foreground">{post.minutes} phút đọc</p>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
