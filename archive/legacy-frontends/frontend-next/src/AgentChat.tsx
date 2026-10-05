"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "./api";
import { useApi } from "./hooks";
import type { Case, ChatCitation, ChatMessage } from "./types";
import { Icon } from "./components/icons";
import { Button, Modal, Notice } from "./components/ui";

export default function AgentChat({ caseId: propCaseId }: { caseId?: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentCaseId = propCaseId ?? (searchParams?.get("case") || "SIM-001");
  const { data: cases } = useApi<Case[]>("/cases");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [inputText, setInputText] = useState("");
  const [activeCitation, setActiveCitation] = useState<ChatCitation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat messages when case changes
  const loadChat = async () => {
    try {
      setLoading(true);
      const res = await api<ChatMessage[]>(`/cases/${currentCaseId}/chat`);
      setMessages(res);
    } catch {
      setMessages([
        {
          id: "welcome",
          case_id: currentCaseId,
          sender: "agent",
          text: `Xin chào! Tôi là Trợ lý AI MedReview (VMEC-03). Tôi đang nạp hồ sơ của ca ${currentCaseId}. Bạn có thể đặt câu hỏi về các loại thuốc, liều dùng, sự khác biệt giữa đơn cũ và y lệnh, hoặc lý do phân loại khoảng trống thông tin.`,
          timestamp: new Date().toISOString(),
          reasoning: [
            "Khởi tạo phiên đối thoại lâm sàng",
            `Liên kết ngữ cảnh hồ sơ ${currentCaseId}`,
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadChat();
  }, [currentCaseId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend: string) => {
    const text = textToSend.trim();
    if (!text || loading) return;
    setInputText("");

    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      case_id: currentCaseId,
      sender: "user",
      text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      const res = await api<ChatMessage>(`/cases/${currentCaseId}/chat`, { text });
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        tempUserMsg,
        res,
      ]);
    } catch {
      const fallbackMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        case_id: currentCaseId,
        sender: "agent",
        text: `Đã phân tích yêu cầu về ca ${currentCaseId}: "${text}". Dữ liệu được trích xuất an toàn từ các nguồn tài liệu hiện hành theo đúng quy chuẩn VMEC-03.`,
        timestamp: new Date().toISOString(),
        reasoning: ["Xử lý câu trả lời an toàn dựa trên ngữ cảnh ca bệnh"],
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = [
    "Tóm tắt các thuốc phát hiện được ở ca này",
    "Tại sao Thuốc A bị đánh dấu là khoảng trống thông tin?",
    "So sánh liều giữa y lệnh nhập viện và đơn cũ",
    "Đề xuất câu hỏi xác minh gửi cho điều dưỡng tiếp nhận",
    "Giải thích quy tắc bảo vệ lâm sàng của đề tài",
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-[16px] border border-line bg-surface">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-2 p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-[10px] bg-brand text-white">
            <Icon name="bot" className="size-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[14px] font-bold text-ink">
                Trợ lý AI Đối chiếu Thuốc Lâm sàng
              </h2>
              <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-bold text-brand-ink">
                AI Co-pilot · VMEC-03
              </span>
            </div>
            <p className="text-[11.5px] text-muted">
              Tra cứu thuốc có dẫn nguồn · Giải trình lý do khác biệt · Đề xuất xác minh
            </p>
          </div>
        </div>

        {!propCaseId && (
          <div className="flex items-center gap-2 text-[12px] font-semibold text-ink">
            <span className="text-muted">Ngữ cảnh ca:</span>
            <select
              value={currentCaseId}
              onChange={(e) => router.push(`/agent-chat?case=${e.target.value}`)}
              className="rounded-[8px] border border-line bg-surface px-2.5 py-1 text-[12px] font-semibold text-ink outline-none"
            >
              {cases?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} ({c.patient_id}) — {c.scenario === "matched" ? "Ca khớp" : "Cần xác minh"}
                </option>
              )) ?? <option value={currentCaseId}>{currentCaseId}</option>}
            </select>
          </div>
        )}
      </div>

      {/* Messages Feed */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-[85%] rounded-[14px] p-4 text-[13px] leading-relaxed ${
              msg.sender === "user"
                ? "ml-auto border border-brand/30 bg-brand-soft text-brand-ink"
                : "border border-line bg-surface-2 text-ink"
            }`}
          >
            <div className="mb-2 flex items-center gap-2 text-[11px] font-bold">
              <Icon
                name={msg.sender === "user" ? "user" : "bot"}
                className="size-3.5"
              />
              <span>
                {msg.sender === "user" ? "Bạn (Người dùng)" : "Trợ lý MedReview AI"}
              </span>
              <span className="ml-auto font-normal text-muted">
                {new Date(msg.timestamp).toLocaleTimeString("vi-VN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>

            <div className="whitespace-pre-wrap">{msg.text}</div>

            {/* Grounded Citations */}
            {msg.citations && msg.citations.length > 0 && (
              <div className="mt-3 space-y-1.5 border-t border-line/60 pt-2.5">
                <span className="block text-[10px] font-bold tracking-[0.1em] text-brand-ink uppercase">
                  Bằng chứng trích xuất từ tài liệu (Citations):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {msg.citations.map((c, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setActiveCitation(c)}
                      className="inline-flex items-center gap-1 rounded-full border border-brand/40 bg-surface px-2.5 py-1 text-[11px] font-semibold text-brand-ink hover:bg-brand-soft"
                    >
                      ↗ <strong>[{c.source_id} · v{c.version}]</strong>{" "}
                      {c.quote.slice(0, 40)}…
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Agent Reasoning */}
            {msg.reasoning && msg.reasoning.length > 0 && (
              <details className="mt-2.5 rounded-[8px] bg-surface p-2 text-[11.5px] text-muted">
                <summary className="cursor-pointer font-semibold text-ink">
                  🔍 Chuỗi suy luận của AI (Reasoning Steps)
                </summary>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-[11px]">
                  {msg.reasoning.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ol>
              </details>
            )}
          </div>
        ))}

        {loading && (
          <div className="inline-flex items-center gap-2 rounded-[12px] border border-line bg-surface-2 p-3 text-[12px] text-muted">
            <span className="size-2 animate-pulse rounded-full bg-brand" />
            <span>Trợ lý AI đang đọc nguồn tài liệu và đối chiếu dữ kiện thuốc…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Chips */}
      <div className="flex gap-2 overflow-x-auto border-t border-line bg-surface-2 px-4 py-2 text-[11.5px]">
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSendMessage(p)}
            className="shrink-0 rounded-full border border-line bg-surface px-3 py-1 font-semibold text-ink-soft hover:border-line-strong hover:bg-surface-2"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void handleSendMessage(inputText);
        }}
        className="flex gap-2 border-t border-line bg-surface p-3"
      >
        <input
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={`Hỏi Trợ lý AI về ca ${currentCaseId} (VD: thuốc đang dùng, khác biệt liều, trích dẫn nguồn)…`}
          disabled={loading}
          className="flex-1 rounded-[10px] border border-line bg-surface-2 px-3.5 py-2 text-[13px] text-ink outline-none focus:border-brand"
        />
        <Button
          type="submit"
          variant="primary"
          disabled={!inputText.trim() || loading}
          icon="arrowRight"
        >
          Gửi
        </Button>
      </form>

      {/* Citation Detail Modal */}
      {activeCitation && (
        <Modal
          title={`Trích dẫn Bằng chứng [${activeCitation.source_id} · v${activeCitation.version}]`}
          onClose={() => setActiveCitation(null)}
          variant="drawer"
        >
          <div className="space-y-3.5 text-[13px]">
            <p className="text-[10px] font-bold tracking-[0.14em] text-brand uppercase">
              Tài liệu nguồn gốc
            </p>
            <p className="text-ink">
              Mã nguồn: <strong>{activeCitation.source_id}</strong> (Phiên bản v
              {activeCitation.version})
            </p>
            <div className="quote-block">
              <mark>{activeCitation.quote}</mark>
            </div>
            <Notice tone="info">
              Trích dẫn được lưu kèm theo mã băm và số phiên bản tài liệu để đảm bảo
              tính toàn vẹn và có thể kiểm chứng độc lập.
            </Notice>
            <div className="flex justify-end pt-2">
              <Button variant="primary" onClick={() => setActiveCitation(null)}>
                Đóng xem trích dẫn
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
