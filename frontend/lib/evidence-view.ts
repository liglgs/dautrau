/** Backend locators count Unicode code points, not UTF-16 code units. */
export function quoteSegments(text: string, quote: { start: number; end: number; text: string }) {
  const chars = [...text];
  if (!Number.isInteger(quote.start) || !Number.isInteger(quote.end) || quote.start < 0 || quote.end <= quote.start || quote.end > chars.length) return null;
  const marked = chars.slice(quote.start, quote.end).join("");
  if (marked !== quote.text) return null;
  return { before: chars.slice(0, quote.start).join(""), marked, after: chars.slice(quote.end).join("") };
}

export function safeSourceUrl(raw?: string): string | undefined {
  if (!raw) return undefined;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || url.username || url.password) return undefined;
    const hosts = ["pubmed.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "dailymed.nlm.nih.gov", "open.fda.gov", "api.fda.gov", "www.fda.gov"];
    return hosts.includes(url.hostname) ? url.href : undefined;
  } catch { return undefined; }
}
