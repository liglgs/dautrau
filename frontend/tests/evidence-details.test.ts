import { describe, expect, it } from "vitest";
import { evidenceDetails } from "@/lib/api/evidence-details";

describe("reviewer evidence details", () => {
  it("shows extracted population/dose and readable notes without internal JSON", () => {
    const details = evidenceDetails({
      scope: { population: "adults", dose: "10 mg/day" },
      notes: JSON.stringify({ schema_version: "person3.1", comparator: "placebo", uncertainty: "low",
        document_hash: "internal-hash", drug_ingredient: "ingredient_alpha" }),
    });
    expect(details.studyPopulation).toBe("adults");
    expect(details.dose).toBe("10 mg/day");
    expect(details.designNote).toContain("Đối chứng: placebo");
    expect(details.designNote).not.toMatch(/schema_version|internal-hash|ingredient_alpha/);
  });
  it("keeps missing source fields unspecified and hides malformed internal metadata", () => {
    const details = evidenceDetails({ scope: { population: null, dose: null }, notes: '{"schema_version":' });
    expect(details.studyPopulation).toBeUndefined();
    expect(details.dose).toBeUndefined();
    expect(details.designNote).toBeUndefined();
  });
});
