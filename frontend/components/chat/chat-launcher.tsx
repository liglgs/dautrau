"use client";

import * as React from "react";
import { MessageSquare, Send, Sparkles, X } from "lucide-react";
import { Button, Textarea } from "@/components/ui";
import { useChatStore } from "@/lib/store/chat";
import { useInspector } from "@/lib/store/inspector";
import { useAppStore } from "@/lib/store/app-store";
import { hasGuardrailRisk, looksLikePatientIdentifier } from "@/lib/guardrails";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DEMO_EVIDENCE } from "@/lib/mock/seed";

const SUGGESTIONS = [
  "VigiLens khác gì một công cụ RAG thông thường?",
  "Vì sao kết luận “thiếu bằng chứng” lại hữu ích?",
  "Các bạn xử lý mâu thuẫn giữa hai nghiên cứu thế nào?",
];

/** Trợ lý VigiLens — hiện diện ở góc phải dưới, có ngữ cảnh theo trang đang mở. */
export function ChatLauncher() {
  const { open, setOpen, messages, push, context } = useChatStore();
  const [draft, setDraft] = React.useState("");
  const [thinking, setThinking] = React.useState(false);
  const openInspector = useInspector((state) => state.open);
  const role = useAppStore((state) => state.role);

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      kind: "text",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };
    push(userMessage);
    setDraft("");
    setThinking(true);
    setTimeout(() => {
      push(buildAssistantReply(trimmed, context.investigationId));
      setThinking(false);
    }, 620);
  };

  return (
    <>
      {open ? (
        <div className="fixed bottom-20 right-4 z-40 flex h-[min(640px,80vh)] w-[min(420px,92vw)] flex-col rounded-[var(--radius-overlay)] border border-border bg-popover hairline-shadow">
          <header className="flex items-center gap-2 border-b border-border px-4 py-3">
            <Sparkles className="h-4 w-4 text-ai" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-semibold text-foreground">Trợ lý VigiLens</p>
              <p className="truncate text-[11px] text-muted-foreground">
                {context.investigationId ? `Ngữ cảnh: ${context.investigationId}` : "Hỏi về sản phẩm, thuật ngữ hoặc cách đọc kết quả"}
              </p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Đóng trợ lý">
              <X className="h-4 w-4" aria-hidden />
            </Button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 ? (
              <div className="space-y-3">
                <p className="text-[13px] text-muted-foreground">
                  Trợ lý chỉ giải thích sản phẩm và cách đọc kết quả. Trợ lý <strong>không</strong> đưa khuyến cáo điều trị
                  và không tự duyệt hồ sơ.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {SUGGESTIONS.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => send(item)}
                      className="rounded-[var(--radius-chip)] border border-border px-2.5 py-1 text-left text-[12px] text-muted-foreground hover:bg-muted"
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {messages.map((message) => (
              <div key={message.id} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-[var(--radius-card)] border px-3 py-2 text-[13px] leading-relaxed",
                    message.role === "user" ? "border-border bg-muted text-foreground" : "border-ai-border bg-ai-soft/60 text-foreground",
                  )}
                >
                  {message.role === "assistant" ? (
                    <span className="mb-1 flex items-center gap-1 text-[11px] font-semibold text-ai-fg">
                      <Sparkles className="h-3 w-3" aria-hidden /> AI đề xuất
                    </span>
                  ) : null}
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.citations?.length ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {message.citations.map((citation) => (
                        <button
                          key={citation}
                          type="button"
                          onClick={() => {
                            const evidence = DEMO_EVIDENCE["INV-0007"]?.find((item) => item.label === citation);
                            if (evidence && context.investigationId) openInspector({ investigationId: context.investigationId, evidence });
                          }}
                          className="mono rounded-[var(--radius-control)] border border-ai-border bg-card px-1.5 text-[11px] text-ai-fg"
                        >
                          [{citation}]
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
            {thinking ? <p className="text-[12px] text-muted-foreground">Trợ lý đang soạn câu trả lời…</p> : null}
          </div>

          <footer className="border-t border-border px-3 py-3">
            <div className="flex items-end gap-2">
              <Textarea
                rows={2}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    send(draft);
                  }
                }}
                placeholder="Hỏi về sản phẩm, thuật ngữ, cách đọc kết quả…"
                aria-label="Nội dung câu hỏi"
              />
              <Button size="icon" onClick={() => send(draft)} aria-label="Gửi câu hỏi">
                <Send className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">Không nhập thông tin định danh bệnh nhân.</p>
            {looksLikePatientIdentifier(draft) ? (
              <p className="mt-1 text-[11px] text-caution-fg">Có thể bạn vừa nhập thông tin định danh — vui lòng xóa trước khi gửi.</p>
            ) : null}
          </footer>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="fixed bottom-4 right-4 z-40 inline-flex items-center gap-2 rounded-[var(--radius-chip)] border border-ai-border bg-ai-soft px-3.5 py-2.5 text-[13px] font-medium text-ai-fg hairline-shadow"
        aria-expanded={open}
      >
        <MessageSquare className="h-4 w-4" aria-hidden />
        {open ? "Đóng trợ lý" : role === "visitor" ? "Hỏi về VigiLens" : "Trợ lý VigiLens"}
      </button>
    </>
  );
}

function buildAssistantReply(question: string, investigationId: string | undefined): ChatMessage {
  const lower = question.toLowerCase();
  let content =
    "Mình là trợ lý của VigiLens, chỉ giải thích sản phẩm và cách đọc kết quả. Mình không đưa khuyến cáo điều trị và không tự duyệt hồ sơ — dược sĩ lâm sàng luôn là người quyết định cuối cùng.";
  const kind: ChatMessage["kind"] = "text";
  let citations: string[] | undefined;

  if (lower.includes("rag") || lower.includes("khác")) {
    content =
      "Khác biệt chính nằm ở ba điểm. Thứ nhất, agent phân rã nhận định thành từng thành phần kiểm chứng được (hoạt chất, biến cố, quần thể, liều, đường dùng, thời gian) rồi mới tìm. Thứ hai, khi thiếu dữ liệu agent tự đổi truy vấn hoặc đổi nguồn, và chủ động tìm bằng chứng phản bác. Thứ ba, khi chưa đủ căn cứ agent từ chối kết luận thay vì tóm tắt liều lĩnh.";
  } else if (lower.includes("thiếu bằng chứng") || lower.includes("từ chối")) {
    content =
      "“Thiếu bằng chứng — Agent từ chối kết luận” là một kết quả hợp lệ. Nó cho biết đã tìm ở đâu, đã thử cách nào, và còn thiếu thành phần nào. Nhờ vậy người đọc không bị đẩy sang một kết luận không có căn cứ.";
  } else if (lower.includes("mâu thuẫn") || lower.includes("đối chiếu")) {
    content =
      "Khi hai nguồn khác nhau, agent không gộp thành một câu kết luận. Hệ thống ghi nhận khác biệt theo từng trường (quần thể, liều, đường dùng, thời gian) và đưa ra để reviewer phân xử.";
    citations = ["E1", "E4"];
  } else if (lower.includes("an toàn") || lower.includes("nguy hiểm")) {
    content =
      "Màu trong VigiLens chỉ nói về nhận định: xanh là nhận định được bằng chứng ủng hộ, đỏ là bị phản bác. Màu không có nghĩa thuốc an toàn hay nguy hiểm.";
  } else if (investigationId) {
    content = `Với ${investigationId}, bạn xem Timeline để biết từng bước suy luận, Ma trận bằng chứng để đối chiếu lập trường và phạm vi, và tab Hồ sơ để đọc bản Markdown trước khi duyệt.`;
  }

  if (hasGuardrailRisk(content)) {
    return {
      id: `msg-${Date.now()}-a`,
      role: "assistant",
      kind: "refusal",
      content:
        "Mình không thể diễn đạt câu trả lời theo hướng khẳng định nhân quả hoặc kết luận về mức độ an toàn của thuốc. Bạn xem lại giúp mình câu hỏi nhé.",
      createdAt: new Date().toISOString(),
    };
  }

  return { id: `msg-${Date.now()}-a`, role: "assistant", kind, content, citations, createdAt: new Date().toISOString() };
}

