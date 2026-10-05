"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { CircleAlert, CircleCheck, Info, Sparkles } from "lucide-react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Input, Label, Textarea } from "@/components/ui";
import { ClaimChips, SourceChip } from "@/components/pv/badges";
import { useCreateInvestigation } from "@/lib/hooks/use-data";
import { SubmissionIdentity, validateClaim } from "@/lib/claim-form";
import { DATA_MODE } from "@/lib/api";
import type { SourceId } from "@/lib/types";
import { cn } from "@/lib/utils";

const SAMPLE_CLAIMS = [
  "Metformin gây nhiễm toan lactic ở bệnh nhân suy thận giai đoạn 3b dùng ≥2.000 mg/ngày.",
  "Telmisartan gây phù mạch ở người lớn.",
  "Warfarin gây xuất huyết nội sọ ở người trên 75 tuổi.",
];

export default function NewInvestigationPage() {
  const router = useRouter();
  const create = useCreateInvestigation();
  const [claimText, setClaimText] = React.useState("");
  const [drug, setDrug] = React.useState("");
  const [adverseEvent, setAdverseEvent] = React.useState("");
  const [population, setPopulation] = React.useState("");
  const [dose, setDose] = React.useState("");
  const [route, setRoute] = React.useState("");
  const [timeWindow, setTimeWindow] = React.useState("");
  const [sources, setSources] = React.useState<SourceId[]>(["pubmed", "dailymed", "faers"]);
  const identity = React.useRef(new SubmissionIdentity());
  const submitting = React.useRef(false);
  const [maxSteps, setMaxSteps] = React.useState(8);
  const [maxDocs, setMaxDocs] = React.useState(50);
  const [localError, setLocalError] = React.useState<string | null>(null);
  const hasDraft = Boolean(claimText || drug || adverseEvent || population || dose || route || timeWindow);
  React.useEffect(() => {
    if (!hasDraft) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasDraft]);

  const toggleSource = (source: SourceId) => {
    setSources((current) => (current.includes(source) ? current.filter((item) => item !== source) : [...current, source]));
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting.current) return;
    setLocalError(null);
    const text = claimText.trim() || `${drug.trim()} gây ${adverseEvent.trim()}${population.trim() ? ` ở ${population.trim()}` : ""}.`;
    if (!drug.trim() || !adverseEvent.trim()) {
      setLocalError("Cần ít nhất hoạt chất và biến cố để agent bắt đầu tìm bằng chứng.");
      return;
    }
    const input = {
        claimText: text,
        drug: drug.trim(),
        adverseEvent: adverseEvent.trim(),
        population: population.trim() || undefined,
        dose: dose.trim() || undefined,
        route: route.trim() || undefined,
        timeWindow: timeWindow.trim() || undefined,
        sources,
        maxSteps,
        maxDocs,
      };
    const error = validateClaim(input);
    if (error) { setLocalError(error); return; }
    submitting.current = true;
    create.mutate(
      { input, key: identity.current.forInput(input) },
      {
        onSuccess: (result) => router.push(`/app/investigations/${result.id}`),
        onError: (error) => setLocalError((error as Error).message),
        onSettled: () => { submitting.current = false; },
      },
    );
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Điều tra mới</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Mô tả nhận định cần kiểm chứng. Agent sẽ phân rã thành các thành phần kiểm chứng được trước khi tìm.
        </p>
      </header>

      {DATA_MODE === "mock" ? (
        <Alert tone="caution" title="Đang ở chế độ dữ liệu minh họa">
          Cuộc điều tra sẽ chạy trên dữ liệu mẫu, không gọi nguồn thật.
        </Alert>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>1 · Nhận định</CardTitle>
            </CardHeader>
            <CardBody className="space-y-3">
              <div>
                <Label htmlFor="claim">Câu nhận định cần kiểm chứng</Label>
                <Textarea
                  id="claim"
                  maxLength={5000}
                  rows={3}
                  value={claimText}
                  onChange={(event) => setClaimText(event.target.value)}
                  placeholder="Ví dụ: Metformin gây nhiễm toan lactic ở bệnh nhân suy thận giai đoạn 3b dùng ≥2.000 mg/ngày."
                />
                <p className="mt-1 text-[12px] text-muted-foreground">
                  Không nhập thông tin định danh bệnh nhân. Hệ thống chỉ nhận nhận định ở mức quần thể.
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {SAMPLE_CLAIMS.map((sample) => (
                  <button
                    key={sample}
                    type="button"
                    onClick={() => setClaimText(sample)}
                    className="rounded-[var(--radius-chip)] border border-border px-2.5 py-1 text-left text-[12px] text-muted-foreground hover:bg-muted"
                  >
                    {sample.slice(0, 46)}…
                  </button>
                ))}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2 · Thành phần kiểm chứng được</CardTitle>
            </CardHeader>
            <CardBody className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="drug">Hoạt chất *</Label>
                <Input id="drug" value={drug} onChange={(event) => setDrug(event.target.value)} placeholder="metformin" />
              </div>
              <div>
                <Label htmlFor="event">Biến cố bất lợi *</Label>
                <Input id="event" value={adverseEvent} onChange={(event) => setAdverseEvent(event.target.value)} placeholder="nhiễm toan lactic" />
              </div>
              <div>
                <Label htmlFor="population">Quần thể</Label>
                <Input id="population" value={population} onChange={(event) => setPopulation(event.target.value)} placeholder="suy thận giai đoạn 3b" />
              </div>
              <div>
                <Label htmlFor="dose">Liều</Label>
                <Input id="dose" value={dose} onChange={(event) => setDose(event.target.value)} placeholder="≥2.000 mg/ngày" />
              </div>
              <div>
                <Label htmlFor="route">Đường dùng</Label>
                <Input id="route" value={route} onChange={(event) => setRoute(event.target.value)} placeholder="đường uống" />
              </div>
              <div>
                <Label htmlFor="timeWindow">Cửa sổ thời gian</Label>
                <Input id="timeWindow" value={timeWindow} onChange={(event) => setTimeWindow(event.target.value)} placeholder="trong 90 ngày" />
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>3 · Nguồn dữ liệu</CardTitle>
            </CardHeader>
            <CardBody className="space-y-2">
              {(
                [
                  { id: "pubmed", label: "PubMed", note: "Y văn có bối cảnh phương pháp. Chất lượng thiết kế rất khác nhau." },
                  { id: "dailymed", label: "DailyMed", note: "Nhãn thuốc: cảnh báo, liều, chống chỉ định. Không phải bằng chứng dịch tễ." },
                  { id: "faers", label: "openFDA FAERS", note: "Báo cáo tự nguyện. Không có mẫu số, không suy ra tỷ lệ." },
                ] as const
              ).map((source) => {
                const active = sources.includes(source.id);
                return (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => toggleSource(source.id)}
                    disabled={create.isPending}
                    aria-pressed={active}
                    className={cn(
                      "flex w-full items-start gap-3 rounded-[var(--radius-card)] border px-4 py-3 text-left",
                      active ? "border-ai-border bg-ai-soft/50" : "border-border hover:bg-muted",
                    )}
                  >
                    <span className="mt-0.5">
                      {active ? <CircleCheck className="h-4 w-4 text-ai" aria-hidden /> : <span className="block h-4 w-4 rounded-full border border-border" aria-hidden />}
                    </span>
                    <span>
                      <span className="flex items-center gap-2 text-[14px] font-medium text-foreground">
                        <SourceChip source={source.id} /> {source.label}
                      </span>
                      <span className="mt-1 block text-[12px] text-muted-foreground">{source.note}</span>
                    </span>
                  </button>
                );
              })}
              <p className="text-[12px] text-muted-foreground">
                Chỉ có FAERS thì hệ thống không bao giờ kết luận “có bằng chứng ủng hộ”.
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>4 · Ngân sách</CardTitle>
            </CardHeader>
            <CardBody className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="maxSteps">Số bước tối đa ({maxSteps})</Label>
                <input
                  id="maxSteps"
                  disabled={create.isPending}
                  type="range"
                  min={2}
                  max={20}
                  value={maxSteps}
                  onChange={(event) => setMaxSteps(Number(event.target.value))}
                  className="mt-2 w-full accent-[hsl(var(--primary))]"
                />
                <p className="text-[12px] text-muted-foreground">Trần cứng của hệ thống là 20 bước.</p>
              </div>
              <div>
                <Label htmlFor="maxDocs">Số tài liệu tối đa ({maxDocs})</Label>
                <input
                  id="maxDocs"
                  disabled={create.isPending}
                  type="range"
                  min={5}
                  max={100}
                  step={5}
                  value={maxDocs}
                  onChange={(event) => setMaxDocs(Number(event.target.value))}
                  className="mt-2 w-full accent-[hsl(var(--primary))]"
                />
                <p className="text-[12px] text-muted-foreground">Trần cứng của hệ thống là 100 tài liệu.</p>
              </div>
            </CardBody>
          </Card>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle>Xem trước</CardTitle>
            </CardHeader>
            <CardBody className="space-y-3">
              <ClaimChips
                claim={{
                  drug: drug || "—",
                  adverseEvent: adverseEvent || "—",
                  population: population || undefined,
                  doseText: dose || undefined,
                  timeWindow: timeWindow || undefined,
                  rawText: claimText || undefined,
                }}
              />
              <div className="flex flex-wrap gap-1.5 border-t border-border pt-3">
                {sources.length ? sources.map((source) => <SourceChip key={source} source={source} />) : <span className="text-[12px] text-contradict-fg">Chưa chọn nguồn nào</span>}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardBody className="space-y-2 text-[13px] text-muted-foreground">
              <p className="flex items-start gap-2">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-ai" aria-hidden />
                Hệ thống luôn chạy một truy vấn phản bác trước khi kết luận “có bằng chứng ủng hộ”.
              </p>
              <p className="flex items-start gap-2">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-ai" aria-hidden />
                Agent dừng ở checkpoint; dược sĩ lâm sàng là người duyệt cuối cùng.
              </p>
              <p className="flex items-start gap-2">
                <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-caution" aria-hidden />
                Hệ thống không kết luận nhân quả và không tính tỷ lệ mắc.
              </p>
            </CardBody>
          </Card>

          {localError ? <Alert tone="contradict" title="Chưa gửi được">{localError}</Alert> : null}
          {create.isError ? <Alert tone="contradict" title="Lỗi từ máy chủ">{(create.error as Error).message}</Alert> : null}

          <Button type="submit" className="w-full" disabled={create.isPending}>
            <Sparkles className="h-4 w-4" aria-hidden />
            {create.isPending ? "Đang tạo…" : "Bắt đầu điều tra"}
          </Button>
          <p className="text-[12px] text-muted-foreground">
            Bạn có thể dừng ở bất kỳ checkpoint nào. Không có thao tác nào tự động duyệt hồ sơ.
          </p>
        </aside>
      </div>
    </form>
  );
}
