"use client";
import { useParams } from "next/navigation";
import { FollowUpsPanel } from "@/components/casework/work-item-panels";
export default function WorkItemFollowUpsPage() { const params = useParams<{ id: string }>(); return <FollowUpsPanel id={decodeURIComponent(params.id ?? "")} />; }
