# ProjectFit migration baseline

## Working branch

- Repository: `myabusinessha-del/ProjectFit`
- Production branch: `main`
- Migration branch: `projectfit/migration-foundation`
- Baseline commit inspected: `acca4492465bf7544412e9585af549a7a725c6c3`
- This work is isolated from `main`; no production deployment or database mutation is part of this baseline.

## Current application architecture

The repository is not a blank project. It currently contains:

- A single-page vanilla HTML/CSS/JavaScript frontend in `index.html`.
- A Python HTTP API in `server.py`, with application services generated at Render build time from a compressed source artifact.
- A Python calculation engine in `engine.py` for workout progression, training volume, estimated 1RM, body-fat estimation, nutrition totals and progress rules.
- A Python meal-planning module in `planner.py`.
- SQLite persistence in `db.py`, used as the application's local/server cache.
- Supabase Auth and a versioned record-sync layer in `supabase_auth.py`, `cloud_service.py` and `cloud_sync.py`.
- GitHub Actions tests under `tests/` and `.github/workflows/tests.yml`.

## Existing functionality confirmed in source

- Supabase email/password signup, login, password recovery, confirmation resend and logout.
- Profile/goals, programme, workout sessions, exercise logs, measurements, nutrition entries, activity entries, weekly check-ins, progress reviews and privacy settings in the local schema.
- Cloud record synchronization uses per-user `pf_records` rows and version checks.
- Workout progression recommendations are calculated in `engine.py`; the programme is a prescription and should not be silently rewritten.
- The meal planner currently supports 3, 4 or 5 meals/day and a configurable 1–14 day plan.
- The current food catalogue and meal templates are static planning data. Vegetarian templates are present; a vegan catalogue/template set is not present.

## Gaps and risks to address

1. **Meal-plan persistence:** the SQLite schema has no dedicated saved meal-plan or shopping-list entities. These need a safe additive design and corresponding cloud record support.
2. **Budget optimisation:** `plan_for` computes a plan and then reports whether the estimated pack total is within budget. It does not currently optimise ingredient quantities or meal choices to satisfy a hard budget ceiling.
3. **Retailer pricing:** catalogue prices are hard-coded planning estimates and each catalogue item lists the same three retailers. There is no live retailer feed or store-specific product match. The UI correctly describes prices as estimates; future price integrations must preserve that distinction.
4. **Dietary coverage:** vegetarian templates exist, but vegan meals, explicit allergy/exclusion validation and ingredient-level dietary guarantees need implementation.
5. **Nutrition calculator validation:** `calculate_targets` implements a Mifflin-St Jeor-style estimate and activity/goal adjustments, but needs boundary validation, clearer calculation explanations and regression tests before expansion.
6. **User profile UX:** the current profile form exposes display name, age, height and manual calorie/protein targets; the full set of requested sex, weight, activity, goal, dietary and allergy fields is not yet represented in that form.
7. **Frontend architecture:** the current interface is a single HTML file with inline JavaScript and CSS. React/TypeScript migration should be incremental, with the current API kept stable until replacement routes are tested.
8. **SQLite durability:** the live Render service has no persistent disk configured in the inspected service settings. Cloud records are the durable source; verify that all writes are synced and recovery paths are safe before depending on local SQLite across restarts.
9. **Authentication consolidation:** the code contains both legacy local credential/session handling and Supabase Auth. Supabase should remain the production identity provider; legacy routes should be reviewed before removal.
10. **Production configuration:** the deployed service is named `projectfit-live`; the repository's `render.yaml` describes a separate service named `projectfit`. Do not apply the Blueprint or change either service until the intended hosting topology is reviewed.

## Safe implementation sequence

### Foundation / Stage 1
- Preserve the current application and production branch.
- Add focused regression coverage for nutrition calculations, authentication boundaries and data synchronization.
- Validate health/readiness and identify a reliable test path for the compressed service source.
- Define additive profile and meal-plan data contracts before schema changes.
- Build the React/TypeScript frontend alongside the current UI; keep the current API operational during the transition.

### Nutrition / Stage 2
- Add profile-driven targets with explicit user overrides.
- Implement ingredient-level vegetarian/vegan/allergen checks.
- Add saved daily and weekly meal plans, editable portions and recalculated macros.

### Shopping / Stage 3
- Generate shopping quantities from saved meal-plan ingredients.
- Add retailer-specific product mapping and timestamped prices only from verified sources.
- Add budget-aware substitutions/optimisation; clearly mark estimates when live feeds are unavailable.

### Tracking / Stages 4–5
- Extend the diary and progress views, then add reviewed AI food estimates, exercise media and parent-controlled child nutrition with age-specific references.

### Release / Stage 6
- Run unit, integration, authorization/RLS, sync/recovery, accessibility and responsive-layout tests.
- Deploy only after the production migration and hosting plan has been explicitly reviewed.

## Safety rules

- Do not alter `main`, deploy the migration branch, change Render services, or mutate Supabase production data as part of exploratory work.
- Database changes must be additive, reviewed and backed up; no destructive migrations without explicit approval.
- Never report a feature as complete based only on a UI control or README statement. Require implementation and test evidence.
