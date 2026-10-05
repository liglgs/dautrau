"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { CircleAlert, CircleCheck, Download, LoaderCircle } from "lucide-react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Chip, Skeleton } from "@/components/ui";
import { HashChip } from "@/components/pv/badges";
import { useDossier, useEvidence, useExportDossier } from "@/lib/hooks/use-data";
import { useInspector } from "@/lib/store/inspector";
import { safeSourceUrl } from "@/lib/evidence-view";
import { assertNoCausalClaim, GuardrailError } from "@/lib/guardrails";
import { downloadMarkdown } from "@/lib/utils";

export default function DossierTabPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id ?? "");
  const { data: dossier, isLoading, error } = useDossier(id);
  const exportDossier = useExportDossier(id);
  const { data: evidence } = useEvidence(id);
  const openInspector = useInspector((state) => state.open);
  const [message, setMessage] = React.useState<string | null>(null);

  const markdown = dossier?.markdown ?? "";
  const blockedByGuardrail = React.useMemo(() => {
    if (!markdown) return false;
    try {
      assertNoCausalClaim(markdown);
      return false;
    } catch (error) {
      return error instanceof GuardrailError;
    }
  }, [markdown]);

  const handleExport = () => {
    if (error || !dossier?.approved || dossier.validation?.ok === false || blockedByGuardrail || exportDossier.isPending) return;
    setMessage(null);
    exportDossier.mutate(undefined, {
      onSuccess: (result) => {
        if (!result.ok || !result.markdown) {
          setMessage(result.message ?? "Chưa xuất được hồ sơ.");
          return;
        }
        downloadMarkdown(result.markdown, `${id}-dossier.md`);
      },
      onError: (error) => setMessage((error as Error).message),
    });
  };

  if (isLoading) {
    return (
      <Card>
        <CardBody className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </CardBody>
      </Card>
    );
  }

  if (error && !dossier) return <Alert tone="contradict" title="Không tải được hồ sơ">{error.message}</Alert>;
  if (!markdown) {
    return (
      <Card>
        <CardBody className="space-y-2">
          <p className="text-[15px] text-foreground">Chưa có hồ sơ cho cuộc điều tra này</p>
          <p className="text-[13px] text-muted-foreground">
            Hồ sơ được tạo sau khi agent hoàn tất phần đánh giá. Sau đó hồ sơ phải được dược sĩ lâm sàng duyệt mới xuất được.
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.7fr_1fr]">
      {error ? <div className="xl:col-span-2"><Alert tone="caution" title="Không làm mới được hồ sơ">{error.message} Đang hiển thị bản đã tải trước đó; cần tải lại thành công trước khi xuất.</Alert></div> : null}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Hồ sơ Markdown</CardTitle>
            {error ? <Chip tone="caution">Chưa xác nhận trạng thái duyệt</Chip> : dossier?.approved ? (
              <Chip tone="support">
                <CircleCheck className="h-3 w-3" aria-hidden /> Đã duyệt
              </Chip>
            ) : (
              <Chip tone="caution">Chưa duyệt</Chip>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={Boolean(error) || exportDossier.isPending || !dossier?.approved || dossier.validation?.ok === false || blockedByGuardrail}>
            {exportDossier.isPending ? <LoaderCircle className="h-3.5 w-3.5 animate-spin-slow" aria-hidden /> : <Download className="h-3.5 w-3.5" aria-hidden />}
            Xuất .md
          </Button>
        </CardHeader>
        <CardBody>
          <article className="prose-vigilens max-w-none text-[15px] leading-[1.75] text-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]} components={{ a: ({ href, children }) => {
              if (href?.startsWith("#evidence-")) {
                let ref: string;
                try { ref = decodeURIComponent(href.slice("#evidence-".length)); } catch { return <span>{children}</span>; }
                const item = evidence?.find((entry) => entry.id === ref);
                return <button className="text-ai-fg underline" disabled={!item} onClick={() => { if (item) openInspector({ investigationId: id, evidence: item }); }}>{children}</button>;
              }
              const safe = safeSourceUrl(href);
              return safe ? <a href={safe} target="_blank" rel="noreferrer">{children}</a> : <span>{children}</span>;
            } }}>
              {markdown}
            </ReactMarkdown>
          </article>
        </CardBody>
      </Card>

      <div className="space-y-4">
        {dossier?.validation ? (
          <Card>
            <CardHeader>
              <CardTitle>Kiểm tra toàn vẹn</CardTitle>
            </CardHeader>
            <CardBody className="space-y-2">
              <p className="flex items-center gap-2 text-[13px]">
                {dossier.validation.ok ? (
                  <>
                    <CircleCheck className="h-4 w-4 text-support" aria-hidden />
                    <span className="text-support-fg">Mọi trích dẫn còn khớp nguyên văn tài liệu nguồn.</span>
                  </>
                ) : (
                  <>
                    <CircleAlert className="h-4 w-4 text-contradict" aria-hidden />
                    <span className="text-contradict-fg">Hồ sơ không vượt qua kiểm tra — không thể duyệt hoặc xuất.</span>
                  </>
                )}
              </p>
              {dossier.validation.errors.length ? (
                <ul className="list-disc space-y-1 pl-5 text-[12px] text-contradict-fg">
                  {dossier.validation.errors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              {dossier.validation.warnings.length ? (
                <ul className="list-disc space-y-1 pl-5 text-[12px] text-caution-fg">
                  {dossier.validation.warnings.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </CardBody>
          </Card>
        ) : null}

        {blockedByGuardrail ? (
          <Alert tone="caution" title="Cảnh báo guardrail">
            Hồ sơ có câu mang nghĩa khẳng định nhân quả. Nội dung vẫn hiển thị nguyên văn để bạn đối chiếu, nhưng đây là
            lỗi cần sửa trước khi duyệt: agent chỉ được mô tả mức độ bằng chứng, không được kết luận quan hệ nhân quả.
          </Alert>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Truy vết</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2 text-[13px] text-muted-foreground">
            {dossier?.contentHash ? <HashChip hash={dossier.contentHash} status="unchecked" /> : null}
            <p>
              Hồ sơ gắn với phiên bản bằng chứng tại thời điểm tạo. Nếu bằng chứng thay đổi sau đó, hồ sơ bị đánh dấu cần
              duyệt lại và không xuất được cho tới khi kiểm tra lại.
            </p>
            <p>Bản Markdown nêu rõ nguồn, phiên bản và khoảng trống còn lại; không chứa khuyến cáo điều trị.</p>
          </CardBody>
        </Card>

        {message ? <Alert tone="caution" title="Chưa xuất được">{message}</Alert> : null}
      </div>
    </div>
  );
}
