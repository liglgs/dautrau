// @vitest-environment jsdom
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import WorkItemsPage from "@/app/app/work-items/page";

vi.mock("@/lib/hooks/use-casework", () => ({ useWorkItems: () => ({ data: { items: [{ id: "CW/1", kind: "di", raw_text: "Câu hỏi", priority: "routine", version: 1, input_revision: 1, work_status: "accepted", run_status: "not_started", review_status: "pending", created_at: "2026-10-07T00:00:00Z" }] }, isLoading: false, error: null }) }));

describe("work-item list", () => {
  it("uses the normalized id in detail and reviewer queue links", () => {
    render(<WorkItemsPage />);
    const links = screen.getAllByRole("link", { name: /Câu hỏi/ });
    expect(links.some((link) => link.getAttribute("href") === "/app/work-items/CW%2F1")).toBe(true);
    expect(screen.getAllByRole("link", { name: /CW\/1.*Câu hỏi/ }).find((link) => link.getAttribute("href")?.endsWith("/review"))?.getAttribute("href")).toBe("/app/work-items/CW%2F1/review");
  });
});
