"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { QuoteInspector } from "@/components/pv/quote-inspector";
import { RoleSwitcher } from "@/components/pv/role-switcher";
import { ChatLauncher } from "@/components/chat/chat-launcher";
import { useAppStore } from "@/lib/store/app-store";

export function Providers({ children }: { children: React.ReactNode }) {
  // Nạp lại vai trò đã lưu sau khi mount, tránh lệch cây DOM giữa máy chủ và trình duyệt.
  React.useEffect(() => {
    void useAppStore.persist.rehydrate();
  }, []);

  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 } },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        {children}
        <QuoteInspector />
        <ChatLauncher />
        <RoleSwitcher />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
