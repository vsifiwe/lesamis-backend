# Tracker import

Run Django migrations to create the schema in the fresh database. Then use the tracker commands to review and load the financial baseline.

## Extract and preview

Run these commands from the backend directory. The ignored `workbook-import/` directory is for private workbook manifests and audit reports.

```bash
python manage.py extract_workbook_fixture "../Situation les Amis Sept 2023 Version (1).xlsx" \
  --output workbook-import/tracker.json

python manage.py import_workbook workbook-import/tracker.json \
  --report workbook-import/preview.json
```

The extractor reads the saved values in the tracker. If a required formula cache is missing or invalid, open the workbook in Excel, recalculate, and save before trying again. The manifest records the workbook SHA-256 and source cells. It uses the tracker layout through December 2026. Review any change to that layout before extending the extractor.

Review the counts, totals, and discrepancies in the preview. Copy the `manifest_sha256` from the reviewed report. Keep the original workbook, reviewed manifest, and reports together in private storage.

## Apply to fresh PostgreSQL

Point the backend database settings at the fresh PostgreSQL target. For a new Supabase project used only by Django, disable its Data API before loading tracker data. Keep the web service and scheduler stopped on the target during setup.

```bash
python manage.py migrate --noinput

python manage.py import_workbook workbook-import/tracker.json \
  --report workbook-import/applied.json \
  --apply --expect-sha256 "<manifest_sha256 from preview.json>" \
  --operator "<operator name>"
```

The import verifies the hash, checks that the database is empty of business records, and compares the inserted counts and totals before it commits. It stores the result and source references in Django admin under Import batches and Source references. Running the same apply command again regenerates the report from the saved batch. Review the dashboard and investment totals before enabling the application. Provision admin accounts using `python manage.py createsuperuser`.

## Accounting

- Contributions are historical monthly entries. Imported periods end at the latest month with contribution activity. Automatic cycles and advance payments start after that month.
- Loans and repayments retain exact dates where available. Undated loan aggregates, expenses, income, bank charges, and bond coupon totals retain blank dates. The workbook cover date is separate from the unverified bank balance date.
- The audit reports the variance between the workbook’s stated bank balance and its calculated cash. The ledger retains the underlying amounts and signed corrections.
