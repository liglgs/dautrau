import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
export function useApi<T>(path: string, poll = false) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const active = useRef(true);
  const load = useCallback(async () => {
    try {
      const result = await api<T>(path);
      if (active.current) {
        setData(result);
        setError("");
      }
    } catch (e) {
      if (active.current) setError((e as Error).message);
    }
  }, [path]);
  useEffect(() => {
    active.current = true;
    void load();
    const interval = poll ? window.setInterval(load, 3000) : undefined;
    return () => {
      active.current = false;
      clearInterval(interval);
    };
  }, [load, poll]);
  return { data, error, load };
}
// An uncertain network result retains its request body/key until retried.
export function useMutation() {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [uncertain, setUncertain] = useState(false);
  const pending = useRef<{
    path: string;
    body: unknown;
    method?: string;
    key: string;
  } | null>(null);
  const lock = useRef(false);
  const run = async <T>(
    path: string,
    body: unknown,
    method?: string,
  ): Promise<T | undefined> => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    if (
      pending.current &&
      (pending.current.path !== path || pending.current.method !== method)
    ) {
      setError(
        "Thao tác trước chưa rõ kết quả. Hãy thử lại chính thao tác đó trước.",
      );
      setBusy(false);
      lock.current = false;
      return;
    }
    const req = pending.current ?? {
      path,
      body,
      method,
      key: crypto.randomUUID(),
    };
    pending.current = req;
    try {
      const result = await api<T>(req.path, req.body, {
        method: req.method,
        key: req.key,
      });
      pending.current = null;
      setUncertain(false);
      return result;
    } catch (e) {
      setError((e as Error).message);
      const unknown =
        e instanceof ApiError && (e.status === 0 || e.status >= 500);
      setUncertain(unknown);
      if (!unknown) pending.current = null;
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return { run, error, busy, uncertain };
}
