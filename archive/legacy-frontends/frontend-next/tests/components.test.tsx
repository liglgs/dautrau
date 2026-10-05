import { it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Badge, ErrorBox } from "../src/components/ui";
import { EvidenceChoices } from "../src/forms";
import { useState } from "react";
afterEach(cleanup);
it("trạng thái bằng chứng có nhãn rõ, không chỉ dùng màu", () => {
  render(<Badge value="inconclusive" />);
  expect(screen.getByText("Chưa thể kết luận")).toBeVisible();
});
it("các nhãn mới của dashboard và dispatch hiển thị đúng tiếng Việt", () => {
  render(<Badge value="urgent" />);
  expect(screen.getByText("Khẩn cấp")).toBeVisible();
  cleanup();
  render(<Badge value="online" />);
  expect(screen.getByText("Trực tuyến · Sẵn sàng")).toBeVisible();
});
it("lỗi có nút thử lại hoạt động", async () => {
  let count = 0;
  render(<ErrorBox message="Không tải được nguồn" retry={() => count++} />);
  await userEvent.click(screen.getByRole("button", { name: "Thử lại" }));
  expect(count).toBe(1);
  expect(screen.getByRole("alert")).toHaveTextContent("Không tải được nguồn");
});
it("chọn evidence độc lập từng nguồn", async () => {
  function Fixture() {
    const [ids, setIds] = useState<string[]>([]);
    return (
      <>
        <EvidenceChoices
          items={[
            {
              id: "E1",
              source_id: "S1",
              version: 1,
              quote: "Nguồn 🧪",
              context: "",
            },
          ]}
          ids={ids}
          setIds={setIds}
        />
        <output>{ids.join(",")}</output>
      </>
    );
  }
  render(<Fixture />);
  await userEvent.click(screen.getByRole("checkbox"));
  expect(screen.getByRole("status")).toHaveTextContent("E1");
  await userEvent.click(screen.getByRole("checkbox"));
  expect(screen.getByRole("status")).toBeEmptyDOMElement();
});
