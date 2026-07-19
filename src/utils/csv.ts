const FORMULA_PREFIX = /^[\t ]*[=+\-@]/;

export function escapeCsvCell(value: unknown): string {
  const normalized = String(value ?? "").replace(/[\r\n]+/g, " ");
  const safe = FORMULA_PREFIX.test(normalized) ? `'${normalized}` : normalized;
  return `"${safe.replace(/"/g, '""')}"`;
}
