"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "../../src/api";
import { isLive } from "../../src/lib/env";
import { users } from "../../src/mocks/seed";
import {
  Button,
  IconButton,
  Modal,
  StatusPill,
  cx,
  useToast,
} from "../../src/components/ui";
import { Icon, type IconName } from "../../src/components/icons";
import { useSession, useTheme } from "../providers";

type NavItem = {
  href: string;
  label: string;
  icon: IconName;
  hideForResponder?: boolean;
  badge?: string;
};

const navGroups: { title: string; items: NavItem[] }[] = [
  {
    title: "Tổng quan & Chỉ số",
    items: [
      { href: "/dashboard", label: "Bảng điều khiển", icon: "dashboard", hideForResponder: true },
    ],
  },
  {
    title: "Phân hệ lâm sàng",
    items: [
      { href: "/cases", label: "Danh sách ca bệnh", icon: "cases", hideForResponder: true },
      { href: "/dispatch", label: "Điều phối kíp trực", icon: "dispatch", hideForResponder: true },
      { href: "/tasks", label: "Nhiệm vụ xác minh", icon: "tasks" },
    ],
  },
  {
    title: "AI Co-pilot",
    items: [
      { href: "/agent-chat", label: "Trợ lý Agent Chat", icon: "chat", badge: "Live" },
    ],
  },
];

const roleLabel = (role: string) =>
  role === "clinician"
    ? "Bác sĩ phê duyệt"
    : role === "reviewer"
      ? "Dược sĩ rà soát"
      : role === "responder"
        ? "Điều dưỡng tiếp nhận"
        : "Quản trị viên";

const breadcrumbFor = (pathname: string) => {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return ["Tổng quan"];
  if (parts[0] === "dashboard") return ["Tổng quan", "Bảng điều khiển"];
  if (parts[0] === "dispatch") return ["Nghiệp vụ", "Điều phối kíp trực"];
  if (parts[0] === "tasks") return ["Nghiệp vụ", "Nhiệm vụ xác minh"];
  if (parts[0] === "agent-chat") return ["AI Co-pilot", "Trợ lý Chat đối chiếu"];
  if (parts[0] === "cases") {
    const trail = ["Nghiệp vụ", "Danh sách ca bệnh"];
    if (parts[1]) trail.push(`Ca ${parts[1]}`);
    if (parts[2] === "review") trail.push("Tổng hợp & Ký duyệt");
    return trail;
  }
  return ["MedReview"];
};

function ShellNav({ onNavigate, isResponder }: { onNavigate?: () => void; isResponder: boolean }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-6" aria-label="Điều hướng chính">
      {navGroups.map((group) => {
        const items = group.items.filter((item) => !(isResponder && item.hideForResponder));
        if (!items.length) return null;
        return (
          <div key={group.title}>
            <p className="mb-2.5 px-3.5 text-[10.5px] font-bold tracking-[0.16em] text-slate-400 uppercase">
              {group.title}
            </p>
            <ul className="space-y-1">
              {items.map((item) => {
                const active =
                  pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={cx(
                        "group relative flex items-center justify-between rounded-xl px-3.5 py-2.5 text-[13px] font-semibold no-underline transition-all duration-150",
                        active
                          ? "bg-gradient-to-r from-teal-500/20 to-teal-500/5 text-white shadow-xs"
                          : "text-slate-300 hover:bg-white/[0.06] hover:text-white",
                      )}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span
                          className={cx(
                            "grid size-7.5 place-items-center rounded-lg border transition-all duration-150",
                            active
                              ? "border-teal-400/40 bg-teal-500/25 text-teal-300 shadow-sm shadow-teal-500/30"
                              : "border-white/10 bg-white/5 text-slate-400 group-hover:border-white/20 group-hover:text-slate-200",
                          )}
                        >
                          <Icon name={item.icon} className="size-4" />
                        </span>
                        <span className="truncate">{item.label}</span>
                      </div>

                      {item.badge && (
                        <span className="rounded-full bg-teal-400/20 px-2 py-0.5 text-[10px] font-bold text-teal-300 border border-teal-400/30">
                          {item.badge}
                        </span>
                      )}

                      {active && (
                        <span className="absolute top-1/2 -left-3 h-6 w-1 -translate-y-1/2 rounded-r-full bg-teal-400 shadow-sm shadow-teal-400/80" />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, setUserId, clear } = useSession();
  const { theme, toggle } = useTheme();
  const notify = useToast();
  const [mobileNav, setMobileNav] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);

  useEffect(() => setMobileNav(false), [pathname]);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.role === "responder" && !pathname.startsWith("/tasks")) {
      router.replace("/tasks");
    }
  }, [user, pathname, router]);

  const switchRole = (id: string) => {
    if (isLive) {
      router.push("/login");
      return;
    }
    const target = users.find((u) => u.id === id);
    setUserId(id);
    if (target?.role === "responder") router.replace("/tasks");
    else router.refresh();
    notify(`Đã chuyển vai trò sang ${target?.name ?? id}.`);
  };

  const logout = async () => {
    if (isLive) {
      void api("/sessions/current", undefined, { method: "DELETE" }).catch(() => {});
    }
    clear();
    setLogoutOpen(false);
    router.replace("/login");
  };

  if (!user) {
    return (
      <div className="grid min-h-dvh place-items-center bg-canvas text-[13px] text-muted">
        Đang mở phiên làm việc…
      </div>
    );
  }

  const trail = breadcrumbFor(pathname);

  return (
    <div className="min-h-dvh bg-canvas lg:grid lg:grid-cols-[272px_minmax(0,1fr)]">
      {/* Sidebar */}
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-[272px] flex-col overflow-y-auto bg-gradient-to-b from-[#091522] via-[#0c1a2b] to-[#070e17] border-r border-[#16253b] px-4.5 py-6 transition-transform lg:sticky lg:top-0 lg:z-auto lg:h-dvh lg:translate-x-0 shadow-xl",
          mobileNav ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Brand Header */}
        <div className="relative flex items-center justify-between">
          <Link
            href={user.role === "responder" ? "/tasks" : "/dashboard"}
            className="flex items-center gap-3 no-underline group"
          >
            <span className="grid size-10.5 place-items-center rounded-2xl bg-gradient-to-tr from-teal-600 via-teal-500 to-emerald-400 text-white shadow-lg shadow-teal-500/25 border border-teal-300/30 transition-transform group-hover:scale-105">
              <Icon name="cross" className="size-5.5" strokeWidth={2.4} />
            </span>
            <span className="leading-tight text-white">
              <span className="block font-heading text-[18px] font-extrabold tracking-tight">
                MedReview
              </span>
              <span className="block text-[9.5px] font-bold tracking-[0.16em] text-teal-400 uppercase">
                VMEC-03 · AI Copilot
              </span>
            </span>
          </Link>
          <IconButton
            name="close"
            label="Đóng điều hướng"
            onClick={() => setMobileNav(false)}
            className="border-white/10 bg-white/5 text-white lg:hidden"
          />
        </div>

        {/* Navigation List */}
        <div className="relative mt-8 flex-1">
          <ShellNav
            onNavigate={() => setMobileNav(false)}
            isResponder={user.role === "responder"}
          />
        </div>

        {/* System Guardrail Badge Card */}
        <div className="relative mt-6 rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-[12px] leading-relaxed text-slate-300 shadow-inner backdrop-blur-sm">
          <div className="flex items-center gap-2 font-bold text-white">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-teal-400 opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-teal-400" />
            </span>
            <span>Chuẩn mực Y tế VMEC-03</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-400 leading-normal">
            Trợ lý AI đối chiếu có bằng chứng trích xuất. Quyết định do Bác sĩ trực tiếp phê duyệt.
          </p>
        </div>
      </aside>

      {mobileNav && (
        <button
          type="button"
          aria-label="Đóng điều hướng"
          onClick={() => setMobileNav(false)}
          className="fixed inset-0 z-30 bg-slate-950/60 backdrop-blur-xs lg:hidden"
        />
      )}

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-col">
        {/* Topbar Header */}
        <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface/85 px-5 py-3.5 backdrop-blur-md lg:px-8 shadow-xs">
          <div className="flex min-w-0 items-center gap-3">
            <IconButton
              name="list"
              label="Mở điều hướng"
              onClick={() => setMobileNav(true)}
              className="lg:hidden"
            />
            <div className="min-w-0">
              <nav className="flex items-center gap-1.5 text-[11px] font-semibold text-muted">
                {trail.map((part, idx) => (
                  <span key={idx} className="flex items-center gap-1.5">
                    {idx > 0 && <span className="text-slate-300 dark:text-slate-700">/</span>}
                    <span className={idx === trail.length - 1 ? "font-bold text-ink" : ""}>
                      {part}
                    </span>
                  </span>
                ))}
              </nav>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Live Environment Indicator */}
            <span className="hidden items-center gap-2 rounded-full border border-teal-500/25 bg-teal-500/10 px-3 py-1.5 text-[11px] font-semibold text-brand-ink md:inline-flex shadow-2xs">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-teal-500 opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-teal-500" />
              </span>
              {isLive ? "Live Server · FastAPI" : "Replay Demo · MSW Engine"}
            </span>

            {/* Fast Role Switcher */}
            <div className="hidden sm:flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 p-1 text-[11.5px] font-semibold shadow-xs">
              <span className="px-2 text-muted text-[11px]">Đổi vai trò:</span>
              <select
                value={user.id}
                onChange={(event) => switchRole(event.target.value)}
                title="Chuyển nhanh vai trò để kiểm thử luồng demo"
                className="h-7.5 rounded-lg border border-line/80 bg-surface px-2.5 text-[12px] font-semibold text-ink outline-none cursor-pointer hover:border-brand/50 transition-colors"
              >
                {users.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.role})
                  </option>
                ))}
              </select>
            </div>

            {/* Dark/Light Toggle */}
            <IconButton
              name={theme === "dark" ? "sun" : "moon"}
              label={theme === "dark" ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}
              onClick={toggle}
              className="rounded-xl shadow-xs"
            />

            {/* User Avatar Badge */}
            <div className="flex items-center gap-2.5 rounded-full border border-line bg-surface-2 py-1 pr-3.5 pl-1.5 shadow-2xs">
              <span className="grid size-7.5 place-items-center rounded-full bg-gradient-to-tr from-teal-600 to-emerald-500 text-[11.5px] font-bold text-white shadow-sm">
                {user.name.charAt(0).toUpperCase()}
              </span>
              <span className="hidden leading-tight sm:block">
                <span className="block text-[12.5px] font-bold text-ink">{user.name}</span>
                <span className="block text-[10px] text-muted">{roleLabel(user.role)}</span>
              </span>
            </div>

            {/* Logout Button */}
            <Button
              variant="secondary"
              size="sm"
              icon="logout"
              onClick={() => setLogoutOpen(true)}
              title="Đăng xuất khỏi hệ thống"
            >
              Đăng xuất
            </Button>
          </div>
        </header>

        {/* Page Content Viewport */}
        <main className="min-w-0 flex-1 px-5 py-7 lg:px-9 lg:py-8">
          <div className="mx-auto w-full max-w-[1400px]">{children}</div>
        </main>

        {/* Footer */}
        <footer className="border-t border-line px-5 py-4.5 text-[11.5px] text-muted lg:px-9 bg-surface/50">
          <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3">
            <span>
              MedReview / VMEC-03 · Hệ thống Hỗ trợ Ra Quyết định Lâm sàng &amp; Đối chiếu Thuốc
            </span>
            <div className="flex items-center gap-2.5">
              <StatusPill tone={isLive ? "ok" : "info"} icon={isLive ? "shield" : "flask"}>
                {isLive ? "FastAPI Core Active" : "MSW Sandbox"}
              </StatusPill>
              <span>Dữ liệu hồ sơ mô phỏng lâm sàng</span>
            </div>
          </div>
        </footer>
      </div>

      {logoutOpen && (
        <Modal
          title="Xác nhận Đăng xuất"
          onClose={() => setLogoutOpen(false)}
          footer={
            <div className="flex justify-end gap-2.5">
              <Button variant="secondary" onClick={() => setLogoutOpen(false)}>
                Hủy bỏ
              </Button>
              <Button variant="danger" onClick={logout}>
                Đăng xuất an toàn
              </Button>
            </div>
          }
        >
          <p className="text-[13.5px] leading-relaxed text-ink-soft">
            Bạn có chắc chắn muốn kết thúc phiên làm việc của <strong>{user.name}</strong>?
          </p>
          <p className="mt-2 text-[12px] text-muted">
            Mọi dữ liệu nháp đã lưu trên hệ thống sẽ được bảo toàn an toàn cho ca trực tiếp theo.
          </p>
        </Modal>
      )}
    </div>
  );
}
