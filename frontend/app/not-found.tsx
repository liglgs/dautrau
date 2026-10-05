import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[720px] flex-col justify-center px-5">
      <p className="mono text-[12px] uppercase tracking-wide text-muted-foreground">404</p>
      <h1 className="mt-2 font-display text-[30px] text-foreground">Không tìm thấy trang này</h1>
      <p className="mt-2 max-w-[60ch] text-[15px] leading-relaxed text-muted-foreground">
        Đường dẫn có thể sai, hoặc trang thuộc phần chưa được dựng trong bản MVP này. Bạn có thể quay về trang chủ hoặc vào
        khu vực làm việc.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        <Link href="/" className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-primary px-4 text-[14px] font-medium text-primary-foreground">
          Về trang chủ
        </Link>
        <Link href="/app" className="inline-flex h-10 items-center rounded-[var(--radius-control)] border border-input px-4 text-[14px]">
          Vào khu vực làm việc
        </Link>
        <Link href="/docs" className="inline-flex h-10 items-center rounded-[var(--radius-control)] border border-input px-4 text-[14px]">
          Đọc tài liệu
        </Link>
      </div>
    </main>
  );
}
