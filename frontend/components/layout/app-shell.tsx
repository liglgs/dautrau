"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  BookOpen,
  ChevronsLeft,
  ChevronsRight,
  Database,
  FileText,
  FlaskConical,
  FolderSearch,
  Gauge,
  LayoutDashboard,
  Library,
  Menu,
  MessageSquare,
  Moon,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  ShieldHalf,
  Sun,
  Users,
} from "lucide-react";
import { DATA_MODE } from "@/lib/api";
import { request, SESSION_AUTH } from "@/lib/api/real";
import { useQueryClient } from "@tanstack/react-query";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/utils";
import { Button, Input } from "@/components/ui";
import { ROLE_LABEL, useAppStore } from "@/lib/store/app-store";
import { useInvestigations } from "@/lib/hooks/use-data";
import { DemoBanner } from "@/components/pv/demo-banner";
import { useTheme } from "next-themes";
import type { Role } from "@/lib/types";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  roles?: Role[];
  /** Khoá đếm sống; số hiển thị lấy từ dữ liệu backend, không hard-code. */
  badgeKey?: "investigations" | "reviews";
}

const WORKSPACE_NAV: NavItem[] = [
  { href: "/app", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" aria-hidden /> },
  { href: "/app/investigations", label: "Cuộc điều tra", icon: <FolderSearch className="h-4 w-4" aria-hidden />, badgeKey: "investigations" },
  { href: "/app/reviews", label: "Hàng chờ duyệt", icon: <ShieldCheck className="h-4 w-4" aria-hidden />, roles: ["reviewer"], badgeKey: "reviews" },
];

const LIBRARY_NAV: NavItem[] = [
  { href: "/app/dossiers", label: "Hồ sơ đã xuất", icon: <FileText className="h-4 w-4" aria-hidden /> },
  { href: "/app/library", label: "Thư viện tài liệu", icon: <BookOpen className="h-4 w-4" aria-hidden /> },
];

const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Tổng quan", icon: <LayoutDashboard className="h-4 w-4" aria-hidden /> },
  { href: "/admin/users", label: "Người dùng & vai trò", icon: <Users className="h-4 w-4" aria-hidden /> },
  { href: "/admin/sources", label: "Nguồn dữ liệu", icon: <FolderSearch className="h-4 w-4" aria-hidden /> },
  { href: "/admin/ingestion", label: "Nạp tài liệu", icon: <Database className="h-4 w-4" aria-hidden /> },
  { href: "/admin/corpus", label: "Kho tài liệu", icon: <Library className="h-4 w-4" aria-hidden /> },
  { href: "/admin/terminology", label: "Thuật ngữ & từ đồng nghĩa", icon: <BookOpen className="h-4 w-4" aria-hidden /> },
  { href: "/admin/agent-config", label: "Cấu hình agent", icon: <Gauge className="h-4 w-4" aria-hidden /> },
  { href: "/admin/guardrails", label: "Guardrail", icon: <ShieldHalf className="h-4 w-4" aria-hidden /> },
  { href: "/admin/evaluation", label: "Đánh giá chất lượng", icon: <FlaskConical className="h-4 w-4" aria-hidden /> },
  { href: "/admin/audit", label: "Audit log", icon: <FileText className="h-4 w-4" aria-hidden /> },
  { href: "/admin/content", label: "Nội dung", icon: <MessageSquare className="h-4 w-4" aria-hidden /> },
  { href: "/admin/system", label: "Sức khỏe hệ thống", icon: <Settings className="h-4 w-4" aria-hidden /> },
];

export function AppShell({
  children,
  variant = "app",
  breadcrumb,
}: {
  children: React.ReactNode;
  variant?: "app" | "admin";
  breadcrumb?: { href: string; label: string }[];
}) {
  const pathname = usePathname();
  const router = useRouter();
  const sessionMode = DATA_MODE === "api" && SESSION_AUTH;
  const [sessionReady, setSessionReady] = React.useState(false);
  const [sessionError, setSessionError] = React.useState<string | null>(null);
  // Explicit logout owns navigation until this shell unmounts.
  const logoutStarted = React.useRef(false);
  const [userName, setUserName] = React.useState("");
  const queryClient = useQueryClient();
  const { role, sidebarCollapsed, toggleSidebar } = useAppStore();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [commandOpen, setCommandOpen] = React.useState(false);
  const { theme, setTheme } = useTheme();

  React.useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  React.useEffect(() => {
    if (!sessionMode) return;
    let active = true;
    let redirecting = false;
    const expired = () => {
      if (!active || redirecting || logoutStarted.current) return;
      redirecting = true;
      setSessionReady(false);
      useAppStore.getState().setRole("visitor");
      queryClient.clear();
      router.replace(`/login?returnTo=${encodeURIComponent(window.location.pathname + window.location.search)}`);
    };
    const verify = async () => {
      if (logoutStarted.current) return;
      try {
        const user = await request<{ user_id: string; role: "investigator" | "reviewer" }>("/api/v1/auth/me");
        if (active && !logoutStarted.current) { useAppStore.getState().setRole(user.role); setUserName(user.user_id); setSessionReady(true); setSessionError(null); }
      } catch (error) {
        if (active && !logoutStarted.current) {
          if ((error as { status?: number }).status === 401) expired();
          else { setSessionReady(false); setSessionError((error as Error).message); }
        }
      }
    };
    window.addEventListener("vigilens-session-expired", expired);
    window.addEventListener("focus", verify);
    void verify();
    return () => { active = false; window.removeEventListener("vigilens-session-expired", expired); window.removeEventListener("focus", verify); };
  }, [sessionMode, queryClient, router]);

  const investigations = useInvestigations(!sessionMode || sessionReady).data?.items ?? [];
  const isAdminArea = variant === "admin" || pathname.startsWith("/admin");
  const primary = isAdminArea ? ADMIN_NAV : WORKSPACE_NAV;
  const secondary = isAdminArea ? [] : LIBRARY_NAV;

  const badges: Record<string, number> = {
    investigations: investigations.length,
    reviews: investigations.filter((item) => item.runStatus === "waiting_for_review").length,
  };

  const navButton = (item: NavItem) => {
    const active = pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
    if (item.roles && !item.roles.includes(role)) return null;
    return (
      <Link
        key={item.href}
        href={item.href}
        onClick={() => setMobileOpen(false)}
        className={cn(
          "group flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-[13px] transition-colors",
          active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
          sidebarCollapsed && "justify-center px-0",
        )}
        title={sidebarCollapsed ? item.label : undefined}
      >
        {item.icon}
        {!sidebarCollapsed ? <span className="truncate">{item.label}</span> : null}
        {!sidebarCollapsed && item.badgeKey && badges[item.badgeKey] ? (
          <span className="tabular ml-auto rounded-full bg-ai-soft px-1.5 text-[11px] text-ai-fg">
            {badges[item.badgeKey]}
          </span>
        ) : null}
      </Link>
    );
  };

  const sidebar = (
    <aside
      className={cn(
        "flex h-full flex-col gap-4 border-r bg-card px-3 py-4 transition-[width] duration-200",
        isAdminArea && "border-l-2 border-l-neutral",
        sidebarCollapsed ? "w-16" : "w-[264px]",
      )}
    >
      <div className={cn("flex items-center gap-2 px-1", sidebarCollapsed && "justify-center")}>
        <Link href="/" className="flex items-center gap-2 font-display text-[16px] font-semibold text-foreground">
          <span className="flex h-7 w-7 items-center justify-center rounded-[8px] border border-border text-[12px]">VL</span>
          {!sidebarCollapsed ? BRAND.name : null}
        </Link>
      </div>
      {isAdminArea && !sidebarCollapsed ? (
        <p className="rounded-[var(--radius-control)] bg-muted px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Quản trị
        </p>
      ) : null}

      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto" aria-label="Điều hướng không gian làm việc">
        <div className="space-y-1">
          {!sidebarCollapsed ? <p className="px-2.5 text-[11px] uppercase tracking-wide text-muted-foreground">{isAdminArea ? "Quản trị" : "Làm việc"}</p> : null}
          {primary.map(navButton)}
        </div>
        {secondary.length > 0 ? (
          <div className="space-y-1">
            {!sidebarCollapsed ? <p className="px-2.5 text-[11px] uppercase tracking-wide text-muted-foreground">Kho</p> : null}
            {secondary.map(navButton)}
          </div>
        ) : null}
        {!isAdminArea ? (
          <div className="space-y-1">
            {!sidebarCollapsed ? <p className="px-2.5 text-[11px] uppercase tracking-wide text-muted-foreground">Trợ lý</p> : null}
            <Link
              href="/app/assistant"
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-[13px] text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                sidebarCollapsed && "justify-center px-0",
              )}
            >
              <MessageSquare className="h-4 w-4 text-ai" aria-hidden />
              {!sidebarCollapsed ? "Trợ lý VigiLens" : null}
            </Link>
          </div>
        ) : null}
      </nav>

      <div className="space-y-1 border-t border-border pt-3">
        <Link href="/app/notifications" className={cn("flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-[13px] text-muted-foreground hover:bg-muted/60", sidebarCollapsed && "justify-center px-0")}>
          <Bell className="h-4 w-4" aria-hidden />
          {!sidebarCollapsed ? "Thông báo" : null}
        </Link>
        <Link href="/app/settings" className={cn("flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-[13px] text-muted-foreground hover:bg-muted/60", sidebarCollapsed && "justify-center px-0")}>
          <Settings className="h-4 w-4" aria-hidden />
          {!sidebarCollapsed ? "Cài đặt" : null}
        </Link>
        {role === "admin" ? (
          <Link href="/admin" className={cn("flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-2 text-[13px] text-muted-foreground hover:bg-muted/60", sidebarCollapsed && "justify-center px-0")}>
            <ShieldCheck className="h-4 w-4" aria-hidden />
            {!sidebarCollapsed ? "Quản trị" : null}
          </Link>
        ) : null}
        <div className={cn("mt-2 flex items-center gap-2 rounded-[var(--radius-card)] border border-border px-2 py-2", sidebarCollapsed && "justify-center")}>
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-foreground">TM</span>
          {!sidebarCollapsed ? (
            <span className="min-w-0">
              <span className="block truncate text-[12px] font-medium text-foreground">{sessionMode ? userName : "Trần Minh"}</span>
              <span className="block truncate text-[11px] text-muted-foreground">{ROLE_LABEL[role]}</span>
            </span>
          ) : null}
        </div>
        {sessionMode ? <Button variant="ghost" onClick={async () => {
          if (logoutStarted.current) return;
          logoutStarted.current = true;
          try { await request("/api/v1/auth/logout", { method: "POST" }); queryClient.clear(); useAppStore.getState().setRole("visitor"); setSessionReady(false); router.replace("/login"); }
          catch (error) { logoutStarted.current = false; setSessionError((error as Error).message); }
        }}>Đăng xuất</Button> : null}
        <button
          type="button"
          onClick={toggleSidebar}
          className="mt-1 flex w-full items-center justify-center gap-2 rounded-[var(--radius-control)] px-2 py-1.5 text-[12px] text-muted-foreground hover:bg-muted"
          aria-label={sidebarCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
        >
          {sidebarCollapsed ? <ChevronsRight className="h-3.5 w-3.5" aria-hidden /> : <ChevronsLeft className="h-3.5 w-3.5" aria-hidden />}
          {!sidebarCollapsed ? "Thu gọn" : null}
        </button>
      </div>
    </aside>
  );

  if (sessionMode && !sessionReady) return <div className="p-8" role="status">{sessionError ?? "Đang xác nhận phiên đăng nhập…"}</div>;
  return (
    <div className="flex min-h-screen flex-col">
      <DemoBanner compact />
      {sessionError ? <p role="alert" className="p-3">{sessionError}</p> : null}
      <div className="flex flex-1">
        <div className="hidden lg:block">{sidebar}</div>
        {mobileOpen ? (
          <div className="fixed inset-0 z-40 flex lg:hidden">
            <button className="absolute inset-0 bg-foreground/20" aria-label="Đóng thanh bên" onClick={() => setMobileOpen(false)} />
            <div className="relative">{sidebar}</div>
          </div>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur-sm">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Mở thanh bên">
              <Menu className="h-4 w-4" aria-hidden />
            </Button>
            <nav aria-label="Breadcrumb" className="min-w-0 flex-1">
              <ol className="flex items-center gap-2 text-[13px] text-muted-foreground">
                <li>
                  <Link href={isAdminArea ? "/admin" : "/app"} className="hover:text-foreground">
                    {isAdminArea ? "Quản trị" : "Không gian làm việc"}
                  </Link>
                </li>
                {(breadcrumb ?? []).map((crumb) => (
                  <li key={crumb.href} className="flex min-w-0 items-center gap-2">
                    <span aria-hidden>/</span>
                    <Link href={crumb.href} className="truncate text-foreground">
                      {crumb.label}
                    </Link>
                  </li>
                ))}
              </ol>
            </nav>
            <button
              type="button"
              onClick={() => setCommandOpen(true)}
              className="hidden items-center gap-2 rounded-[var(--radius-control)] border border-input bg-card px-2.5 py-1.5 text-[12px] text-muted-foreground hover:bg-muted md:flex"
            >
              <Search className="h-3.5 w-3.5" aria-hidden />
              Tìm kiếm / lệnh
              <kbd className="mono rounded border border-border px-1 text-[10px]">⌘K</kbd>
            </button>
            <Button variant="ghost" size="icon" aria-label="Đổi giao diện" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
            </Button>
            <Button variant="ghost" size="icon" aria-label="Thông báo">
              <Bell className="h-4 w-4" aria-hidden />
            </Button>
            <span className="hidden rounded-[var(--radius-chip)] border border-border px-2 py-0.5 text-[11px] text-muted-foreground sm:inline">
              {ROLE_LABEL[role]}
            </span>
            <Link
              href="/app/investigations/new"
              className="inline-flex h-8 items-center gap-1.5 rounded-[var(--radius-control)] bg-primary px-3 text-[13px] font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden />
              Điều tra mới
            </Link>
          </header>

          <main className="min-w-0 flex-1 px-4 py-5 sm:px-6">{children}</main>
        </div>
      </div>

      {commandOpen ? (
        <CommandPalette
          onClose={() => setCommandOpen(false)}
          onNavigate={(href) => {
            setCommandOpen(false);
            router.push(href);
          }}
        />
      ) : null}
    </div>
  );
}

function CommandPalette({ onClose, onNavigate }: { onClose: () => void; onNavigate: (href: string) => void }) {
  const [query, setQuery] = React.useState("");
  const commands = [
    { label: "Điều tra mới", href: "/app/investigations/new" },
    { label: "Mở hàng chờ duyệt", href: "/app/reviews" },
    { label: "Danh sách cuộc điều tra", href: "/app/investigations" },
    { label: "Thư viện hồ sơ", href: "/app/dossiers" },
    { label: "Trợ lý VigiLens", href: "/app/assistant" },
    { label: "Giới hạn & cách đọc kết quả", href: "/limitations" },
  ];
  const filtered = commands.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]" role="dialog" aria-modal="true" aria-label="Bảng lệnh">
      <button className="absolute inset-0 bg-foreground/20 backdrop-blur-[1px]" onClick={onClose} aria-label="Đóng bảng lệnh" />
      <div className="relative w-full max-w-lg rounded-[var(--radius-overlay)] border border-border bg-popover p-2 hairline-shadow">
        <Input autoFocus placeholder="Tìm cuộc điều tra theo mã/thuốc/biến cố, hoặc chạy lệnh…" value={query} onChange={(event) => setQuery(event.target.value)} />
        <ul className="mt-2 max-h-72 overflow-y-auto">
          {filtered.map((item) => (
            <li key={item.href}>
              <button
                type="button"
                onClick={() => onNavigate(item.href)}
                className="flex w-full items-center gap-2 rounded-[var(--radius-control)] px-2.5 py-2 text-left text-[13px] text-foreground hover:bg-muted"
              >
                {item.label}
              </button>
            </li>
          ))}
          {filtered.length === 0 ? <li className="px-2.5 py-2 text-[13px] text-muted-foreground">Không có kết quả phù hợp.</li> : null}
        </ul>
      </div>
    </div>
  );
}
