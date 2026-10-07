"use client";
import { useParams } from "next/navigation";
import { WorkOverview } from "@/components/casework/work-item-panels";
export default function WorkItemOverviewPage() { const params = useParams<{ id: string }>(); return <WorkOverview id={decodeURIComponent(params.id ?? "")} />; }
