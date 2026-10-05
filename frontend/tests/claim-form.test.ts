import { describe, expect, it } from "vitest";
import { SubmissionIdentity, validateClaim } from "@/lib/claim-form";
import type { CreateInvestigationInput } from "@/lib/api/types";

const input: CreateInvestigationInput = { claimText: "Investigate Drug and Event", drug: "Drug", adverseEvent: "Event", sources: ["pubmed", "dailymed", "faers"], maxSteps: 8, maxDocs: 50 };

describe("claim creation", () => {
  it("does not clear operation identity after uncertain failure", () => {
    const identity = new SubmissionIdentity();
    const key = identity.forInput(input);
    expect(identity.forInput({ ...input })).toBe(key);
    expect(identity.forInput({ ...input, drug: "Changed" })).not.toBe(key);
  });
  it("requires drug/event and a source before creating a job", () => {
    expect(validateClaim({ ...input, drug: " " })).toBeTruthy();
    expect(validateClaim({ ...input, adverseEvent: "" })).toBeTruthy();
    expect(validateClaim({ ...input, sources: [] })).toBeTruthy();
  });
  it("enforces ceilings and integer budgets", () => {
    expect(validateClaim({ ...input, maxSteps: 21 })).toBeTruthy();
    expect(validateClaim({ ...input, maxDocs: 101 })).toBeTruthy();
    expect(validateClaim({ ...input, maxSteps: 1.5 })).toBeTruthy();
    expect(validateClaim(input)).toBeNull();
  });
  it("counts Unicode code points for backend text limits", () => {
    expect(validateClaim({ ...input, drug: "😀".repeat(200) })).toBeNull();
    expect(validateClaim({ ...input, drug: "😀".repeat(201) })).toBeTruthy();
  });
});
