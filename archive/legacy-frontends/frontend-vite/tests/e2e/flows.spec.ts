import { test, expect, type Page } from "@playwright/test";
const time = "2026-09-01T08:00:00+07:00";
const manifest = {
  schema_version: "1.0",
  case_id: "UPLOAD-001",
  patient_id: "P-UPLOAD",
  encounter_id: "E-UPLOAD",
  reconciliation_at: time,
  initial_visible_at: time,
  documents: [
    {
      source_id: "U-S1",
      version: 1,
      kind: "medication_history",
      filename: "history.txt",
      author_role: "reviewer",
      event_time: null,
      recorded_at: time,
      available_at: time,
    },
  ],
};
async function login(page: Page, name = "Linh · Người rà soát") {
  await page.goto("/login");
  await page.getByRole("button", { name: `${name} →`, exact: true }).click();
  if (name.startsWith("Hà")) {
    await expect(
      page.getByRole("heading", { name: "Nhiệm vụ của tôi", exact: true }),
    ).toBeVisible();
    return;
  }
  // Đăng nhập của reviewer/clinician mở Bảng điều khiển; danh sách ca nằm ở mục "Danh sách ca".
  await expect(
    page.getByRole("heading", {
      name: "Bảng điều khiển Rà soát Thuốc Lâm sàng",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Danh sách ca", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hồ sơ cần rà soát", exact: true }),
  ).toBeVisible();
}
async function open(page: Page, id = "SIM-002") {
  await page.goto(`/cases/${id}`);
  await expect(
    page.getByRole("heading", { name: `Ca ${id}`, exact: true }),
  ).toBeVisible();
}
async function confirmClose(page: Page) {
  await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Lý do", { exact: true })
    .fill("Đã kiểm tra thông tin theo nguồn mô phỏng.");
  await dialog.getByRole("checkbox").first().check();
  await dialog.getByRole("button", { name: "Lưu xác nhận" }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: "Đóng vấn đề", exact: true }).click();
  await expect(page.getByText("Đã đóng", { exact: true })).toBeVisible();
}
async function approve(page: Page) {
  await page.getByRole("link", { name: "Xem tổng hợp →" }).click();
  await page.getByRole("button", { name: "Tạo bản nháp" }).click();
  await page
    .getByRole("button", { name: "Duyệt phiên bản", exact: true })
    .click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Xác nhận duyệt" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByText("Đã duyệt", { exact: true })).toBeVisible();
}

test("T02 · nhập file thật, lỗi thiếu file, lưu qua reload và không bịa extraction", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("button", { name: "+ Nhập hồ sơ mô phỏng" }).click();
  await page
    .getByLabel("Manifest JSON")
    .setInputFiles({
      name: "case.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(manifest)),
    });
  await page.getByRole("button", { name: "Kiểm tra gói" }).click();
  await expect(page.getByRole("alert")).toContainText("Thiếu tệp history.txt");
  await page
    .getByLabel("Nguồn TXT")
    .setInputFiles({
      name: "history.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Tiếng Việt 🧪 chưa rõ liều."),
    });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Kiểm tra gói" }).click();
  await page.getByRole("button", { name: "Nhập hồ sơ", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ca UPLOAD-001" }),
  ).toBeVisible();
  await expect(page.getByText(/Đã nhập 1 nguồn/)).toBeVisible();
  await page.reload();
  await expect(page.getByText(/Chưa trích xuất/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Chạy kịch bản mẫu" }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "Nguồn", exact: true }).click();
  await page.getByRole("button", { name: "history.txt · v1" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Tiếng Việt 🧪 chưa rõ liều.",
  );
});
test("T03/T11 · nguồn Unicode, focus và giao diện 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await open(page);
  const source = page
    .getByRole("button", { name: "↗ SIM-002-S1", exact: true })
    .first();
  await source.click();
  await expect(page.getByRole("dialog").locator("mark")).toContainText(
    "tiếng Việt 🧪",
  );
  await page.keyboard.press("Tab");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(source).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
test("T04/T05 · chạy mẫu, responder trả lời và không tự đóng", async ({
  page,
}) => {
  await login(page);
  await open(page);
  await page.getByRole("button", { name: "Chạy kịch bản mẫu" }).click();
  await expect(page.getByText("Chờ phản hồi", { exact: true })).toBeVisible();
  await login(page, "Hà · Người phản hồi");
  await expect(
    page.getByRole("link", { name: "Danh sách ca", exact: false }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Mở nhiệm vụ" }).click();
  await expect(
    page.getByRole("button", { name: "Gửi phản hồi" }),
  ).toBeDisabled();
  await page
    .getByLabel("Phản hồi", { exact: true })
    .fill("Chưa xác minh được, cần thêm thông tin.");
  await page.getByRole("button", { name: "Gửi phản hồi" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Đã lưu phản hồi; kết quả sẽ được rà soát",
  );
  await page.getByRole("button", { name: "Đóng panel" }).click();
  await login(page);
  await open(page);
  await expect(page.getByText("Chờ rà soát", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Đóng vấn đề" }),
  ).toBeDisabled();
});
test("T06/T08 · xác nhận có nguồn, reviewer bị chặn duyệt, clinician duyệt", async ({
  page,
}) => {
  await login(page);
  await open(page);
  await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Lưu xác nhận" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Đóng panel" }).click();
  await confirmClose(page);
  await page.getByRole("link", { name: "Xem tổng hợp →" }).click();
  await page.getByRole("button", { name: "Tạo bản nháp" }).click();
  await expect(
    page.getByRole("button", { name: "Duyệt phiên bản", exact: true }),
  ).toBeDisabled();
  await login(page, "Minh · Bác sĩ duyệt");
  await open(page);
  await approve(page);
});
test("T07 · bàn giao cần đúng người nhận, không tính resolved", async ({
  page,
}) => {
  await login(page);
  await open(page);
  await page.getByRole("button", { name: "Bàn giao", exact: true }).click();
  await page
    .getByLabel("Lý do", { exact: true })
    .fill("Cần bác sĩ làm rõ thông tin.");
  await page.getByRole("button", { name: "Gửi đề nghị bàn giao" }).click();
  await page.getByRole("link", { name: "Mở nhiệm vụ và bàn giao →" }).click();
  await expect(page.getByText("Đang chờ nhận bàn giao")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Nhận bàn giao", exact: true }),
  ).toHaveCount(0);
  await login(page, "An · Bác sĩ nhận bàn giao");
  // Mục điều hướng tới trang nhiệm vụ nay có nhãn "Nhiệm vụ xác minh".
  await page.getByRole("link", { name: /Nhiệm vụ xác minh/ }).click();
  await page
    .getByRole("button", { name: "Nhận bàn giao", exact: true })
    .click();
  await expect(
    page.getByText("Đã nhận bàn giao · Chưa thể kết luận"),
  ).toBeVisible();
  await open(page);
  await expect(
    page
      .locator(".stat")
      .filter({ hasText: /^ĐÃ GIẢI QUYẾT/ })
      .locator("strong"),
  ).toHaveText("0");
  await approve(page);
  await expect(
    page.getByText("Đã duyệt — còn việc chưa giải quyết"),
  ).toBeVisible();
});
test("T09 · nguồn mới giữ nguyên snapshot cũ qua reload", async ({ page }) => {
  await login(page, "Minh · Bác sĩ duyệt");
  await open(page, "SIM-003");
  await confirmClose(page);
  await approve(page);
  const old = await page.getByTestId("review-snapshot").innerText();
  await page.getByRole("link", { name: "← Về đối chiếu" }).click();
  await page
    .getByRole("button", { name: "Phát nguồn mới mẫu sau duyệt" })
    .click();
  await expect(page.getByText(/Có thông tin mới; cần rà lại/)).toBeVisible();
  await page.getByRole("link", { name: "Xem tổng hợp →" }).click();
  await page
    .getByRole("combobox", { name: "Phiên bản", exact: true })
    .selectOption({ index: 0 });
  expect(await page.getByTestId("review-snapshot").innerText()).toBe(old);
  await page.reload();
  await page
    .getByRole("combobox", { name: "Phiên bản", exact: true })
    .selectOption({ index: 0 });
  expect(await page.getByTestId("review-snapshot").innerText()).toBe(old);
});
test("T08 · thay đổi revision khi đang mở modal duyệt bị từ chối", async ({
  page,
}) => {
  await login(page, "Minh · Bác sĩ duyệt");
  await open(page, "SIM-001");
  await page.getByRole("link", { name: "Xem tổng hợp →" }).click();
  await page.getByRole("button", { name: "Tạo bản nháp" }).click();
  await page
    .getByRole("button", { name: "Duyệt phiên bản", exact: true })
    .click();
  await page.evaluate(async () => {
    const headers = {
      "X-Demo-User": "clinician",
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    };
    const c = await (await fetch("/api/v1/cases/SIM-001", { headers })).json();
    await fetch("/api/v1/cases/SIM-001/assertions/SIM-001-A1", {
      method: "PATCH",
      headers,
      body: JSON.stringify({
        expected_revision: c.revision,
        name: "Thuốc B đã rà",
        evidence_ids: ["SIM-001-E1"],
      }),
    });
  });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Xác nhận duyệt" }).click();
  await expect(page.getByRole("alert")).toContainText("Hồ sơ đã thay đổi");
});
test("T04 · gửi trùng cùng khóa trả cùng receipt, chỉ tạo một nguồn", async ({
  page,
}) => {
  await login(page);
  await open(page);
  await page.getByRole("button", { name: "Chạy kịch bản mẫu" }).click();
  await expect(page.getByText("Chờ phản hồi", { exact: true })).toBeVisible();
  const result = await page.evaluate(async () => {
    const headers = {
      "X-Demo-User": "responder",
      "Content-Type": "application/json",
      "Idempotency-Key": "same-response",
    };
    const tasks = await (await fetch("/api/v1/tasks", { headers })).json();
    const request = {
      method: "POST",
      headers,
      body: JSON.stringify({
        expected_revision: tasks[0].revision,
        response: "Chưa rõ.",
      }),
    };
    const a = await (
      await fetch(`/api/v1/tasks/${tasks[0].id}/responses`, request)
    ).json();
    const b = await (
      await fetch(`/api/v1/tasks/${tasks[0].id}/responses`, request)
    ).json();
    const c = await (
      await fetch("/api/v1/cases/SIM-002", {
        headers: { "X-Demo-User": "reviewer" },
      })
    ).json();
    return {
      a: a.receipt,
      b: b.receipt,
      count: c.sources.filter(
        (s: { kind: string }) => s.kind === "verification_response",
      ).length,
    };
  });
  expect(result.a).toBe(result.b);
  expect(result.count).toBe(1);
});
test("T10 · lỗi API có retry, polling không mất form", async ({ page }) => {
  await login(page);
  await open(page);
  await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await page.getByLabel("Lý do", { exact: true }).fill("Nội dung đang gõ");
  await page.waitForTimeout(3300);
  await expect(
    page.getByRole("textbox", { name: "Lý do", exact: true }),
  ).toHaveValue("Nội dung đang gõ");
  await page.getByRole("button", { name: "Đóng panel" }).click();
  // MSW owns the request boundary. Override it inside the browser for this test only.
  await page.evaluate(async () => {
    const browserPath = "/src/mocks/browser.ts",
      mswPath = "/node_modules/.vite/deps/msw.js";
    const { worker } = await import(/* @vite-ignore */ browserPath);
    const { http, HttpResponse } = await import(/* @vite-ignore */ mswPath);
    worker.use(
      http.get(
        "/api/v1/cases/SIM-002/evidence/:id",
        () =>
          HttpResponse.json(
            {
              message: "Dịch vụ nguồn tạm lỗi",
              code: "UNAVAILABLE",
              retryable: true,
            },
            { status: 503 },
          ),
      ),
    );
  });
  await page
    .getByRole("button", { name: "↗ SIM-002-S1", exact: true })
    .first()
    .click();
  await expect(page.getByRole("alert")).toContainText("Dịch vụ nguồn tạm lỗi");
  await page.evaluate(async () => {
    const browserPath = "/src/mocks/browser.ts";
    const { worker } = await import(/* @vite-ignore */ browserPath);
    worker.resetHandlers();
  });
  await page.getByRole("button", { name: "Thử lại" }).click();
  await expect(page.getByRole("dialog").locator("mark")).toContainText(
    "tiếng Việt 🧪",
  );
});
