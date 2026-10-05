import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader, Prose, Section } from "@/components/public/sections";
import { AssessmentBadge, CoverageGrid, ReviewStateBadge, SourceChip } from "@/components/pv/badges";
import { DEMO_INVESTIGATIONS, DEMO_EVIDENCE } from "@/lib/mock/seed";
import { DATA_MODE } from "@/lib/api";

const MAP: Record<string, string> = {
  "inv-0001-metformin": "INV-0001",
  "inv-0007-telmisartan": "INV-0007",
  "inv-0004-warfarin": "INV-0004",
};

export function generateStaticParams() {
  return Object.keys(MAP).map((slug) => ({ slug }));
}

export default async function ExampleDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const id = MAP[slug];
  const investigation = DEMO_INVESTIGATIONS.find((item) => item.id === id);
  if (!investigation) notFound();

  const evidence = DEMO_EVIDENCE[id] ?? [];

  return (
    <>
      <PageHeader
        breadcrumb={[
          { href: "/", label: "Trang chủ" },
          { href: "/examples", label: "Ca mẫu" },
          { href: `/examples/${slug}`, label: investigation.id },
        ]}
        title={`${investigation.claim.drug} → ${investigation.claim.adverseEvent}`}
        description={investigation.claim.rawText}
        actions={
          DATA_MODE === "api" ? (
            // Ca mẫu chỉ tồn tại ở chế độ dữ liệu mẫu; mã INV-* không có trong backend thật.
            <Link
              href="/app/investigations"
              className="inline-flex h-10 items-center rounded-[var(--radius-control)] border border-input px-4 text-[14px] hover:bg-muted"
            >
              Ca minh hoạ — mở danh sách cuộc điều tra thật
            </Link>
          ) : (
            <Link
              href={`/app/investigations/${investigation.id}`}
              className="inline-flex h-10 items-center rounded-[var(--radius-control)] border border-input px-4 text-[14px] hover:bg-muted"
            >
              Mở trong khu vực làm việc
            </Link>
          )
        }
      />

      <Section>
        <div className="flex flex-wrap items-center gap-2">
          {investigation.assessment ? <AssessmentBadge status={investigation.assessment.status} size="md" /> : null}
          <ReviewStateBadge state={investigation.reviewState} />
          <span className="text-[12px] text-muted-foreground">
            {investigation.usage.steps}/{investigation.budget.maxSteps} bước · {investigation.usage.docs} tài liệu
          </span>
          <span className="ml-auto flex items-center gap-1.5">
            {investigation.sources.map((source) => (
              <SourceChip key={source} source={source} />
            ))}
          </span>
        </div>

        {investigation.assessment ? (
          <div className="mt-4 space-y-3">
            <Prose>
              <p>{investigation.assessment.rationale}</p>
            </Prose>
            <CoverageGrid coverage={investigation.assessment.coverage} />
          </div>
        ) : null}
      </Section>

      <Section title="Bằng chứng đã dùng">
        <ul className="space-y-3">
          {evidence.map((item) => (
            <li key={item.id} className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="mono text-[12px] text-muted-foreground">[{item.label}]</span>
                <SourceChip source={item.source} />
                <span className="text-[12px] text-muted-foreground">{item.externalId}</span>
                <span className="ml-auto text-[12px] text-muted-foreground">
                  {item.stance} · bước {item.foundAtStep}
                </span>
              </div>
              <h3 className="mt-2 text-[15px] text-foreground">{item.title}</h3>
              <blockquote className="mt-2 border-l-2 border-ai-border pl-3 font-serif text-[15px] leading-relaxed text-foreground">
                {item.quotes[0]?.text}
              </blockquote>
              {item.studyPopulation || item.dose ? (
                <p className="mt-2 text-[12px] text-muted-foreground">
                  {item.studyPopulation ? `Quần thể: ${item.studyPopulation}` : ""}
                  {item.dose ? ` · Liều: ${item.dose}` : ""}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[13px] text-muted-foreground">
          Dữ liệu trong ca mẫu là minh họa, không dùng cho quyết định lâm sàng.{" "}
          <Link href="/limitations" className="underline">
            Đọc cam kết minh bạch
          </Link>
          .
        </p>
      </Section>
    </>
  );
}
