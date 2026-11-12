# Tracker import

Staging and production deployments load the approved tracker once per database, after Django migrations. The VPS reads the manifest and checksum from the Git release.

## Extract and preview

Run these commands from the backend directory. Generated previews and audit reports in `workbook-import/` are ignored by Git.

```bash
python manage.py extract_workbook_fixture "../Situation les Amis Sept 2023 Version (1).xlsx" \
  --output workbook-import/tracker.json

python manage.py import_workbook workbook-import/tracker.json \
  --report workbook-import/preview.json
```

The extractor reads the saved values in the tracker. If a required formula cache is missing or invalid, open the workbook in Excel, recalculate, and save before trying again. The manifest records the workbook SHA-256 and source cells. It uses the tracker layout through December 2026. Review any change to that layout before extending the extractor.

Review the counts, totals, and discrepancies in the preview. The approved baseline is `workbook-import/tracker-november-2026.json`. Its `.sha256` file contains the reviewed `manifest_sha256` as a single lowercase digest. Both files are committed to the public repository. Keep the original workbook and audit reports in private storage.

## Verify a deployment

Check the VPS deployment log for `applied` on the first deployment and `already_applied` on subsequent deployments. In Django admin, check Import batches for the release SHA, inserted counts, and reconciliation totals. See [Deployment](DEPLOYMENT.md) for rollout steps.

## Apply manually to fresh PostgreSQL

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
