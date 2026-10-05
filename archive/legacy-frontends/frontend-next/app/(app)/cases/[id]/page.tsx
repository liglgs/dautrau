import { Suspense } from "react";
import Workspace from "../../../../src/Workspace";
import { LoadingPanel, Panel, PanelBody } from "../../../../src/components/ui";

export default async function CasePage({
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
            <LoadingPanel rows={4} label="Đang tải hồ sơ…" />
          </PanelBody>
        </Panel>
      }
    >
      <Workspace caseId={id} />
    </Suspense>
  );
}
