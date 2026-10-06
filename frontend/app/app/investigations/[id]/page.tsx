"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { RefreshCcw } from "lucide-react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Skeleton } from "@/components/ui";
import { AgentTimeline, GapList } from "@/components/pv/agent-timeline";
import { useCancelRun, useEvidence, useGaps, useInvestigation, useTimeline } from "@/lib/hooks/use-data";
import { useAgentStream } from "@/lib/hooks/use-agent-stream";
import { canRequestMore, useAppStore } from "@/lib/store/app-store";

export default function InvestigationOverviewPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id ?? "");
  const router = useRouter();
  const role = useAppStore((state) => state.role);
  const { data: investigation } = useInvestigation(id);
  const live = investigation?.runStatus === "running" || investigation?.runStatus === "queued";
  const { data: timeline, isLoading, error: timelineError, refetch } = useTimeline(id, live);
  const { data: evidence } = useEvidence(id);
  const { data: gaps } = useGaps(id);
  const stream = useAgentStream(id, { autoStart: true });

  const cancel = useCancelRun(id);
  const cancellable = investigation && ["queued", "running", "waiting_for_review", "interrupted"].includes(investigation.runStatus) && (role === "investigator" || role === "reviewer");
  const steps = timeline?.steps ?? [];
  const items = evidence ?? [];

  return (
    <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Tiến trình điều tra</CardTitle>
            <p className="mt-1 text-[12px] text-muted-foreground">
              Mỗi sự kiện ghi hành động, lý do ngắn, kết quả và trích dẫn đã lưu.
            </p>
          </div>
          <div className="flex items-center gap-1">
            {cancellable ? <Button variant="outline" size="sm" disabled={cancel.isPending} onClick={() => { if (window.confirm("Hủy cuộc điều tra này?")) cancel.mutate(); }}>{cancel.isPending ? "Đang hủy…" : "Hủy điều tra"}</Button> : null}
            <Button variant="ghost" size="sm" onClick={() => { void refetch(); void stream.reload(); }} disabled={stream.status === "loading"}>
              <RefreshCcw className="h-3.5 w-3.5" aria-hidden /> Tải lại
            </Button>
            <Button variant="ghost" size="sm" onClick={() => void stream.reload()} disabled={stream.status === "streaming"}>
              Phát lại
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          {cancel.data && !cancel.data.ok ? <Alert tone="caution" title="Chưa hủy được">{cancel.data.message}</Alert> : null}
          {cancel.error ? <Alert tone="caution" title="Chưa hủy được">{cancel.error.message}</Alert> : null}
          {timelineError ? <Alert tone="caution" title="Không làm mới được tiến trình">{timelineError.message} Các bước đã tải vẫn được giữ lại.</Alert> : null}
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            <AgentTimeline
              investigationId={id}
              steps={steps.length ? steps : stream.steps}
              evidence={items}
              playing={stream.status === "streaming"}
              onReplay={() => void stream.reload()}
            />
          )}
        </CardBody>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Khoảng trống dữ liệu</CardTitle>
          </CardHeader>
          <CardBody>
            <GapList
              gaps={gaps ?? []}
              canRequestMore={canRequestMore(role)}
              onRequestMore={() => router.push(`/app/investigations/${encodeURIComponent(id)}/review`)}
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vì sao dừng</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2 text-[13px] text-muted-foreground">
            <p>Lý do dừng do máy chủ ghi: {investigation?.stopReason ?? "Chưa ghi nhận"}</p>
            {Object.entries(investigation?.sourceStatus ?? {}).map(([source, status]) => <p key={source}>Nguồn {source}: {status === "error" ? "lỗi truy cập" : status === "empty" ? "không có kết quả" : status}</p>)}
            <p>
              Agent dừng khi bằng chứng bão hoà, khi hết ngân sách, hoặc khi gặp checkpoint bắt buộc người duyệt. Lý do dừng
              luôn hiện ở bước cuối của dòng suy luận.
            </p>
            <p>
              Trạng thái “Thiếu bằng chứng — Agent từ chối kết luận” là kết quả hợp lệ: hệ thống cho biết đã tìm ở đâu và
              còn thiếu gì thay vì đưa ra kết luận không có căn cứ.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
