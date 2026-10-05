"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useSession } from "./providers";

export default function HomeRedirect() {
  const router = useRouter();
  const { user, hydrated } = useSession();

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    router.replace(user.role === "responder" ? "/tasks" : "/dashboard");
  }, [hydrated, user, router]);

  return (
    <div className="grid min-h-dvh place-items-center bg-canvas text-[13px] text-muted">
      Đang mở không gian làm việc…
    </div>
  );
}
