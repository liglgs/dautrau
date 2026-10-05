"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";
import { Button, Card, CardBody, CardHeader, CardTitle, Textarea } from "@/components/ui";
import { useChatStore } from "@/lib/store/chat";
import { hasGuardrailRisk } from "@/lib/guardrails";

export default function AssistantPage() {
  const { messages, push, context, setContext } = useChatStore();
  const [draft, setDraft] = React.useState("");

  const send = () => {
    const text = draft.trim();
    if (!text) return;
    push({ id: `msg-${Date.now()}`, role: "user", kind: "text", content: text, createdAt: new Date().toISOString() });
    setDraft("");
    const blocked = hasGuardrailRisk(text);
    setTimeout(() => {
      push({
        id: `msg-${Date.now()}-a`,
        role: "assistant",
        kind: blocked ? "refusal" : "text",
        content: blocked
          ? "Câu hỏi này hướng tới khẳng định nhân quả hoặc kết luận về mức độ an toàn của thuốc. Mình chỉ giải thích sản phẩm và cách đọc kết quả, và luôn để kết luận chuyên môn cho dược sĩ lâm sàng."
          : "Mình là trợ lý của VigiLens. Mình giải thích cách hệ thống tìm bằng chứng, cách đọc từng trạng thái kết luận và cách đọc hồ sơ — mình không đưa khuyến cáo điều trị.",
        createdAt: new Date().toISOString(),
      });
    }, 500);
  };

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Trợ lý VigiLens</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Trợ lý chỉ giải thích sản phẩm và cách đọc kết quả. Trợ lý không đưa khuyến cáo điều trị và không tự duyệt hồ sơ.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Hội thoại</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setContext({})}>
              Xóa ngữ cảnh
            </Button>
          </CardHeader>
          <CardBody className="space-y-3">
            <div className="max-h-[420px] space-y-3 overflow-y-auto">
              {messages.length === 0 ? (
                <p className="text-[13px] text-muted-foreground">Chưa có tin nhắn nào. Hãy hỏi về sản phẩm hoặc cách đọc kết quả.</p>
              ) : (
                messages.map((message) => (
                  <div key={message.id} className={message.role === "user" ? "text-right" : ""}>
                    <div
                      className={
                        "inline-block max-w-[85%] rounded-[var(--radius-card)] border px-3 py-2 text-left text-[13px] leading-relaxed " +
                        (message.role === "user" ? "border-border bg-muted" : "border-ai-border bg-ai-soft/60")
                      }
                    >
                      {message.role === "assistant" ? (
                        <span className="mb-1 flex items-center gap-1 text-[11px] font-semibold text-ai-fg">
                          <Sparkles className="h-3 w-3" aria-hidden /> AI đề xuất
                        </span>
                      ) : null}
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="flex items-end gap-2 border-t border-border pt-3">
              <Textarea
                rows={2}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Hỏi về sản phẩm, thuật ngữ, cách đọc kết quả…"
                aria-label="Nội dung câu hỏi"
              />
              <Button onClick={send}>Gửi</Button>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ngữ cảnh đang gắn</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2 text-[13px] text-muted-foreground">
            <p>Cuộc điều tra: {context.investigationId ?? "chưa gắn"}</p>
            <p>
              Khi mở trợ lý từ một cuộc điều tra, trợ lý dùng ngữ cảnh đó để giải thích các bước và trạng thái, nhưng không
              bao giờ tự đưa ra kết luận thay agent hoặc thay người duyệt.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
