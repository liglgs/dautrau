"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, LayoutDashboard, Menu, Moon, Sun, X } from "lucide-react";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui";
import { useAppStore } from "@/lib/store/app-store";
import { useTheme } from "next-themes";

const NAV = [
  { href: "/", label: "Trang chủ" },
  { href: "/how-it-works", label: "Cách hoạt động" },
  { href: "/data-sources", label: "Nguồn dữ liệu" },
  { href: "/examples", label: "Ca điều tra mẫu" },
  { href: "/blog", label: "Blog" },
];

const DOCS_MENU = [
  { href: "/docs", label: "Hướng dẫn sử dụng" },
  { href: "/glossary", label: "Thuật ngữ" },
  { href: "/limitations", label: "Giới hạn & an toàn AI" },
  { href: "/faq", label: "Câu hỏi thường gặp" },
  { href: "/about", label: "Về dự án" },
];

export function PublicNav() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [docsOpen, setDocsOpen] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [scrolled, setScrolled] = React.useState(false);
  const role = useAppStore((state) => state.role);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-30 w-full border-b bg-background/80 backdrop-blur-sm transition-colors",
        scrolled ? "border-border" : "border-transparent",
      )}
    >
      <nav className="mx-auto flex h-16 w-full max-w-[1200px] items-center gap-6 px-5" aria-label="Điều hướng chính">
        <Link href="/" className="flex items-center gap-2 font-display text-[17px] font-semibold text-foreground">
          <span className="flex h-7 w-7 items-center justify-center rounded-[8px] border border-border bg-card text-[12px] font-semibold">VL</span>
          {BRAND.name}
        </Link>

        <ul className="hidden items-center gap-1 lg:flex">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <li key={item.href} className="relative">
                <Link
                  href={item.href}
                  className={cn("relative block rounded-[var(--radius-control)] px-3 py-2 text-[13px] transition-colors", active ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
                >
                  {item.label}
                  {active ? (
                    <motion.span layoutId="public-nav-underline" className="absolute inset-x-2 -bottom-px h-px bg-foreground" />
                  ) : null}
                </Link>
              </li>
            );
          })}
          <li className="relative">
            <button
              type="button"
              className="flex items-center gap-1 rounded-[var(--radius-control)] px-3 py-2 text-[13px] text-muted-foreground hover:text-foreground"
              onClick={() => setDocsOpen((value) => !value)}
              aria-expanded={docsOpen}
            >
              Tài liệu
              <ChevronDown className="h-3.5 w-3.5" aria-hidden />
            </button>
            <AnimatePresence>
              {docsOpen ? (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.12 }}
                  className="absolute left-0 top-full mt-1 w-56 rounded-[var(--radius-overlay)] border border-border bg-popover p-1.5 hairline-shadow"
                  onMouseLeave={() => setDocsOpen(false)}
                >
                  {DOCS_MENU.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="block rounded-[var(--radius-control)] px-2.5 py-1.5 text-[13px] text-muted-foreground hover:bg-muted hover:text-foreground"
                      onClick={() => setDocsOpen(false)}
                    >
                      {item.label}
                    </Link>
                  ))}
                </motion.div>
              ) : null}
            </AnimatePresence>
          </li>
        </ul>

        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Đổi giao diện sáng/tối" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
          </Button>
          <span className="hidden rounded-[var(--radius-control)] border border-border px-2 py-1 text-[11px] text-muted-foreground sm:inline">VI</span>
          <Link href="/login" className="hidden text-[13px] text-muted-foreground hover:text-foreground sm:inline">
            Đăng nhập
          </Link>
          <Link
            href={role === "visitor" ? "/login" : "/app/investigations/new"}
            className="hidden h-8 items-center gap-2 rounded-[var(--radius-control)] bg-primary px-3 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 sm:inline-flex"
          >
            <LayoutDashboard className="h-3.5 w-3.5" aria-hidden />
            {role === "visitor" ? "Bắt đầu điều tra" : "Vào không gian làm việc"}
          </Link>
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Mở menu" onClick={() => setMobileOpen(true)}>
            <Menu className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </nav>

      <AnimatePresence>
        {mobileOpen ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-background lg:hidden"
          >
            <div className="flex h-16 items-center justify-between px-5">
              <span className="font-display text-[17px] font-semibold">{BRAND.name}</span>
              <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} aria-label="Đóng menu">
                <X className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            <ul className="space-y-1 px-5 py-4">
              {[...NAV, ...DOCS_MENU].map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="block rounded-[var(--radius-control)] px-3 py-2.5 text-[15px] text-foreground hover:bg-muted" onClick={() => setMobileOpen(false)}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
            <div className="mt-4 space-y-2 px-5">
              <Link
                href="/app/investigations/new"
                className="flex h-9 w-full items-center justify-center rounded-[var(--radius-control)] bg-primary text-sm font-medium text-primary-foreground"
                onClick={() => setMobileOpen(false)}
              >
                Bắt đầu điều tra
              </Link>
              <Link
                href="/login"
                className="flex h-9 w-full items-center justify-center rounded-[var(--radius-control)] border border-input text-sm text-foreground"
                onClick={() => setMobileOpen(false)}
              >
                Đăng nhập
              </Link>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  );
}

export function PublicFooter() {
  const columns = [
    {
      title: "Sản phẩm",
      links: [
        { href: "/how-it-works", label: "Cách hoạt động" },
        { href: "/data-sources", label: "Nguồn dữ liệu" },
        { href: "/examples", label: "Ca điều tra mẫu" },
        { href: "/login", label: "Đăng nhập" },
      ],
    },
    {
      title: "Tài nguyên",
      links: [
        { href: "/blog", label: "Blog" },
        { href: "/docs", label: "Tài liệu" },
        { href: "/glossary", label: "Thuật ngữ" },
        { href: "/faq", label: "Câu hỏi thường gặp" },
      ],
    },
    {
      title: "Minh bạch",
      links: [
        { href: "/limitations", label: "Giới hạn & an toàn AI" },
        { href: "/privacy", label: "Chính sách bảo mật" },
        { href: "/terms", label: "Điều khoản sử dụng" },
      ],
    },
    {
      title: "Dự án",
      links: [
        { href: "/about", label: "Về P-066" },
        { href: "/contact", label: "Liên hệ" },
      ],
    },
  ];
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto w-full max-w-[1200px] px-5 py-12">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-1">
            <p className="font-display text-[16px] font-semibold text-foreground">{BRAND.name}</p>
            <p className="mt-2 max-w-[26ch] text-[13px] leading-relaxed text-muted-foreground">{BRAND.tagline}</p>
          </div>
          {columns.map((column) => (
            <div key={column.title}>
              <p className="text-[13px] font-semibold text-foreground">{column.title}</p>
              <ul className="mt-3 space-y-2">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className="text-[13px] text-muted-foreground hover:text-foreground">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-10 border-t border-border pt-6">
          <p className="max-w-[80ch] text-[12px] leading-relaxed text-muted-foreground">{BRAND.disclaimer}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[12px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-support" aria-hidden /> Hệ thống minh họa: hoạt động bình thường
            </span>
            <span>© {new Date().getFullYear()} {BRAND.org}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
