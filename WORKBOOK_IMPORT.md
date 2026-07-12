# Workbook Import

The workbook is normalized into `core/fixtures/workbook_import_v1.json` before migrations run.
Production migrations never parse Excel directly.

## Regenerate the fixture

```bash
python manage.py extract_workbook_fixture "../Situation les Amis Sept 2023 Version (1).xlsx"
python manage.py test core
```

The extractor stores the workbook SHA-256, source sheet/cell, formulas, parsed values,
declared summary date, and latest exact transaction date. Review and commit both the
workbook and generated fixture together.

## Accounting rules

- Monthly workbook contributions become `HistoricalContributionEntry` records and
  month-precision ledger credits. They do not create fake obligations or receipts.
- Undated aggregate loans, repayments, income, expenses, and charges retain null dates
  with `date_precision="unknown"`.
- Exact-dated active loans, investments, profits, and expenses retain their dates.
- The stated bank balance variance is stored in `BankReconciliationSnapshot`; no
  balancing ledger adjustment is generated.
- Migration `0028_workbook_import_integrity` blocks deployment unless all authoritative
  workbook targets reconcile exactly.
