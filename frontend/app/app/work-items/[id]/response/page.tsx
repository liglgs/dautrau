"use client";
import { useParams } from "next/navigation";
import { ResponsePanel } from "@/components/casework/work-item-panels";
export default function WorkItemResponsePage() { const params = useParams<{ id: string }>(); return <ResponsePanel id={decodeURIComponent(params.id ?? "")} />; }
