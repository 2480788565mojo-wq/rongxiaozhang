# Flexible Excel Import Implementation Plan

> **For agentic workers:** Use independent workers for parser, backend batches and charts; the primary agent owns import UI, save orchestration and integration. Preserve existing uncommitted changes.

**Goal:** Import 5000-row heterogeneous Excel files with reviewable conversion, and replace the trend curve with grouped bars.

**Architecture:** Local workbook inspection and explicit column mapping feed a normalized preview. A paginated UI submits stable-key batches, with a compatible single-row fallback. The existing chart host renders grouped bars.

**Tech Stack:** uni-app Vue 3, TypeScript, SheetJS, ECharts, FastAPI and SQLAlchemy.

**Spec:** `docs/superpowers/specs/2026-09-23-flexible-excel-design.md`

## Global Constraints

- Target WeChat mini program; no paid API, new voice plugin or remote spreadsheet upload.
- Capacity 10000 bills / 20MB, 50 preview rows, 100 records per atomic HTTP batch.
- Keep import keys stable across pause, partial success and retry; do not mutate production data during UI tests.

## Task 1 — Recognition and normalization

Files: `src/subpackages/import/excel-import.ts`, `excel-import.test.ts`.

Interfaces: `readExcelWorkbook(data)`, `inspectExcelSheet(workbook, sheetName?, headerRow?)`, `convertExcelSheet(workbook, sheetName, mapping)`. Mapping contains zero-based header/column indices, one-based startRow and amountMode (`type`, `signed`, `split`, `expense`, `income`, `unknown`). Preserve synchronous `parseExcelBills` convenience API.

- [ ] Add failing workbook tests for 5000 rows, late/absent headers, split/signed amounts and explicit mapping; run `npm test -- src/subpackages/import/excel-import.test.ts`.
- [ ] Implement scoring, conservative inference and strict normalization; yield during asynchronous row conversion and reject overflow rather than truncate.
- [ ] Verify invalid rows and true duplicates retain original line numbers; measure 5000-row conversion.

## Task 2 — Atomic batch writes

Files: `backend/app/schemas/bill.py`, `backend/app/api/v1/bills.py`, new `backend/app/services/bill_import_service.py`, backend import tests.

Interface: POST `/bills/import`, `{ledger_id, items: [{import_key, ...bill}]}` → `{items: [{import_key, bill_id, created}]}`. Maximum 100 rows. Same key with different data returns 409; unchanged retries return existing IDs.

- [ ] Write failure tests for absent endpoint, duplicate keys, unauthorized ledger and rollback.
- [ ] Lock user once, fetch existing keys together, insert new bills and aggregate account balance changes; commit all rows before updating cache.
- [ ] Verify real-database transactions, idempotency and unchanged manual-bill APIs.

## Task 3 — Responsive preview and resumable submission

Files: `src/subpackages/import/index.vue`, new `import-runner.ts` and tests, `src/api/bills.ts`, `import.mp.test.ts`.

- [ ] Test batch boundaries, unchanged retry keys, partial success, pause, 404/405 fallback and non-fallback errors before implementing runner.
- [ ] Keep workbook and full row list outside deep UI reactivity; render only 50 visible records. Update checkbox selection only for the visible page.
- [ ] Add sheet/header/start-row/column/amount-mode controls and an explicit conversion button. Preserve user review; lock mapping once writes begin.
- [ ] Save in batches with progress and pause; clear stale global bill list after successful writes so subsequent navigation refetches it.
- [ ] Test preview-only selection, cross-page choices, cancellation, failure and continuation using WeChat conditional compilation.

## Task 4 — Grouped monthly bars

Files: `TrendLine.vue`, `echarts-lite.ts`, chart tests.

- [ ] Assert two non-stacked bar series, month labels and exact money tooltips.
- [ ] Register BarChart and retain existing Canvas initialization/touch handling.
- [ ] Run ordinary chart tests and real ECharts WeChat drawing tests.

## Task 5 — Integration and simulator evidence

- [ ] Run frontend and WeChat tests, type checking, backend tests and production WeChat build.
- [ ] Recompile the actual simulator (disk build alone did not refresh its previous runtime).
- [ ] Use mocked writes to verify 5000-row file recognition, mapping, bounded preview, progress and bars; restore mocks and original ledger state.
- [ ] Update user documentation with limits, recognition review and older-backend behavior.
