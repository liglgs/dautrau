"use client";
import { useParams } from "next/navigation";
import { EvidencePanel } from "@/components/casework/work-item-panels";
export default function WorkItemEvidencePage() { const params = useParams<{ id: string }>(); return <EvidencePanel id={decodeURIComponent(params.id ?? "")} />; }
