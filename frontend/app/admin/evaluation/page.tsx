"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip, Progress } from "@/components/ui";
import { DEMO_EVAL_RUNS } from "@/lib/mock/seed";
import { formatDateTime, formatNumber } from "@/lib/utils";

const METRIC_LABEL: Record<string, string> = {
  accuracy: "Độ chính xác",
  abstainRate: "Tỷ lệ từ chối kết luận",
  scopeMismatchRecall: "Bắt đúng ca lệch phạm vi",
  citationPrecision: "Độ chính xác trích dẫn",
};

export default function AdminEvaluationPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Đánh giá chất lượng</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Bộ kiểm thử vàng và so sánh giữa các phiên bản agent. Số liệu dưới đây là minh họa cho giai đoạn sau.
        </p>
      </header>

      {DEMO_EVAL_RUNS.map((run) => (
        <Card key={run.id}>
          <CardHeader>
            <div>
              <CardTitle>
                {run.id} · {run.agentVersion}
              </CardTitle>
              <p className="mt-1 text-[12px] text-muted-foreground">
                {run.goldSet} · {formatDateTime(run.createdAt)}
              </p>
            </div>
            {run.baseline ? <Chip tone="neutral">Đường cơ sở</Chip> : <Chip tone="ai">Ứng viên</Chip>}
          </CardHeader>
          <CardBody className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.entries(run.metrics).map(([key, value]) => (
                <div key={key}>
                  <div className="flex items-center justify-between text-[13px]">
                    <span className="text-muted-foreground">{METRIC_LABEL[key] ?? key}</span>
                    <span className="tabular text-foreground">{formatNumber(value * 100)}%</span>
                  </div>
                  <Progress className="mt-1" value={value * 100} tone={value >= 0.8 ? "support" : "caution"} />
                </div>
              ))}
            </div>

            <div className="overflow-x-auto border-t border-border pt-3">
              <p className="mb-2 text-[12px] uppercase tracking-wide text-muted-foreground">Ma trận nhầm lẫn (4 lớp)</p>
              <table className="min-w-[320px] text-left text-[12px]">
                <tbody>
                  {run.confusion.map((row, rowIndex) => (
                    <tr key={`row-${rowIndex}`}>
                      {row.map((cell, cellIndex) => (
                        <td
                          key={`cell-${rowIndex}-${cellIndex}`}
                          className="border border-border px-3 py-1.5 tabular"
                          style={{ background: cell > 3 ? "hsl(var(--support-soft))" : undefined }}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      ))}

      <Card>
        <CardBody className="space-y-1.5 text-[13px] text-muted-foreground">
          <p>Chỉ số quan trọng nhất là tỷ lệ từ chối kết luận đúng: hệ thống phải chọn “thiếu bằng chứng” khi thật sự thiếu.</p>
          <p className="text-caution-fg">Chưa có pipeline đánh giá tự động trong MVP; đây là thiết kế màn hình và dữ liệu mẫu.</p>
        </CardBody>
      </Card>
    </div>
  );
}
