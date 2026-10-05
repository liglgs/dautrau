import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Button } from "@/components/ui";

describe("Button", () => {
  it("mặc định type=button để nút nằm trong biểu mẫu không vô tình gửi biểu mẫu", () => {
    // Lỗi thật: nút "Tạo phiên bản mới" trong cảnh báo 409 nằm trong <form> nạp tài liệu;
    // thiếu type mặc định nên một cú nhấp gửi biểu mẫu và sinh phiên bản mới ngoài ý muốn.
    const markup = renderToStaticMarkup(<Button>Nhấn</Button>);
    expect(markup).toContain('type="button"');
  });

  it("tôn trọng type do nơi gọi đặt", () => {
    expect(renderToStaticMarkup(<Button type="submit">Gửi</Button>)).toContain('type="submit"');
  });
});
