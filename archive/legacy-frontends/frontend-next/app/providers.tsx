"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "../src/api";
import { isLive } from "../src/lib/env";
import { users } from "../src/mocks/seed";
import type { User } from "../src/types";
import { ToastProvider } from "../src/components/ui";

/* ------------------------------------------------------------------ *
 * Giao diện (light/dark) — lưu localStorage, mặc định theo hệ thống.
 * ------------------------------------------------------------------ */
type Theme = "light" | "dark";
const THEME_KEY = "vmec03-theme";

const ThemeContext = createContext<{ theme: Theme; toggle: () => void }>({
  theme: "light",
  toggle: () => {},
});

export const useTheme = () => useContext(ThemeContext);

function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const stored = window.localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(stored === "dark" || (!stored && prefersDark) ? "dark" : "light");
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const value = useMemo(
    () => ({ theme, toggle: () => setTheme((prev) => (prev === "dark" ? "light" : "dark")) }),
    [theme],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/* ------------------------------------------------------------------ *
 * Phiên demo — sessionStorage chỉ đọc được ở client nên mọi thứ đi qua
 * effect để tránh lệch hydration khi SSR.
 * ------------------------------------------------------------------ */
type SessionValue = {
  user: User | null;
  userId: string | null;
  hydrated: boolean;
  setUserId: (id: string) => void;
  clear: () => void;
};

const SessionContext = createContext<SessionValue>({
  user: null,
  userId: null,
  hydrated: false,
  setUserId: () => {},
  clear: () => {},
});

export const useSession = () => useContext(SessionContext);

function SessionProvider({ children }: { children: ReactNode }) {
  const [userId, setId] = useState<string | null>(null);
  const [ready, setReady] = useState(!isLive);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = window.sessionStorage.getItem("demo-user");
    if (!isLive) {
      setId(stored);
      setHydrated(true);
      return;
    }
    api<{ id: string }>("/sessions/current")
      .then((user) => {
        window.sessionStorage.setItem("demo-user", user.id);
        setId(user.id);
      })
      .catch(() => {
        window.sessionStorage.removeItem("demo-user");
        setId(null);
      })
      .finally(() => {
        setReady(true);
        setHydrated(true);
      });
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      userId,
      hydrated,
      user: users.find((u) => u.id === userId) ?? null,
      setUserId: (id: string) => {
        window.sessionStorage.setItem("demo-user", id);
        setId(id);
      },
      clear: () => {
        window.sessionStorage.removeItem("demo-user");
        setId(null);
      },
    }),
    [userId, hydrated],
  );

  if (!ready) {
    return (
      <div className="grid min-h-dvh place-items-center bg-canvas text-[13px] text-muted">
        Đang kiểm tra phiên đăng nhập…
      </div>
    );
  }
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

/* ------------------------------------------------------------------ *
 * Providers gốc: khởi động MSW (chế độ replay) rồi mới render ứng dụng
 * để không có truy vấn nào lọt ra ngoài worker.
 * ------------------------------------------------------------------ */
declare global {
  interface Window {
    // Cầu nối cho kiểm thử e2e (thay cho việc import bundle Vite trước đây).
    __demoMsw?: unknown;
  }
}

let mswInitPromise: Promise<void> | null = null;

function initMockServiceWorker(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (mswInitPromise) return mswInitPromise;

  mswInitPromise = (async () => {
    try {
      const [browser, msw] = await Promise.all([
        import("../src/mocks/browser"),
        import("msw"),
      ]);
      await browser.worker.start({ onUnhandledRequest: "bypass", quiet: true });
      window.__demoMsw = {
        worker: browser.worker,
        http: msw.http,
        HttpResponse: msw.HttpResponse,
      };
    } catch (err: unknown) {
      const msg = (err as Error)?.message ?? "";
      // Nếu worker hoặc network interceptor đã được khởi động trước đó (Strict Mode / Fast Refresh)
      if (
        msg.includes("already enabled") ||
        msg.includes("cannot configure an already enabled network")
      ) {
        return;
      }
      mswInitPromise = null;
      throw err;
    }
  })();

  return mswInitPromise;
}

export default function Providers({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(isLive);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isLive) return;
    let cancelled = false;

    initMockServiceWorker()
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch((err) => {
        if (!cancelled) setError((err as Error).message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="grid min-h-dvh place-items-center bg-canvas px-6 text-center">
        <div className="max-w-md rounded-xl border border-danger/20 bg-danger/5 p-6 shadow-sm">
          <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-full bg-danger/10 text-danger">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="mb-2 text-base font-semibold text-slate-900 dark:text-white">Không khởi tạo được môi trường demo</h2>
          <p className="mb-4 text-xs text-muted leading-relaxed">{error}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 rounded-lg bg-navy px-4 py-2 text-xs font-medium text-white shadow transition hover:opacity-90 active:scale-95"
          >
            Tải lại trang
          </button>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="grid min-h-dvh place-items-center bg-canvas text-[13px] text-muted">
        Đang khởi tạo môi trường demo…
      </div>
    );
  }

  return (
    <ThemeProvider>
      <SessionProvider>
        <ToastProvider>{children}</ToastProvider>
      </SessionProvider>
    </ThemeProvider>
  );
}

