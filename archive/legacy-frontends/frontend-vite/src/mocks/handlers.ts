import { http, HttpResponse, delay } from "msw";
import { mutate, readStore } from "./db";
import { dispatch, ServiceError } from "./service";
export const handlers = [
  http.all("/api/v1/*", async ({ request }) => {
    await delay(60);
    const path = new URL(request.url).pathname.replace("/api/v1", ""),
      userId = request.headers.get("X-Demo-User") ?? "",
      method = request.method;
    try {
      let body: unknown = {};
      if (method !== "GET") {
        if (
          request.headers.get("Content-Type")?.includes("multipart/form-data")
        ) {
          const form = await request.formData(),
            manifest = JSON.parse(String(form.get("manifest")));
          const files = await Promise.all(
            (form.getAll("files") as File[]).map(async (f) => ({
              name: f.name,
              text: new TextDecoder("utf-8", { fatal: true }).decode(
                await f.arrayBuffer(),
              ),
            })),
          );
          body = {
            manifest,
            files,
            expected_revision: Number(form.get("expected_revision")),
          };
        } else body = await request.json();
      }
      const result =
        method === "GET"
          ? dispatch(await readStore(), method, path, userId)
          : await mutate((state) => {
              const key = request.headers.get("Idempotency-Key");
              if (!key) throw new ServiceError(422, "Thiếu Idempotency-Key.");
              const receiptKey = `${userId}:${method}:${path}:${key}`,
                payload = JSON.stringify(body),
                old = state.receipts[receiptKey];
              if (old) {
                if (old.payload !== payload)
                  throw new ServiceError(
                    409,
                    "Khóa thao tác đã dùng cho nội dung khác.",
                  );
                return old.response;
              }
              const response = dispatch(state, method, path, userId, body);
              state.receipts[receiptKey] = {
                payload,
                response: structuredClone(response),
              };
              return response;
            });
      return new HttpResponse(JSON.stringify(result), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (e) {
      return HttpResponse.json(
        {
          code: e instanceof ServiceError ? e.code : "INVALID_REQUEST",
          message: (e as Error).message,
          request_id: crypto.randomUUID(),
          retryable: false,
        },
        { status: e instanceof ServiceError ? e.status : 422 },
      );
    }
  }),
];
