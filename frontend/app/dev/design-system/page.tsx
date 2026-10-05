"use client";

import * as React from "react";
import { notFound } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Chip, EmptyState, Input, Label, Progress, Select, Separator, Skeleton, Textarea, Tooltip } from "@/components/ui";
import { AssessmentBadge, CitationChip, CoverageGrid, HashChip, ReviewStateBadge, RunStatusPill, ScopeChip, SourceChip, StanceBadge } from "@/components/pv/badges";
import type { AssessmentStatus, Cov, RunStatus } from "@/lib/types";

const ASSESSMENTS: AssessmentStatus[] = ["supported_for_scope", "contradicted_for_scope", "insufficient_evidence", "scope_mismatch", "out_of_scope", "requires_human_review"];
const RUNS: RunStatus[] = ["queued", "running", "waiting_for_review", "completed", "failed", "interrupted"];
const COVERAGE: Record<string, Cov> = { drug: "verified", adverseEvent: "verified", population: "partial", dose: "missing", route: "not_specified", timeWindow: "partial" };

export default function DesignSystemPage() {
  const [value, setValue] = React.useState(45);

  // Trang chỉ dành cho phát triển: ở bản dựng production trả về 404 thay vì phơi ra công khai.
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return (
    <main className="mx-auto w-full max-w-[1100px] space-y-8 px-5 py-10">
      <header>
        <h1 className="font-display text-[30px] text-foreground">Hệ thống thiết kế VigiLens</h1>
        <p className="mt-2 max-w-[70ch] text-[15px] text-muted-foreground">
          Mọi trạng thái đều dùng màu + icon + chữ. Không có trạng thái nào chỉ phân biệt bằng màu. Trang này dùng để kiểm
          tra token, thành phần và tương phản.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Bảng màu & token</CardTitle>
        </CardHeader>
        <CardBody className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {["background", "foreground", "card", "muted", "border", "primary", "ai", "support", "contradict", "caution", "scope", "neutral"].map((token) => (
            <div key={token} className="rounded-[var(--radius-card)] border border-border p-3">
              <div className="h-10 rounded-[var(--radius-control)]" style={{ background: `hsl(var(--${token}))` }} />
              <p className="mono mt-2 text-[11px] text-muted-foreground">--{token}</p>
            </div>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nút</CardTitle>
        </CardHeader>
        <CardBody className="flex flex-wrap items-center gap-2">
          <Button>Chính</Button>
          <Button variant="secondary">Phụ</Button>
          <Button variant="outline">Viền</Button>
          <Button variant="ghost">Trong suốt</Button>
          <Button variant="danger">Nguy hiểm</Button>
          <Button size="sm">Nhỏ</Button>
          <Button size="lg">Lớn</Button>
          <Button disabled>Vô hiệu</Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nhãn nghiệp vụ</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {ASSESSMENTS.map((status) => (
              <AssessmentBadge key={status} status={status} size="md" />
            ))}
          </div>
          <Separator />
          <div className="flex flex-wrap gap-2">
            {RUNS.map((status) => (
              <RunStatusPill key={status} status={status} />
            ))}
            <ReviewStateBadge state="approved" />
            <ReviewStateBadge state="rejected" />
            <ReviewStateBadge state="needs_rereview" />
            <ReviewStateBadge state="not_reviewed" />
          </div>
          <Separator />
          <div className="flex flex-wrap gap-2">
            <StanceBadge stance="supporting" />
            <StanceBadge stance="contradicting" />
            <StanceBadge stance="uncertain" />
            <StanceBadge stance="background" />
            <ScopeChip scope="mismatched" diffs={[{ field: "dose", claim: "≥2.000 mg/ngày", evidence: "tối đa 1.000 mg/ngày" }]} />
            <SourceChip source="pubmed" />
            <SourceChip source="dailymed" />
            <SourceChip source="faers" />
            <CitationChip label="E3" />
            <HashChip hash="a1b2c3d4e5f6" status="verified" />
            <HashChip hash="9f8e7d6c5b4a" status="mismatch" />
          </div>
          <Separator />
          <CoverageGrid coverage={COVERAGE} />
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cảnh báo</CardTitle>
        </CardHeader>
        <CardBody className="grid gap-3 md:grid-cols-2">
          {(["ai", "support", "contradict", "caution", "scope", "neutral"] as const).map((tone) => (
            <Alert key={tone} tone={tone} title={`Mức ${tone}`}>
              Cảnh báo dùng thanh màu bên trái, không dùng nền đặc để giữ tương phản chữ.
            </Alert>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Biểu mẫu & trạng thái</CardTitle>
        </CardHeader>
        <CardBody className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <div>
              <Label htmlFor="ds-input">Ô nhập</Label>
              <Input id="ds-input" placeholder="Nhập nội dung…" />
            </div>
            <div>
              <Label htmlFor="ds-select">Chọn</Label>
              <Select id="ds-select">
                <option>Lựa chọn một</option>
                <option>Lựa chọn hai</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="ds-area">Vùng văn bản</Label>
              <Textarea id="ds-area" rows={3} placeholder="Nhập mô tả…" />
            </div>
          </div>
          <div className="space-y-3">
            <Progress value={value} />
            <input type="range" value={value} onChange={(event) => setValue(Number(event.target.value))} className="w-full" aria-label="Điều chỉnh tiến độ" />
            <div className="flex items-center gap-2">
              <Chip tone="ai">
                <Sparkles className="h-3 w-3" aria-hidden /> AI đề xuất
              </Chip>
              <Chip tone="caution">Chưa giới hạn</Chip>
              <Tooltip label="Chú thích hiện khi rê chuột">
                <span className="text-[13px] text-muted-foreground underline decoration-dotted">Có chú thích</span>
              </Tooltip>
            </div>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-6 w-56" />
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trạng thái rỗng</CardTitle>
        </CardHeader>
        <CardBody>
          <EmptyState title="Chưa có dữ liệu" description="Trạng thái rỗng luôn nói rõ vì sao trống và bước tiếp theo là gì." />
        </CardBody>
      </Card>
    </main>
  );
}
