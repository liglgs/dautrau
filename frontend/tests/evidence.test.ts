import { describe, expect, it } from "vitest";
import { quoteSegments, safeSourceUrl } from "@/lib/evidence-view";

describe("quote provenance", () => {
  it("highlights the exact Unicode locator, including a repeated quote", () => {
    expect(quoteSegments("😀 quote / quote", { start: 10, end: 15, text: "quote" })).toEqual({ before: "😀 quote / ", marked: "quote", after: "" });
  });
  it("does not use includes() as a substitute for locator verification", () => {
    expect(quoteSegments("one quote two", { start: 0, end: 5, text: "quote" })).toBeNull();
    expect(quoteSegments("quote", { start: -1, end: 5, text: "quote" })).toBeNull();
  });
  it("rejects executable, credentialed and foreign source URLs", () => {
    expect(safeSourceUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeSourceUrl("https://attacker.invalid")).toBeUndefined();
    expect(safeSourceUrl("https://user:pass@pubmed.ncbi.nlm.nih.gov/1")).toBeUndefined();
    expect(safeSourceUrl("https://pubmed.ncbi.nlm.nih.gov/1/")).toBe("https://pubmed.ncbi.nlm.nih.gov/1/");
  });
});
