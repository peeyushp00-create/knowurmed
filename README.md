# KnowUrMed — AI Medicine and Prescription Companion

KnowUrMed helps people understand their medicines and prescriptions before taking them: search a medicine to see what it's for, how to take it, and its safety precautions, with a plain-language safety summary instead of a misleading numeric "score." It also includes a full clinic workflow (patient/doctor/admin roles, appointment booking, complaints, feedback).

> **This project is being built in phases.** The current codebase covers **Phase 1 and Phase 2**: the redesigned landing page, an extended medicine database, medicine search with autocomplete, category-based safety summaries, and prescription upload with OCR-based extraction + a confirm/edit review screen. The AI explainer dashboard, daily schedules, interaction checking, health profiles, and the admin CMS are planned but not yet built — see [Roadmap](#roadmap).

## Medical disclaimer

KnowUrMed is an educational tool. It does not diagnose conditions, prescribe or change medicines, or replace professional medical advice. Always confirm dosing, interactions, and any prescription details with your doctor or pharmacist. Where verified information isn't available, the site says so explicitly ("Information unavailable") rather than guessing.

## Main features (current)

- **Medicine search with autocomplete** — search by brand or generic name; results show composition, dosage, side effects, precautions, food/driving/pregnancy/breastfeeding/kidney/liver guidance, storage, missed-dose guidance, serious warning signs, and source references.
- **Medicine Safety Summary** — category-based safety cards (food, driving, pregnancy, breastfeeding, kidney, liver, allergy, age, interactions, duplicate ingredients), each with a status (Low Concern / Caution / Important Warning / Healthcare Review Required / Information Unavailable), an explanation, a recommended next step, a source, and a review date. No single numeric score is ever shown.
- **Landing page** covering how the product works, the safety-assistant concept, why KnowUrMed instead of a search engine or a general AI chatbot, why to confirm with a professional, FAQ, and privacy notes.
- **Prescription upload & OCR review** — drag-and-drop or camera upload (JPG/PNG/PDF), text extraction via Tesseract, regex + fuzzy-match detection of medicine name/strength/frequency/duration against the verified catalog, and a review screen where every detected medicine must be individually confirmed, edited, or removed (plus a manual-add fallback) before the prescription is marked confirmed. Files are private to the uploading patient.
- **Patient / doctor / admin portal** — registration with admin approval, role-based dashboards, appointment booking and management, complaints, and feedback.

## Screenshots

_Add screenshots here as the UI stabilizes._

## Technology stack

- **Backend**: Django 6 (Python), server-rendered templates (no separate frontend framework — kept consistent with the existing design)
- **Database**: SQLite for local development (toggle via `USE_SQLITE`); MySQL configuration is present for future use
- **Frontend**: Bootstrap 5 (public/patient/doctor pages) plus a custom CSS component set for the admin dashboard
- **Environment config**: `python-dotenv` (`.env` file, gitignored)

## Architecture overview

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full breakdown of models, views, URLs, and template structure.

## Local setup

### Prerequisites

- Python 3.12+
- Git

### 1. Clone and set up a virtual environment

```bash
git clone <this-repo-url>
cd KnowUrMed/project
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` as needed. For local development, the defaults (SQLite, debug on) work out of the box.

### 3. Database setup

```bash
python manage.py migrate
python manage.py seed_medicines   # loads sample medicine + safety data
python manage.py createsuperuser  # create an admin login
```

To use the custom `/login` page (not just Django's `/admin/`) as an admin, add your superuser to the `admin` group:

```bash
python manage.py shell -c "
from django.contrib.auth.models import User, Group
g, _ = Group.objects.get_or_create(name='admin')
User.objects.get(username='<your-username>').groups.add(g)
"
```

### 4. Run the server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/**.

### OCR setup

Prescription upload needs two external tools installed on the machine (not pip packages):

- **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)** — on Windows, `winget install -e --id UB-Mannheim.TesseractOCR`. Defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe`; override with `TESSERACT_CMD` in `.env` if yours is elsewhere.
- **[Poppler](https://github.com/oschwartz10612/poppler-windows)** (needed for PDF uploads only — JPG/PNG work without it) — on Windows, `winget install -e --id oschwartz10612.Poppler`. Set `POPPLER_PATH` in `.env` to its `Library/bin` folder if `pdftoppm` isn't on your PATH.

Uploaded files are stored under `media/` (gitignored, never publicly served — only through an ownership-checked view).

## Testing

Not yet implemented — a test suite is planned for a later phase (see Roadmap). Until then, verification is done via manual route sweeps documented in each phase's changes.

## Security notes

- Secrets (`DJANGO_SECRET_KEY`, database credentials) are read from environment variables via `.env` (gitignored), not hardcoded.
- `db.sqlite3`, `.venv/`, `.env`, and `media/` are excluded from version control.
- Prescription uploads are validated by extension, size (10 MB max), and actual file content (image files are opened/verified with Pillow; PDFs are checked for a real `%PDF` header) — not just the filename.
- Uploaded files are never served through a public `MEDIA_URL`; the only access path is a view that checks the requesting user owns the prescription (returns 404 otherwise), and it requires login.
- CSRF protection is enabled on all forms, including the JS-driven prescription upload.

## Privacy notes

- Prescriptions aren't deleted automatically yet — the review screen has an explicit "Delete this upload" action, and `manage.py cleanup_old_prescriptions --days N` exists for bulk cleanup, but no scheduler runs it automatically (that's a deployment-time decision, not wired up here).
- Patient health/profile data (age, gender, contact info) is only visible to the patient themselves and approved admin/doctor accounts, gated by Django's auth and group system.

## Contributing

This is currently a single-developer project built incrementally in phases. If you'd like to contribute, open an issue describing the change before submitting a pull request, so it can be scoped against the current roadmap.

## License

_License to be decided — treat as all-rights-reserved until a LICENSE file is added._

## Roadmap

1. ~~Phase 1 — Landing page redesign, extended medicine database, search with autocomplete, safety summaries~~ (done)
2. ~~Phase 2 — Prescription upload (image/PDF), OCR text extraction, confirm/edit review screen~~ (done)
3. Phase 3 — Prescription Explainer dashboard, daily medication schedule, interaction checker
4. Phase 4 — Optional health profile, personalized safety checks, printable/PDF report, conversational AI assistant (pending an LLM API key)
5. Phase 5 — Admin CMS with audit logging, OCR-failure review queue, full automated test suite, security hardening pass
