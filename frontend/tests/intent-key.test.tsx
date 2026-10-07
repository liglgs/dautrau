// @vitest-environment jsdom
import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useIntentKey } from "@/lib/hooks/use-intent-key";

function Probe() {
  const [value, setValue] = React.useState("one"); const intent = useIntentKey(value);
  return <><input aria-label="Nội dung" value={value} onChange={(event) => setValue(event.target.value)} /><output>{intent.key}</output><button onClick={intent.reset}>Thành công</button></>;
}

describe("stable intent keys", () => {
  it("reuses the retry key, then rotates only after content change or acknowledged success", async () => {
    const user = userEvent.setup(); render(<Probe />); const first = screen.getByRole("status").textContent;
    expect(screen.getByRole("status").textContent).toBe(first);
    await user.type(screen.getByLabelText("Nội dung"), "!"); const changed = screen.getByRole("status").textContent;
    expect(changed).not.toBe(first);
    await user.click(screen.getByRole("button", { name: "Thành công" }));
    expect(screen.getByRole("status").textContent).not.toBe(changed);
  });
});
