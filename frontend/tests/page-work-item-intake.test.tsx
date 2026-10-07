// @vitest-environment jsdom
import * as React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import NewWorkItemPage from "@/app/app/work-items/new/page";

const push = vi.fn();
const mutate = vi.fn((_input: unknown, options?: { onSuccess?: (item: { id: string }) => void }) => options?.onSuccess?.({ id: "CW-1" }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/hooks/use-casework", () => ({ useCreateIntake: () => ({ mutate, isPending: false, error: null }) }));

afterEach(() => { cleanup(); mutate.mockClear(); push.mockClear(); });

describe("work-item intake", () => {
  it("accepts a raw-only ADR narrative without forcing the minimum-four fields", async () => {
    const user = userEvent.setup(); render(<NewWorkItemPage />);
    await user.selectOptions(screen.getByLabelText("Loại yêu cầu"), "adr");
    await user.type(screen.getByLabelText("Mô tả nghi ngờ ADR"), "Người báo mô tả ban đỏ sau dùng thuốc.");
    await user.click(screen.getByRole("button", { name: "Lưu yêu cầu" }));
    expect(mutate).toHaveBeenCalledWith(expect.objectContaining({ input: expect.objectContaining({ kind: "adr", raw_text: "Người báo mô tả ban đỏ sau dùng thuốc." }) }), expect.anything());
    expect(push).toHaveBeenCalledWith("/app/work-items/CW-1/intake");
  });
});
