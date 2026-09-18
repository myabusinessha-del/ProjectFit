# ProjectFit V2.2 — Cloud-connected local application

ProjectFit is the workbook-derived fitness app with the frozen calculation engine, now connected to a Supabase cloud account for multi-device persistence.

## Run
1. Install Python 3.11+.
2. `pip install -r requirements.txt`
3. Run `START_PROJECTFIT.bat` on Windows or `python server.py`.
4. Open `http://localhost:8000`.

The package contains a `projectfit_config.py` with the Supabase project URL and **publishable** client key. No Supabase secret/service-role key is embedded.

## Cloud features
- Managed email/password account creation and login.
- Password-reset email flow.
- Cloud persistence of profile/goals, programme, workout logs, derivations, measurements, nutrition, activity, weekly check-ins, reviews and privacy settings.
- Startup/login synchronisation and retry when the browser comes back online.
- Local SQLite remains the offline cache.
- Optimistic version checking and explicit conflicts.
- Data export.
- Logout all devices.
- Account deletion including cloud application records.

## Security
- Supabase Auth owns passwords and authentication.
- The database uses RLS policies based on `auth.uid()`.
- The browser receives only a publishable key.
- The local Python bridge keeps the Supabase access token server-side in its local session store.
- No passwords or access tokens are written to application logs.

## Production note
This is a cloud-connected development release, not a public hosted deployment. To make the app accessible from any browser without running Python locally, deploy the application/API to a hosting provider and configure HTTPS and a production domain. The Supabase project is already provisioned.
