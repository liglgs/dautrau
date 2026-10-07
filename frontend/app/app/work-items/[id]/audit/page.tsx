"use client";
import { useParams } from "next/navigation";
import { AuditPanel } from "@/components/casework/work-item-panels";
export default function WorkItemAuditPage() { const params = useParams<{ id: string }>(); return <AuditPanel id={decodeURIComponent(params.id ?? "")} />; }
