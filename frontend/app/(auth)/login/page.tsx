"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LoaderCircle, ShieldCheck } from "lucide-react";
import { Alert, Button, Card, CardBody, Input, Label } from "@/components/ui";
import { ROLE_LABEL, useAppStore } from "@/lib/store/app-store";
import { DATA_MODE } from "@/lib/api";
import { request, SESSION_AUTH } from "@/lib/api/real";
import { useQueryClient } from "@tanstack/react-query";
import type { Role } from "@/lib/types";

/** Tài khoản minh họa chỉ tồn tại ở chế độ dữ liệu mẫu. */
const DEMO_ACCOUNTS: { role: Role; email: string; password: string }[] = [
  { role: "investigator", email: "dieutra@demo.vigilens", password: "demo-investigator" },
  { role: "reviewer", email: "duyet@demo.vigilens", password: "demo-reviewer" },
  { role: "admin", email: "quantri@demo.vigilens", password: "demo-admin" },
];

/** Vai trò backend thật chấp nhận khi xác thực bằng token vai trò (không có tài khoản quản trị). */
const TOKEN_ROLES: { role: "investigator" | "reviewer"; note: string }[] = [
  { role: "investigator", note: "Tạo và theo dõi cuộc điều tra" },
  { role: "reviewer", note: "Duyệt hồ sơ và nạp tài liệu vào kho" },
];

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const setRole = useAppStore((state) => state.setRole);
  const sessionMode = DATA_MODE === "api" && SESSION_AUTH;
  // Backend thật nhưng xác thực bằng token vai trò: chỉ các vai trò đã cấu hình token mới vào được.
  const roleTokenMode = DATA_MODE === "api" && !SESSION_AUTH;
  const [token, setToken] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (pending) return;
    if (sessionMode) {
      setPending(true);
      try {
        const user = await request<{ role: "investigator" | "reviewer" }>("/api/v1/auth/login", { method: "POST", body: { token } });
        queryClient.clear();
        setRole(user.role);
        setToken("");
        const destination = new URLSearchParams(window.location.search).get("returnTo");
        router.replace((destination === "/app" || destination?.startsWith("/app/")) && !destination?.includes("\\") ? destination : "/app");
      } catch (error) { setError((error as Error).message); }
      finally { setPending(false); }
      return;
    }
    const account = DEMO_ACCOUNTS.find((item) => item.email === email.trim() && item.password === password);
    if (!account) {
      setError("Ở chế độ dữ liệu minh họa, chỉ các tài khoản minh họa bên dưới đăng nhập được.");
      return;
    }
    setPending(true);
    setRole(account.role);
    setTimeout(() => router.push("/app"), 400);
  };

  /** Xác nhận vai trò với backend trước khi vào: không hiển thị thông tin đăng nhập mà backend từ chối. */
  const enterWithRole = async (role: "investigator" | "reviewer") => {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const user = await request<{ user_id: string; role: "investigator" | "reviewer" }>("/api/v1/auth/me", { role });
      queryClient.clear();
      setRole(user.role);
      router.replace("/app");
    } catch (error) {
      setError(`Backend không chấp nhận vai trò này: ${(error as Error).message}`);
    } finally {
      setPending(false);
    }
  };

  return (
    <Card className="w-full max-w-[440px]">
      <CardBody className="space-y-4">
        <div>
          <h1 className="font-display text-[24px] text-foreground">Đăng nhập</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            {sessionMode
              ? "Đăng nhập bằng token do nhóm cung cấp. Vai trò được xác định từ phiên máy chủ."
              : roleTokenMode
                ? "Backend cục bộ xác thực bằng token vai trò cấu hình ở máy chủ (VIGILENS_INVESTIGATOR_TOKEN / VIGILENS_REVIEWER_TOKEN). Chọn vai trò đã được cấu hình để vào."
                : "Đăng nhập minh họa để thử giao diện bằng dữ liệu mẫu."}
          </p>
        </div>

        {roleTokenMode ? (
          <div className="space-y-3">
            <div className="grid gap-2">
              {TOKEN_ROLES.map((item) => (
                <Button
                  key={item.role}
                  type="button"
                  variant={item.role === "investigator" ? "primary" : "outline"}
                  className="h-auto justify-start py-2.5 text-left"
                  disabled={pending}
                  onClick={() => void enterWithRole(item.role)}
                >
                  <span className="flex flex-col items-start">
                    <span className="text-[14px] font-medium">{ROLE_LABEL[item.role]}</span>
                    <span className="text-[12px] font-normal opacity-80">{item.note}</span>
                  </span>
                </Button>
              ))}
            </div>
            <p className="text-[12px] text-muted-foreground">
              Không có tài khoản quản trị trong chế độ này: backend chỉ chấp nhận các token vai trò đã cấu hình.
            </p>
            {error ? <Alert tone="caution" title="Chưa đăng nhập được">{error}</Alert> : null}
            {pending ? (
              <p className="flex items-center gap-2 text-[13px] text-muted-foreground" role="status">
                <LoaderCircle className="h-4 w-4 animate-spin-slow" aria-hidden /> Đang xác thực với backend…
              </p>
            ) : null}
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            {sessionMode ? (
              <div>
                <Label htmlFor="token">Token đăng nhập</Label>
                <Input id="token" type="password" autoComplete="off" required value={token} onChange={(event) => setToken(event.target.value)} />
              </div>
            ) : (
              <>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="ten@donvi.vn" />
                </div>
                <div>
                  <Label htmlFor="password">Mật khẩu</Label>
                  <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
                </div>
                <div className="flex items-center justify-between text-[12px]">
                  <Link href="/forgot-password" className="text-muted-foreground underline">
                    Quên mật khẩu?
                  </Link>
                  <Link href="/register" className="text-muted-foreground underline">
                    Tạo tài khoản
                  </Link>
                </div>
              </>
            )}
            {error ? <Alert tone="caution" title="Chưa đăng nhập được">{error}</Alert> : null}
            <Button type="submit" className="w-full" disabled={pending}>
              {pending ? <LoaderCircle className="h-4 w-4 animate-spin-slow" aria-hidden /> : <ShieldCheck className="h-4 w-4" aria-hidden />}
              Đăng nhập
            </Button>
          </form>
        )}

        {!sessionMode && !roleTokenMode ? (
          <>
            <div className="border-t border-border pt-3">
              <p className="text-[12px] uppercase tracking-wide text-muted-foreground">Tài khoản minh họa</p>
              <ul className="mt-2 space-y-1.5">
                {DEMO_ACCOUNTS.map((account) => (
                  <li key={account.email} className="flex items-center justify-between gap-2 text-[12px]">
                    <button
                      type="button"
                      onClick={() => {
                        setEmail(account.email);
                        setPassword(account.password);
                        setError(null);
                      }}
                      className="mono text-left text-muted-foreground underline"
                    >
                      {account.email} / {account.password}
                    </button>
                    <span className="text-muted-foreground">{ROLE_LABEL[account.role]}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Link href="/app" className="block text-center text-[13px] text-muted-foreground underline">
              Vào khu vực làm việc không cần đăng nhập
            </Link>
          </>
        ) : null}
      </CardBody>
    </Card>
  );
}
