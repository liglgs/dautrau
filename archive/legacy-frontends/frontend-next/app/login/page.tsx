"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "../../src/api";
import { isLive } from "../../src/lib/env";
import { users } from "../../src/mocks/seed";
import { Avatar, Button, ErrorBox, Panel, useToast } from "../../src/components/ui";
import { Icon } from "../../src/components/icons";
import { useSession } from "../providers";

const roleLabel = (role: string) =>
  role === "clinician"
    ? "Bác sĩ phê duyệt lâm sàng"
    : role === "reviewer"
      ? "Dược sĩ đối chiếu y lệnh"
      : role === "responder"
        ? "Điều dưỡng tiếp nhận thông tin"
        : "Quản trị viên";

const roleTone = (role: string) =>
  role === "clinician"
    ? "ok"
    : role === "reviewer"
      ? "brand"
      : role === "responder"
        ? "warn"
        : "neutral";

const highlights = [
  {
    icon: "shield" as const,
    title: "100% Nhận định có bằng chứng nguồn gốc",
    text: "Mọi dữ kiện thuốc được gán chặt chẽ với trích dẫn, mã băm sha256 và số phiên bản văn bản gốc.",
  },
  {
    icon: "list" as const,
    title: "Kiểm soát khoảng trống thông tin",
    text: "Đơn thuốc cũ không tự chứng minh bệnh nhân đang dùng tại nhà; tự động tạo câu hỏi xác minh gửi điều dưỡng.",
  },
  {
    icon: "checkCircle" as const,
    title: "Phê duyệt lâm sàng hai lớp",
    text: "Dược sĩ rà soát chuẩn bị phương án, Bác sĩ điều trị trực tiếp thẩm định và ký duyệt biên bản.",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { setUserId } = useSession();
  const notify = useToast();
  const [selected, setSelected] = useState<string>();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const enter = (id: string) => {
    setUserId(id);
    const target = users.find((u) => u.id === id);
    notify(`Đã đăng nhập ${target?.name ?? id}.`);
    router.replace(target?.role === "responder" ? "/tasks" : "/dashboard");
  };

  return (
    <div className="grid min-h-dvh bg-canvas lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      {/* Left Medical Hero Column */}
      <section className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-b from-[#091522] via-[#0d1e32] to-[#070e17] px-12 py-14 text-white lg:flex border-r border-[#16253b] shadow-2xl">
        <div
          className="grid-backdrop pointer-events-none absolute inset-0 opacity-40"
          aria-hidden="true"
        />
        <div
          className="absolute -top-32 -right-32 size-[500px] rounded-full bg-teal-500/15 blur-[120px]"
          aria-hidden="true"
        />
        <div
          className="absolute bottom-10 left-10 size-[350px] rounded-full bg-emerald-500/10 blur-[100px]"
          aria-hidden="true"
        />

        <div className="relative">
          {/* Brand Mark */}
          <div className="flex items-center gap-3.5">
            <span className="grid size-12 place-items-center rounded-2xl bg-gradient-to-tr from-teal-600 via-teal-500 to-emerald-400 text-white shadow-lg shadow-teal-500/30 border border-teal-300/30">
              <Icon name="cross" className="size-6" strokeWidth={2.4} />
            </span>
            <span>
              <span className="block font-heading text-[22px] font-extrabold tracking-tight">
                MedReview
              </span>
              <span className="block text-[10px] font-bold tracking-[0.18em] text-teal-400 uppercase">
                VMEC-03 · Hệ Thống Đối Chiếu Thuốc Lâm Sàng
              </span>
            </span>
          </div>

          <h1 className="mt-12 max-w-[480px] font-heading text-[38px] leading-[1.18] font-extrabold tracking-tight text-white">
            Nền tảng rà soát &amp; đối chiếu thuốc nhập viện chuẩn xác
          </h1>
          <p className="mt-4 max-w-[440px] text-[14px] leading-relaxed text-slate-300">
            Trợ lý AI giúp bác sĩ và dược sĩ phát hiện khác biệt đơn thuốc, trích xuất bằng chứng minh bạch và ngăn ngừa xung đột thuốc nguy hiểm.
          </p>

          <ul className="mt-10 space-y-5 max-w-[460px]">
            {highlights.map((item) => (
              <li key={item.title} className="flex gap-4 items-start">
                <span className="mt-0.5 grid size-9.5 shrink-0 place-items-center rounded-xl border border-white/15 bg-white/[0.06] text-teal-300 shadow-sm backdrop-blur-xs">
                  <Icon name={item.icon} className="size-4.5" />
                </span>
                <div>
                  <strong className="block font-heading text-[13.5px] font-bold text-white">
                    {item.title}
                  </strong>
                  <span className="mt-0.5 block text-[12px] text-slate-300 leading-normal">
                    {item.text}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative flex items-center gap-2 text-[12px] text-slate-400 border-t border-white/10 pt-5">
          <Icon name="flask" className="size-4 text-teal-400" />
          Bản nghiên cứu chuẩn hóa dữ liệu mô phỏng lâm sàng · VMEC-03
        </p>
      </section>

      {/* Right Login / Account Selection Column */}
      <section className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-[480px]">
          {/* Mobile Logo */}
          <div className="mb-7 flex items-center gap-3 lg:hidden">
            <span className="grid size-11 place-items-center rounded-2xl bg-gradient-to-tr from-teal-600 to-emerald-400 text-white shadow-md">
              <Icon name="cross" className="size-5.5" strokeWidth={2.4} />
            </span>
            <span>
              <span className="block font-heading text-[19px] font-bold tracking-tight text-ink">
                MedReview
              </span>
              <span className="block text-[10px] font-bold tracking-[0.16em] text-teal-600 uppercase">
                VMEC-03 · Đối chiếu thuốc
              </span>
            </span>
          </div>

          <div className="inline-flex items-center gap-2 rounded-full border border-teal-500/20 bg-teal-500/10 px-3 py-1 text-[10.5px] font-bold tracking-[0.12em] text-teal-700 dark:text-teal-300 uppercase">
            <span className="size-1.5 rounded-full bg-teal-500" />
            Cổng tiếp nhận hồ sơ
          </div>

          <h2 className="mt-3 font-heading text-[26px] font-extrabold tracking-tight text-ink">
            Chọn Vai Trò Trải Nghiệm
          </h2>
          <p className="mt-2 text-[13px] text-muted leading-relaxed">
            {isLive
              ? "Đăng nhập tài khoản chuyên môn để rà soát hồ sơ thực tế."
              : "Chọn một trong các kíp trực mẫu để kiểm thử quy trình đối chiếu thuốc hai lớp."}
          </p>

          {/* Account Selector Cards */}
          <Panel className="mt-6 overflow-hidden border border-line shadow-md">
            <ul className="divide-y divide-line/70">
              {users.map((user) => (
                <li key={user.id}>
                  <button
                    type="button"
                    aria-label={`${user.name} →`}
                    onClick={() => {
                      if (isLive) {
                        setSelected(user.id);
                        setError("");
                      } else {
                        enter(user.id);
                      }
                    }}
                    className="flex w-full items-center gap-4 px-5 py-4 text-left transition-all hover:bg-teal-50/30 dark:hover:bg-teal-950/20 group cursor-pointer"
                  >
                    <Avatar name={user.name} tone={roleTone(user.role)} className="size-10 text-[13px] shadow-xs" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-heading text-[14px] font-bold text-ink group-hover:text-brand transition-colors">
                        {user.name}
                      </span>
                      <span className="block text-[12px] text-muted">
                        {roleLabel(user.role)} · ID: <span className="font-mono">{user.id}</span>
                      </span>
                    </span>
                    <span className="hidden rounded-full border border-line bg-surface-2 px-3 py-1 text-[11px] font-bold text-ink-soft sm:inline-flex group-hover:border-teal-500/30">
                      {user.role}
                    </span>
                    <span className="text-slate-300 group-hover:text-teal-600 transition-colors font-bold text-sm">
                      →
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Panel>

          {isLive && selected && (
            <Panel className="mt-4 border border-line shadow-md">
              <form
                className="space-y-4 px-6 py-5"
                onSubmit={async (event) => {
                  event.preventDefault();
                  setBusy(true);
                  setError("");
                  try {
                    const user = await api<{ id: string; role: string }>("/sessions", {
                      user_id: selected,
                      password,
                    });
                    enter(user.id);
                  } catch (err) {
                    setError((err as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <div className="flex items-center justify-between">
                  <p className="font-heading text-[14px] font-bold text-ink">
                    Xác thực: {users.find((u) => u.id === selected)?.name}
                  </p>
                  <button
                    type="button"
                    onClick={() => setSelected(undefined)}
                    className="text-[11.5px] text-muted hover:underline"
                  >
                    Đổi người khác
                  </button>
                </div>
                <label className="block text-[12px] font-semibold text-ink-soft">
                  Mật khẩu tài khoản (Mặc định: demo12345)
                  <input
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    placeholder="Nhập mật khẩu…"
                    className="mt-1.5 h-10 w-full rounded-xl border border-line bg-surface px-3.5 text-[13px] outline-none focus:border-brand"
                  />
                </label>
                {error && <ErrorBox message={error} />}
                <Button type="submit" variant="primary" busy={busy} className="w-full justify-center shadow-md">
                  Vào phiên làm việc
                </Button>
              </form>
            </Panel>
          )}

          <div className="mt-6 flex items-center justify-center gap-2 text-[12px] text-muted">
            <Icon name="info" className="size-4 text-teal-600" />
            <span>Hệ thống áp dụng phân quyền rà soát &amp; phê duyệt độc lập.</span>
          </div>
        </div>
      </section>
    </div>
  );
}
