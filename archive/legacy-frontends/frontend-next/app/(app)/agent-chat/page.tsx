import { Suspense } from "react";
import AgentChat from "../../../src/AgentChat";
import { LoadingPanel, Panel, PanelBody } from "../../../src/components/ui";

export default function AgentChatPage() {
  return (
    <Suspense
      fallback={
        <Panel>
          <PanelBody>
            <LoadingPanel rows={4} label="Đang mở trợ lý AI…" />
          </PanelBody>
        </Panel>
      }
    >
      <AgentChat />
    </Suspense>
  );
}
