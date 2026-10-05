import Link from "next/link";
import { PageHeader, Section } from "@/components/public/sections";
import { AssessmentBadge, CoverageGrid } from "@/components/pv/badges";
import { DEMO_INVESTIGATIONS } from "@/lib/mock/seed";

export const metadata = { title: "Ca mẫu" };

const SLUGS: Record<string, string> = {
  "INV-0001": "inv-0001-metformin",
  "INV-0007": "inv-0007-telmisartan",
  "INV-0004": "inv-0004-warfarin",
};

export default function ExamplesPage() {
  const items = DEMO_INVESTIGATIONS.filter((item) => SLUGS[item.id]);

  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/examples", label: "Ca mẫu" }]}
        title="Ca mẫu công khai"
        description="Ba ca minh họa ba kết cục khác nhau: có bằng chứng ủng hộ, lệch phạm vi, và thiếu bằng chứng."
      />
      <Section>
        <ul className="grid gap-4 md:grid-cols-3">
          {items.map((item) => (
            <li key={item.id} className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
              <span className="mono text-[12px] text-muted-foreground">{item.id}</span>
              <h2 className="mt-1.5 font-display text-[18px] leading-snug text-foreground">
                {item.claim.drug} → {item.claim.adverseEvent}
              </h2>
              <p className="mt-1 text-[13px] text-muted-foreground">
                {item.claim.population ?? "Chưa giới hạn quần thể"}
                {item.claim.dose ? ` · ${item.claim.dose.value} ${item.claim.dose.unit}` : ""}
              </p>
              <div className="mt-3">{item.assessment ? <AssessmentBadge status={item.assessment.status} /> : null}</div>
              {item.assessment ? (
                <div className="mt-3 border-t border-border pt-3">
                  <CoverageGrid coverage={item.assessment.coverage} />
                </div>
              ) : null}
              <Link href={`/examples/${SLUGS[item.id]}`} className="mt-3 inline-block text-[13px] underline">
                Đọc ca này
              </Link>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
