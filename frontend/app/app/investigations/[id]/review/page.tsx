"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Input, Label, Select, Textarea } from "@/components/ui";
import { useEvidence, useInvestigation, useReviewAction } from "@/lib/hooks/use-data";
import { canReview, useAppStore } from "@/lib/store/app-store";
import { MIN_REVIEW_REASON } from "@/lib/review-rules";
import type { EvidenceItem, Investigation, ReviewAction } from "@/lib/types";

const ACTIONS = [
  ["approve", "Xác nhận checkpoint"], ["edit_claim", "Sửa nhận định / hoạt chất"],
  ["edit", "Sửa bằng chứng"], ["exclude_evidence", "Loại bằng chứng khỏi đánh giá"],
  ["request_more", "Yêu cầu tìm thêm"], ["reject", "Từ chối"],
] as const;

function evidenceForm(item?: EvidenceItem) {
  return {
    quote: item?.quotes[0]?.text ?? "",
    stance: item?.stance === "supporting" ? "supports" : item?.stance === "contradicting" ? "contradicts" : "uncertain",
    scope: { population: item?.scopeValues?.population ?? "", dose: item?.scopeValues?.dose ?? "",
      route: item?.scopeValues?.route ?? "", time_window: item?.scopeValues?.time_window ?? "" },
  };
}

export default function ReviewTabPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id ?? "");
  const state = useInvestigation(id);
  const evidence = useEvidence(id);
  const review = useReviewAction(id);
  const role = useAppStore((store) => store.role);
  const [viewed, setViewed] = React.useState<Investigation | null>(null);
  const [viewedEvidence, setViewedEvidence] = React.useState<EvidenceItem[]>([]);
  const [selected, setSelected] = React.useState<ReviewAction["action"]>("approve");
  const [target, setTarget] = React.useState("");
  const [quote, setQuote] = React.useState("");
  const [stance, setStance] = React.useState("uncertain");
  const [drug, setDrug] = React.useState("");
  const [event, setEvent] = React.useState("");
  const [scope, setScope] = React.useState({ population: "", dose: "", route: "", time_window: "" });
  const [reason, setReason] = React.useState("");
  const [result, setResult] = React.useState<{ ok: boolean; message: string; code?: string } | null>(null);
  const [refreshError, setRefreshError] = React.useState<string | null>(null);
  const [refreshing, setRefreshing] = React.useState(false);
  const refreshPending = React.useRef(false);
  const pending = React.useRef(false);
  const identity = React.useRef({ fingerprint: "", id: "" });

  React.useEffect(() => {
    if (!viewed && state.data && evidence.data && !state.error && !evidence.error) {
      setViewed(state.data);
      setViewedEvidence(evidence.data);
      setDrug(state.data.claim.drug);
      setEvent(state.data.claim.adverseEvent);
    }
  }, [viewed, state.data, state.error, evidence.data, evidence.error]);

  const refresh = async () => {
    if (refreshPending.current || pending.current) return;
    refreshPending.current = true;
    setRefreshing(true);
    setRefreshError(null);
    try {
      const updated = await state.refetch();
      if (!updated.data || updated.error) throw new Error("Không tải được phiên bản mới. Hãy thử lại.");
      const refreshedEvidence = await evidence.refetch();
      if (!refreshedEvidence.data || refreshedEvidence.error) {
        throw new Error("Không tải được bằng chứng mới. Phiên bản đang xem và nội dung đang sửa được giữ lại.");
      }
      // Evidence has no investigation-version field. Check state again before accepting it.
      const confirmed = await state.refetch();
      if (!confirmed.data || confirmed.error || confirmed.data.version !== updated.data.version) {
        throw new Error("Phiên bản đã thay đổi trong khi tải bằng chứng. Hãy tải lại trước khi gửi quyết định.");
      }
      const current = confirmed.data;
      setDrug((value) => value === viewed?.claim.drug ? current.claim.drug : value);
      setEvent((value) => value === viewed?.claim.adverseEvent ? current.claim.adverseEvent : value);
      const previousItem = viewedEvidence.find((item) => item.id === target);
      const nextItem = refreshedEvidence.data.find((item) => item.id === target);
      if (previousItem && nextItem) {
        const previousForm = evidenceForm(previousItem);
        const nextForm = evidenceForm(nextItem);
        setQuote((value) => value === previousForm.quote ? nextForm.quote : value);
        setStance((value) => value === previousForm.stance ? nextForm.stance : value);
        setScope((value) => ({
          population: value.population === previousForm.scope.population ? nextForm.scope.population : value.population,
          dose: value.dose === previousForm.scope.dose ? nextForm.scope.dose : value.dose,
          route: value.route === previousForm.scope.route ? nextForm.scope.route : value.route,
          time_window: value.time_window === previousForm.scope.time_window ? nextForm.scope.time_window : value.time_window,
        }));
      } else if (target && !nextItem) {
        setTarget("");
      }
      setViewedEvidence(refreshedEvidence.data);
      setViewed(current);
      setResult(null);
    } catch (error) {
      setRefreshError((error as Error).message);
    } finally {
      refreshPending.current = false;
      setRefreshing(false);
    }
  };
  const chooseEvidence = (value: string) => {
    setTarget(value);
    const form = evidenceForm(viewedEvidence.find((entry) => entry.id === value));
    setQuote(form.quote);
    setStance(form.stance);
    setScope(form.scope);
  };
  const stale = Boolean((viewed && state.data && viewed.version !== state.data.version) || result?.code === "version_conflict");
  const unavailable = refreshing || Boolean(refreshError) || evidence.isPending || evidence.isError || state.isError;
  const submit = () => {
    if (pending.current || refreshPending.current || !canReview(role) || !viewed || stale || unavailable) return;
    if (reason.trim().length < MIN_REVIEW_REASON) { setResult({ ok: false, message: `Ghi lý do ít nhất ${MIN_REVIEW_REASON} ký tự.` }); return; }
    if ((selected === "edit" || selected === "exclude_evidence") && !target) { setResult({ ok: false, message: "Chọn bằng chứng cần xử lý." }); return; }
    const checkpoint = (viewed.checkpoint as ReviewAction["checkpoint"]) ?? "assessment";
    const action: ReviewAction = { action: selected, reason: reason.trim(), expectedVersion: viewed.version, checkpoint,
      target: selected === "edit" || selected === "exclude_evidence" ? target : undefined,
      payload: selected === "edit" ? { quote, stance, scope: Object.fromEntries(Object.entries(scope).map(([key, value]) => [key, value.trim() || null])) }
        : selected === "edit_claim" ? { drug: drug.trim(), event: event.trim() } : {},
    };
    const fingerprint = JSON.stringify(action);
    if (identity.current.fingerprint !== fingerprint) identity.current = { fingerprint, id: crypto.randomUUID() };
    action.decisionId = identity.current.id;
    pending.current = true;
    review.mutate(action, {
      onSuccess: (response) => { setResult(response); if (response.ok) setReason(""); },
      onError: (error) => setResult({ ok: false, message: (error as Error).message }),
      onSettled: () => { pending.current = false; },
    });
  };

  if (!canReview(role)) return <Alert title="Chỉ người duyệt được gửi quyết định">Vai trò hiện tại chỉ xem được hồ sơ.</Alert>;
  return <Card>
    <CardHeader><CardTitle>Quyết định của người duyệt</CardTitle></CardHeader>
    <CardBody className="space-y-4">
      {state.error ? <Alert tone="contradict" title="Không tải được phiên bản">{state.error.message}</Alert> : null}
      {evidence.error ? <Alert tone="contradict" title="Không tải được bằng chứng">{evidence.error.message}</Alert> : null}
      {refreshError ? <Alert tone="contradict" title="Chưa tải đủ nội dung mới">{refreshError}</Alert> : null}
      <p>Phiên bản đang xem: {viewed ? `v${viewed.version}` : "đang tải…"} · Checkpoint: {viewed?.checkpoint ?? "không có"}</p>
      <p className="text-[13px] text-muted-foreground">Duyệt nhận định hoặc đánh giá chỉ xác nhận checkpoint đó. Hồ sơ cần được duyệt riêng trước khi xuất.</p>
      {stale ? <Alert tone="caution" title="Phiên bản đã thay đổi">Nội dung nhập được giữ lại. Tải phiên bản mới, đối chiếu lại bằng chứng rồi gửi quyết định.</Alert> : null}
      <Button variant="outline" onClick={() => void refresh()} disabled={refreshing || state.isFetching || review.isPending}>Tải phiên bản mới</Button>
      <div><Label htmlFor="review-action">Hành động</Label><Select id="review-action" value={selected} disabled={refreshing || review.isPending} onChange={(e) => setSelected(e.target.value as ReviewAction["action"])}>
        {ACTIONS.map(([key, label]) => <option key={key} value={key}>{label}{key === "approve" && viewed?.checkpoint ? ` (${viewed.checkpoint})` : ""}</option>)}
      </Select></div>
      {selected === "edit_claim" ? <div className="grid gap-3 sm:grid-cols-2">
        <div><Label htmlFor="review-drug">Hoạt chất</Label><Input id="review-drug" maxLength={200} value={drug} onChange={(e) => setDrug(e.target.value)} /></div>
        <div><Label htmlFor="review-event">Biến cố</Label><Input id="review-event" maxLength={200} value={event} onChange={(e) => setEvent(e.target.value)} /></div>
      </div> : null}
      {selected === "edit" || selected === "exclude_evidence" ? <div>
        <Label htmlFor="review-evidence">Bằng chứng</Label><Select id="review-evidence" value={target} disabled={refreshing || review.isPending} onChange={(e) => chooseEvidence(e.target.value)}>
          <option value="">Chọn bằng chứng</option>{viewedEvidence.map((item) => <option key={item.id} value={item.id}>{item.label} · {item.title}{item.excluded ? " (đã loại)" : ""}</option>)}
        </Select>
      </div> : null}
      {selected === "edit" ? <>
        <div><Label htmlFor="review-quote">Trích dẫn nguyên văn</Label><Textarea id="review-quote" maxLength={2000} value={quote} onChange={(e) => setQuote(e.target.value)} /></div>
        <div><Label htmlFor="review-stance">Hướng bằng chứng</Label><Select id="review-stance" value={stance} onChange={(e) => setStance(e.target.value)}>
          <option value="supports">Ủng hộ</option><option value="contradicts">Phản bác</option><option value="uncertain">Chưa rõ</option>
        </Select></div>
        <div className="grid gap-3 sm:grid-cols-2">{Object.entries(scope).map(([key, value]) => <div key={key}>
          <Label htmlFor={`review-${key}`}>{({ population: "Quần thể", dose: "Liều", route: "Đường dùng", time_window: "Cửa sổ thời gian" } as Record<string, string>)[key]} (trống = chưa rõ)</Label>
          <Input id={`review-${key}`} maxLength={key === "population" ? 200 : 120} value={value} onChange={(e) => setScope((current) => ({ ...current, [key]: e.target.value }))} />
        </div>)}</div>
      </> : null}
      <div><Label htmlFor="reason">Lý do (ít nhất {MIN_REVIEW_REASON} ký tự)</Label><Textarea id="reason" rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} /></div>
      {result ? <Alert tone={result.ok ? "support" : "contradict"} title={result.ok ? "Đã ghi nhận" : "Chưa thực hiện được"}>{result.message}</Alert> : null}
      <Button onClick={submit} disabled={review.isPending || !viewed || stale || unavailable || (selected === "approve" && !viewed.checkpoint)}>Gửi quyết định</Button>
    </CardBody>
  </Card>;
}
