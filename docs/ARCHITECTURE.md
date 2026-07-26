# Architecture

## Overview

KnowUrMed is a single Django project (`project/`) with one app (`app/`). It's server-rendered — Django views return HTML templates directly, no separate frontend build or JSON API layer (yet).

```text
project/
├── manage.py
├── requirements.txt
├── .env.example
├── project/            # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── app/                 # The one Django app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   ├── management/commands/seed_medicines.py
│   └── templatetags/safety_extras.py
├── templates/            # All HTML templates (project-level, not per-app)
├── static/                # Two Bootstrap-based theme bundles + admin CSS
└── docs/
```

## Roles and auth

Three Django `Group`s gate three dashboards:

- `admin` — full site administration (medicines, doctor/patient approval, appointments, complaints, feedback)
- `docter` — doctor dashboard (appointment management, schedule, medicine reference, complaints/feedback review, password change)
- `user` — patient dashboard (booking, medicine search, complaints, feedback)

`USER` and `DOCTOR` models both carry an `Approval_Status` field (Pending/Approved/Rejected); the `login` view checks this before allowing sign-in for those roles, so admin approval is required for both patient and doctor accounts.

## Data model (current)

- `MEDICINE` — the core medicine record. Extended in Phase 1 with structured safety-relevant fields (category, prescription-required flag, mechanism, food/driving/pregnancy/breastfeeding/kidney/liver guidance, storage, missed-dose guidance, serious warning signs, source reference, last-reviewed date).
- `MedicineSafetyNote` — one row per (medicine, category) pair, driving the Safety Summary cards. Categories: food, driving, pregnancy, breastfeeding, kidney, liver, allergy, age, interaction, duplicate. Status is an enum (general_info/low_concern/caution/important_warning/review_required/unavailable) — deliberately never a numeric score.
- `DOCTOR`, `USER` — profile records linked one-to-one to Django's built-in `User` for auth.
- `Appointment`, `complaints`, `feedback` — the clinic-workflow models, pre-dating the AI Prescription Explainer feature set.

All medicine safety data is **admin-curated**, not pulled from a live external drug database — see the README's note on data sourcing. This is a deliberate choice for the medical-safety requirement that AI/automation never invents facts: the `MedicineSafetyNote` and extended `MEDICINE` fields are the single source of truth, and any future AI-generated text (Phase 3+) is required to only rephrase what's already in these fields.

## Search

`search_med` (full results page) and `search_med_autocomplete` (JSON endpoint, `GET /search_med/autocomplete/?q=...`) both query `MEDICINE` by `Medicine_name` or `Generic_Name` (case-insensitive contains). The autocomplete endpoint returns up to 8 matches; the frontend (`templates/search_med.html`) debounces input and renders a dropdown, calling it via vanilla JS `fetch` — no frontend framework.

## Templates

Two design systems coexist:

- `header.html` / `footer.html` / `docter_header.html` — a Bootstrap 5 theme ("MediNest") used for the landing page, medicine search, patient dashboard, and doctor dashboard.
- `admin_header.html` / `admin_footer.html` — a custom sidebar admin shell with its own CSS variables and component classes (`.panel`, `.data-table`, `.status-badge`, `.btn-*`), used only for admin pages.

`templates/_safety_status_card.html` is a reusable partial for rendering one `MedicineSafetyNote` as a card; `app/templatetags/safety_extras.py` provides the template filters that map status values to Bootstrap color classes and compute the overall (non-numeric) safety result for a medicine.

## Why Django, not the Next.js/FastAPI stack mentioned in the original product spec

The product spec allowed reusing an existing stack when one exists. This project already had a working Django app with real templates, auth, and a role-based workflow — rewriting it in a different framework would have thrown away working code for no functional benefit. All new features are being added as Django apps/views/models, keeping one deployable unit.
