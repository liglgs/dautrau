import Link from "next/link";
import { BRAND } from "@/lib/brand";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden flex-col justify-between border-r border-border bg-card px-10 py-12 lg:flex">
        <Link href="/" className="font-display text-[20px] text-foreground">
          {BRAND.name}
        </Link>
        <div className="max-w-[46ch]">
          <h2 className="font-display text-[30px] leading-tight text-foreground">
            Một quy trình, một câu hỏi: bằng chứng này đúng với ai, ở liều nào, trong nguồn nào?
          </h2>
          <ul className="mt-6 space-y-3 text-[14px] leading-relaxed text-muted-foreground">
            <li>Mỗi câu kết luận đều dẫn về nguyên văn đoạn bằng chứng.</li>
            <li>Agent chủ động tìm chiều phản bác trước khi kết luận.</li>
            <li>Thiếu bằng chứng là kết quả hợp lệ, không phải lỗi.</li>
            <li>Dược sĩ lâm sàng là người duyệt cuối cùng.</li>
          </ul>
        </div>
        <p className="text-[12px] text-muted-foreground">{BRAND.demoNotice}</p>
      </div>
      <div className="flex items-center justify-center px-5 py-12">{children}</div>
    </div>
  );
}
