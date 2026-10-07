// @vitest-environment jsdom
import * as React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CaseworkError } from "@/components/casework/work-item-panels";
import { BackendError } from "@/lib/api/real";

describe("casework conflict recovery", () => {
  it("preserves the local draft path and exposes explicit reload/keep-mine choices", () => {
    const reload = vi.fn(); const keep = vi.fn();
    render(<CaseworkError error={new BackendError(409, "version_conflict", "conflict", { expected_version: 3, current_version: 4 })} onReload={reload} onKeepMine={keep} />);
    expect(screen.getByText(/So sánh: v3 và v4/i)).toBeTruthy();
    screen.getByRole("button", { name: "Tải bản mới" }).click(); screen.getByRole("button", { name: "Giữ nội dung tôi đang soạn" }).click();
    expect(reload).toHaveBeenCalledOnce(); expect(keep).toHaveBeenCalledOnce();
  });
});
