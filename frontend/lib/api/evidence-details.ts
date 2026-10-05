/** Evidence fields come from the extracted observation, never from the claim. */
export function evidenceDetails(item: Record<string, unknown>) {
  const scope = item.scope && typeof item.scope === "object"
    ? item.scope as Record<string, unknown> : {};
  const text = (value: unknown) => typeof value === "string" && value.trim() ? value : undefined;
  const rawNote = text(item.notes);
  let designNote = rawNote;
  if (rawNote?.trim().startsWith("{")) {
    designNote = undefined;
    try {
      const annotation = JSON.parse(rawNote) as Record<string, unknown>;
      if (annotation.schema_version === "person3.1") {
        const pieces: string[] = [];
        if (text(annotation.comparator)) pieces.push(`Đối chứng: ${annotation.comparator}`);
        const uncertainty: Record<string, string> = { low: "thấp", high: "cao", unknown: "chưa rõ" };
        if (typeof annotation.uncertainty === "string" && uncertainty[annotation.uncertainty]) {
          pieces.push(`Độ bất định của kết quả: ${uncertainty[annotation.uncertainty]}`);
        }
        designNote = pieces.join(". ") || undefined;
      }
    } catch {
      // Malformed internal metadata is not a reviewer-facing study note.
    }
  }
  return { studyPopulation: text(scope.population), dose: text(scope.dose), designNote };
}
