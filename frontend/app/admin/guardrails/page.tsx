"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip, Input } from "@/components/ui";
import { CAUSAL_PATTERNS, ALLOWED_SCOPE_PHRASES, findCausalClaims } from "@/lib/guardrails";

const SAMPLES = [
  "Metformin gây nhiễm toan lactic ở bệnh nhân suy thận.",
  "Thuốc này an toàn cho mọi bệnh nhân.",
  "Có bằng chứng ủng hộ trong phạm vi: nhóm suy thận giai đoạn 3b dùng ≥2.000 mg/ngày.",
  "Không tìm thấy bằng chứng về liều cao hơn ở nhóm này.",
];

export default function AdminGuardrailsPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Guardrail ngôn ngữ</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Các mẫu câu khẳng định nhân quả hoặc kết luận an toàn bị chặn trước khi hiển thị.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Mẫu câu bị chặn</CardTitle>
            <Chip tone="contradict">{CAUSAL_PATTERNS.length} mẫu</Chip>
          </CardHeader>
          <CardBody>
            <ul className="space-y-1.5">
              {CAUSAL_PATTERNS.map((rule) => (
                <li key={rule.pattern.source} className="rounded-[var(--radius-control)] border border-border px-3 py-1.5">
                  <span className="mono block text-[12px] text-muted-foreground">{rule.pattern.source}</span>
                  <span className="mt-0.5 block text-[12px] text-caution-fg">{rule.reason}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cụm từ phạm vi được phép</CardTitle>
            <Chip tone="support">{ALLOWED_SCOPE_PHRASES.length} cụm</Chip>
          </CardHeader>
          <CardBody>
            <ul className="flex flex-wrap gap-1.5">
              {ALLOWED_SCOPE_PHRASES.map((phrase) => (
                <li key={phrase}>
                  <Chip tone="support">{phrase}</Chip>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Thử nhanh</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <Input
            defaultValue={SAMPLES[0]}
            aria-label="Câu cần kiểm tra"
            onChange={(event) => {
              const target = event.currentTarget.nextElementSibling as HTMLElement | null;
              if (target) {
                const hits = findCausalClaims(event.target.value);
                target.textContent = hits.length ? `Bị chặn: ${hits.join(", ")}` : "Không phát hiện mẫu câu bị chặn.";
              }
            }}
          />
          <p className="text-[13px] text-muted-foreground">Sửa câu trên để xem kết quả kiểm tra.</p>
          <div className="space-y-1.5 border-t border-border pt-3">
            {SAMPLES.map((sample) => {
              const hits = findCausalClaims(sample);
              return (
                <p key={sample} className="text-[13px]">
                  <span className={hits.length ? "text-contradict-fg" : "text-support-fg"}>{hits.length ? "Chặn" : "Cho qua"}</span>
                  <span className="text-muted-foreground"> — {sample}</span>
                </p>
              );
            })}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
