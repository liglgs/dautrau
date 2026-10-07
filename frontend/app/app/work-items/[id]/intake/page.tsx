"use client";
import { useParams } from "next/navigation";
import { IntakePanel, AdrPanel } from "@/components/casework/work-item-panels";
import { useWorkflow } from "@/lib/hooks/use-casework";
export default function WorkItemIntakePage() { const params = useParams<{ id: string }>(); const id = decodeURIComponent(params.id ?? ""); const { data } = useWorkflow(id); return data?.work_item.kind === "adr" ? <AdrPanel id={id} /> : <IntakePanel id={id} />; }
