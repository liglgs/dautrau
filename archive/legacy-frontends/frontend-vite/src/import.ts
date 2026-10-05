import type { Manifest, Source } from "./types";
const stamp = (v: unknown) =>
  typeof v === "string" &&
  /T.*(Z|[+-]\d{2}:\d{2})$/.test(v) &&
  !Number.isNaN(Date.parse(v));
const safeId = (v: unknown) =>
  typeof v === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(v);
export function validateImport(
  raw: unknown,
  files: { name: string; text: string }[],
): { manifest: Manifest; sources: Source[] } {
  const m = raw as Manifest;
  if (
    !m ||
    m.schema_version !== "1.0" ||
    !safeId(m.case_id) ||
    !safeId(m.patient_id) ||
    !safeId(m.encounter_id) ||
    !stamp(m.reconciliation_at) ||
    !stamp(m.initial_visible_at)
  )
    throw new Error(
      "case.json: sai schema, mã ca hoặc thời gian (cần múi giờ).",
    );
  if (
    !Array.isArray(m.documents) ||
    !m.documents.length ||
    m.documents.length > 8
  )
    throw new Error("Gói phải có từ 1 đến 8 tài liệu.");
  if (
    !Array.isArray(files) ||
    new Set(files.map((f) => f.name)).size !== files.length
  )
    throw new Error("Danh sách tệp sai hoặc tên tệp bị trùng.");
  const ids = new Set<string>(),
    names = new Set<string>();
  const sources = m.documents.map((d) => {
    if (!d || !safeId(d.source_id) || ids.has(d.source_id))
      throw new Error("source_id không hợp lệ hoặc bị trùng.");
    ids.add(d.source_id);
    if (
      typeof d.filename !== "string" ||
      !/^[^\\/:]+\.txt$/i.test(d.filename) ||
      d.filename.includes("..") ||
      names.has(d.filename)
    )
      throw new Error("Tên tệp TXT không hợp lệ hoặc bị trùng.");
    names.add(d.filename);
    if (
      ![
        "prior_prescription",
        "medication_history",
        "admission_order",
        "clinical_note",
      ].includes(d.kind) ||
      !Number.isInteger(d.version) ||
      d.version < 1 ||
      typeof d.author_role !== "string" ||
      !d.author_role.trim() ||
      !stamp(d.available_at) ||
      (d.event_time !== null && !stamp(d.event_time)) ||
      (d.recorded_at !== null && !stamp(d.recorded_at))
    )
      throw new Error(`${d.filename}: metadata không hợp lệ.`);
    if (Date.parse(d.available_at) > Date.parse(m.initial_visible_at))
      throw new Error(`${d.filename}: nguồn tương lai chưa được phép nhập.`);
    const file = files.find((f) => f.name === d.filename);
    if (!file) throw new Error(`Thiếu tệp ${d.filename}.`);
    if (Array.from(file.text).length > 12000)
      throw new Error(`${d.filename}: vượt 12.000 ký tự Unicode.`);
    return { ...d, text: file.text };
  });
  if (files.length !== sources.length)
    throw new Error("Có tệp không được tham chiếu trong manifest.");
  if (sources.reduce((n, s) => n + Array.from(s.text).length, 0) > 96000)
    throw new Error("Gói vượt 96.000 ký tự.");
  return { manifest: m, sources };
}
export async function readImport(manifestFile: File, files: File[]) {
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let raw: unknown;
  try {
    raw = JSON.parse(decoder.decode(await manifestFile.arrayBuffer()));
  } catch {
    throw new Error("case.json: JSON hoặc UTF-8 không hợp lệ.");
  }
  return validateImport(
    raw,
    await Promise.all(
      files.map(async (file) => ({
        name: file.name,
        text: decoder.decode(await file.arrayBuffer()),
      })),
    ),
  );
}
