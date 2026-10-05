import { Suspense } from "react";
import CaseList from "../../../src/CaseList";
import { LoadingPanel, Panel, PanelBody } from "../../../src/components/ui";

export default function CasesPage() {
  return (
    <Suspense
      fallback={
        <Panel>
          <PanelBody>
            <LoadingPanel rows={4} label="Đang tải danh sách ca…" />
          </PanelBody>
        </Panel>
      }
    >
      <CaseList />
    </Suspense>
  );
}
