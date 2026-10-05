import { Suspense } from "react";
import Review from "../../../../../src/Review";
import { LoadingPanel, Panel, PanelBody } from "../../../../../src/components/ui";

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense
      fallback={
        <Panel>
          <PanelBody>
            <LoadingPanel rows={4} label="Đang tải tổng hợp…" />
          </PanelBody>
        </Panel>
      }
    >
      <Review caseId={id} />
    </Suspense>
  );
}
