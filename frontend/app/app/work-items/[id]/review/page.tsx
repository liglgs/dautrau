"use client";
import { useParams } from "next/navigation";
import { ReviewPanel } from "@/components/casework/work-item-panels";
export default function WorkItemReviewPage() { const params = useParams<{ id: string }>(); return <ReviewPanel id={decodeURIComponent(params.id ?? "")} />; }
