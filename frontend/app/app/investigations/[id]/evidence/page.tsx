"use client";

import { useParams } from "next/navigation";
import { Alert, Card, CardBody, Skeleton } from "@/components/ui";
import { EvidenceMatrix } from "@/components/pv/evidence-matrix";
import { useEvidence } from "@/lib/hooks/use-data";
import { useAppStore } from "@/lib/store/app-store";

export default function EvidenceTabPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id ?? "");
  const { data, isLoading, error } = useEvidence(id);
  const density = useAppStore((state) => state.density);
  const role = useAppStore((state) => state.role);

  if (isLoading) {
    return (
      <Card>
        <CardBody className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardBody>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card>
        <CardBody>
          <p className="text-[14px] text-contradict-fg">Không tải được bằng chứng: {(error as Error).message}</p>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {error ? <Alert tone="caution" title="Không làm mới được bằng chứng">{error.message} Đang hiển thị dữ liệu đã tải trước đó.</Alert> : null}
      <EvidenceMatrix
        investigationId={id}
        items={data ?? []}
        density={density}
        canRequestMore={role === "reviewer" || role === "admin"}
      />
    </div>
  );
}
