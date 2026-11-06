# ProjectFit authentication and data-integrity audit

Audit date: 2026-11-06

Scope: read-only inspection of the migration branch, Supabase schema/policies and Render service configuration, followed by isolated code/test changes on `projectfit/migration-foundation`. No production deployment, Render configuration change or Supabase data mutation was performed.

## Findings confirmed in source

1. **Cloud session expiry was not enforced on ordinary API requests.** `server.Handler.uid()` used `CloudAccountService.user_id()`, which previously trusted the presence of a local cookie-to-session row without checking whether its Supabase access token had expired or could be refreshed. This meant normal app endpoints could continue accepting a locally stored cloud session after token expiry. The migration branch now requires a valid or successfully refreshed access token before returning the cloud user ID. Focused tests cover active, expired, refreshable and revoked/failed-refresh sessions.
2. **Account deletion was only partial.** The prior implementation deleted `pf_records` and the local SQLite user, but did not delete the corresponding Supabase Auth user or clean up the separate `pf_users` / `pf_sessions` records. The app has no trusted-server Admin API deletion implementation or verified secret-key configuration. The migration branch now fails closed before deleting anything and returns a clear message that no data was changed. Complete deletion remains blocked until a secure server-side cleanup flow is designed and configured.
3. **Password recovery is incomplete end-to-end.** The API requests a recovery email, but the inspected frontend has no recovery-token callback or password-update form/route. Sending the email alone does not complete a reset. This remains a feature gap.
4. **Export source needs improvement.** The current export endpoint calls the local SQLite export routine for a Supabase-authenticated account. It does not first export the cloud source of truth, so a stale local cache could result in an incomplete export. This remains a feature gap.
5. **RLS policy inspection.** RLS is enabled on `pf_users`, `pf_records` and `pf_sessions`. The observed policies scope `pf_records` reads/inserts/updates/deletes to `auth.uid() = user_id`, with update ownership checked in both `USING` and `WITH CHECK`. `pf_users` has self-select and self-update policies. `pf_sessions` has self-select only. The app's current record-sync code uses `pf_records`; a broader review is still required before adding direct use of the other tables.
6. **Supabase security advisor warning.** Leaked-password protection is disabled. This is a dashboard-level Auth configuration item and has not been changed.
7. **Production topology.** Render's `projectfit-live` service deploys from `main`; migration-branch changes remain isolated and have not been deployed.

## Branch changes from this audit

- `CloudAccountService.user_id()` now validates/refreshes the cloud access token before authorizing ordinary API requests.
- Regression tests cover cloud-session expiry and refresh.
- Account deletion now fails closed before any cloud or local deletion because the complete Auth/profile cleanup capability is not implemented.
- Regression test verifies the fail-closed deletion path leaves both cloud and local data untouched.

## Remaining work

- Implement a verified password-recovery callback and password-update flow.
- Implement complete account deletion using a trusted server-side Supabase secret key, covering Auth and all related application records; require a deliberate user confirmation and test rollback/failure handling.
- Change account export to read the authenticated cloud source of truth and test completeness.
- Review session revocation semantics and multi-device behaviour.
- Enable leaked-password protection through the approved Supabase project settings workflow before public release.
- Expand authorization tests and validate the RLS model before introducing new tables or client access.

## Safety boundary

All code changes above are on the migration branch. No merge, production deploy, Render configuration update, Supabase schema change, Auth setting change or production data write was performed.
