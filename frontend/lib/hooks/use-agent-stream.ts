"use client";

import * as React from "react";
import { getDataSource } from "@/lib/api";
import type { AgentEvent, AgentStep, EvidenceItem, Gap } from "@/lib/types";

interface StreamState {
  steps: AgentStep[];
  evidence: EvidenceItem[];
  gaps: Gap[];
  events: AgentEvent[];
  status: "idle" | "loading" | "streaming" | "done" | "error";
  error?: string;
}

/**
 * Hook theo dõi tiến trình điều tra.
 *
 * Chế độ mock: phát lại kịch bản có độ trễ để Timeline "chạy thật".
 * Chế độ api:  đọc `GET /events` một lần rồi phát lại dần cho dễ theo dõi; việc làm mới dữ liệu
 *              do `useTimeline`/`useInvestigation` lo (poll khi cuộc điều tra còn đang chạy).
 */
export function useAgentStream(investigationId: string | null, options: { speed?: number; autoStart?: boolean } = {}) {
  const { speed = 1, autoStart = true } = options;
  const [state, setState] = React.useState<StreamState>({
    steps: [],
    evidence: [],
    gaps: [],
    events: [],
    status: "idle",
  });
  const timers = React.useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = React.useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  const load = React.useCallback(async () => {
    if (!investigationId) return;
    setState((current) => ({ ...current, status: "loading" }));
    const source = getDataSource();
    try {
      const [timeline, evidence, gaps] = await Promise.all([
        source.getTimeline(investigationId),
        source.getEvidence(investigationId),
        source.getGaps(investigationId),
      ]);
      if (!autoStart) {
        setState({ steps: timeline.steps, evidence, gaps, events: timeline.events, status: "done" });
        return;
      }
      clearTimers();
      setState({ steps: [], evidence: [], gaps: [], events: [], status: "streaming" });
      timeline.steps.forEach((step, index) => {
        const timer = setTimeout(
          () => {
            setState((current) => ({
              ...current,
              steps: [...current.steps, step],
              evidence: evidence.filter((item) => item.foundAtStep == null || item.foundAtStep <= step.index),
              gaps: index === timeline.steps.length - 1 ? gaps : current.gaps,
              status: index === timeline.steps.length - 1 ? "done" : "streaming",
            }));
          },
          (index * 900) / speed,
        );
        timers.current.push(timer);
      });
      if (timeline.steps.length === 0) {
        setState({ steps: [], evidence, gaps, events: timeline.events, status: "done" });
      }
    } catch (error) {
      setState((current) => ({ ...current, status: "error", error: (error as Error).message }));
    }
  }, [investigationId, autoStart, speed, clearTimers]);

  React.useEffect(() => {
    void load();
    return () => clearTimers();
  }, [load, clearTimers]);

  return { ...state, reload: load };
}
