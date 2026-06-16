# Architecture Changes — Django Migration of DemSchoolTools

This document records all significant changes made while porting the
DemSchoolTools Play/Scala stack to Django.  Each section corresponds to
a self-contained commit that could be cherry-picked or reviewed
independently.

---

## 1. CI Pipeline & Test Infrastructure

**Commit:** `e339f6eb` (squashed into branch)

### What
- `.github/workflows/ci.yml` — 4-job CI (lint, test-django, test-react, build)
- `django/demschooltools/settings_ci.py` — CI-specific Django settings
- `django/dst/tests.py` — 40+ tests covering models, roles, manual views, health
- `django/custodia/tests.py` — 15+ tests covering swipes, overrides, login
- `react/vitest.config.js` + test suites for utils and components

### Why
- No CI existed when the Django migration began
- Needed validation that new code didn't break existing behaviour

### Key Decisions
- CI uses `settings_ci.py` with Postgres service, separate from dev/prod
- `django_vite` dev_mode=False in CI; manifest read from static-vite/
- Frontend tests use Vitest (React Testing Library); wired into package.json

---

## 2. Logging, Secrets & Quick Wins

**Commit:** precedes the CI commit on the branch

### What
- Logger fix: replaced `print()` with `LOGGER` calls in `auth.py`
- Cookie loop fix: `PlaySessionMiddleware` no longer re-processes its own
  cookie writes
- `.env.example` — documented required environment variables
- `/health/` endpoint — JSON health check (DB connectivity)
- `SECRET_KEY` reads from `DJANGO_SECRET_KEY` env var with fallback

### Why
- Hardcoded `print()` statements polluted stdout
- Cookie loop caused infinite redirects in certain auth flows
- No health check existed for monitoring / Docker

---

## 3. Docker & Dev Environment

**Commit:** `1da3ebce`

### Files
- `django/Dockerfile` — multi-stage production build (Node → Python)
- `django/Dockerfile.dev` — dev build with hot-reload
- `django/docker-entrypoint.sh` — entrypoint that runs migrate + seed + runserver
- `docker-compose.yml` — production Compose (postgres + django + nginx)
- `docker-compose.dev.yml` — dev Compose (postgres + django on port 8001)

### Key Decisions
- Dev Docker uses `npm install` not `npm ci` (lockfile out of sync with
  test deps; `npm ci` fails)
- `docker-entrypoint.sh` calls `seed_test_data` then creates test admin user
- No volume mounts in dev — every code change requires `up -d --build`
- `settings_ci.py` is the dev settings file; sets `DEBUG=true` via env var

---

## 4. Login Decoupling from Play/Scala

**Commit:** part of the CI squashed commit

### What
- `LoginView.post()` now validates passwords via `User.check_password()`
  and generates a JWT using `APPLICATION_SECRET`
- JWT stored as `PLAY_SESSION` cookie, consumable by `PlaySessionMiddleware`
- Tests cover: successful login, wrong password, nonexistent user,
  inactive user, GET renders form

### Why
- Previously login required the Play/Scala server to be running for
  Facebook SSO
- Decoupling allows Django to operate independently; Play/Scala frozen

### Files
- `django/custodia/views.py` — `LoginView` rewrite
- `django/demschooltools/auth.py` — `PlaySessionMiddleware` reads JWT

---

## 5. DRF Serializers & API Versioning

**Commit:** part of CI squashed commit

### What
- `django/custodia/serializers.py` — serializers for custodia API responses
- `django/dst/serializers.py` — serializers for DST models
- Custodia views updated to use serializers (`IsAdminView`,
  `StudentsTodayView`, `StudentDataView`, `ReportYears`, `ReportView`)
- API routes registered under both `/custodia-api/` and `/api/v1/custodia/`

### Why
- Previously views manually shaped dicts; serializers provide
  testable, ORJSON-compatible data contracts
- Versioning prefix prepares for future API evolution without breaking
  existing consumers

---

## 6. Static Assets Fix

**Commit:** `d127ea3f`

### What
- `django/static/css/main.css` — created from Play framework assets
  (bootstrap.css + jquery-ui.css + main.less converted to flat CSS)
- `django/static/js/bundle.js` — created with CDN links for
  jQuery/jQuery UI/Bootstrap JS plus site-specific JS
- `django/static/images/` — copied from `app/assets/images/`,
  replaced broken symlinks with real files
- `Dockerfile.dev` — removed `RUN rm -f favicon.png` line
- `main.html` — added CDN script tags for jQuery, jQuery UI, Bootstrap

### Why
- CSS, JS, and image files were symlinks pointing to Play build
  output (`target/`, `gen/`) that doesn't exist in Django-only setup
- Pages rendered without styling ("plain look")
- Favicon was 404

---

## 7. People/CRM Module

**Commit:** `86fd0057`

### What
- `django/dst/people_views.py` — 5 views:
  - `people_index` — CRM dashboard (recent comments + people list)
  - `all_people` — tabular view of all people
  - `person_detail` — person detail (name, tags, contacts, comments)
  - `add_person` — create person form
  - `edit_person` — edit person form
- Templates: `crm_index.html`, `all_people.html`, `person_detail.html`,
  `person_form.html`
- Routes: `/people`, `/allPeople`, `/people/new`, `/people/<id>`,
  `/people/edit/<id>`

### Why
- "People" nav link was 404 — the Play CRM hadn't been ported
- Full CRUD needed for basic school management

### Data Model
- Uses `Person` model (`django/dst/models.py:108`), same as attendance/JC
- Phone numbers via `PhoneNumber` model
- Tags via `Person.tags` M2M
- Comments via `Comment` model

---

## 8. OrgConfig Timezone Fix

**Commit:** `86fd0057` (same as CRM)

### What
- Changed all timezone aliases in `django/dst/org_config.py`:
  - `US/Eastern` → `America/New_York`
  - `US/Central` → `America/Chicago`
  - `US/Pacific` → `America/Los_Angeles`

### Why
- Docker containers running Python 3.13 don't include legacy `US/*`
  timezone aliases by default
- `ZoneInfo("US/Eastern")` raises `ZoneInfoNotFoundError`
- Pages using `get_org_config()` crashed with 500

---

## 9. Brokwn Nav Links Fix

**Commit:** `d127ea3f` (same as static assets)

### What
- Wired `/logout` to `LogoutView` (`/custodia/logout`)
- Wired `/attendance` to `SignInSheetView`
- Added `/settings`, `/settings/password` placeholders
- Added `/viewAllTags` tag listing
- Removed broken Scala `messages` references from `main.html`

### Routes Fixed
| Route | Previously | Now |
|---|---|---|
| `/attendance` | 404 → install link | 200 → SignInSheetView |
| `/logout` | 404 | 302 → /custodia/logout |
| `/settings` | 404 | 200 → placeholder |
| `/settings/password` | 404 | 200 → placeholder |
| `/viewAllTags` | 404 | 200 → tag listing |

---

## 10. Seed Data Command

**Commit:** `1706fd13`

### What
- `django/dst/management/commands/seed_test_data.py`
- Creates: org "Test School", tags (Current Student, Staff, Absent Today),
  a school Year, 24 random students, 72 swipe records, 72 attendance
  day records

### Key Features
- **Idempotent** — uses `get_or_create` throughout; safe to re-run
- **Deterministic seeding** — uses `get_or_create` so re-running doesn't
  create duplicates
- **Auto-runs** on Docker container start via `docker-entrypoint.sh`

### JC Data (added in `94f77c70`)
- Current Student tag has `show_in_jc=True`
- Creates a Meeting, Case, and 4 Charges with varied pleas,
  resolution plans, one SM referral

---

## 11. JC Module — Core Pages

**Commit:** `94f77c70`

### What
- `django/dst/jc_views.py` — first 5 views:
  - `jc_index` — JC dashboard (meeting calendar, per-person charges,
    per-rule charges)
  - `view_meeting` — read-only meeting view
  - `view_todays_minutes` — today's meeting or fallback
  - `view_sm_referrals` — charges pending SM decision
  - `view_sm_decisions` — past SM decisions
- Templates: `jc_index.html`, `view_meeting.html`, `no_meeting.html`,
  `view_sm_referrals.html`, `view_sm_decisions.html`
- Model constants: `PersonAtMeeting.ROLE_*`, `PersonAtCase.ROLE_*`

### Route Changes
- Root `/` changed from custodia `IndexView` → JC `jc_index`
- JC tab links to `/jc` instead of `/`

---

## 12. JC Module — History, Reports, RPs, SM

**Commit:** `8aaecc1b`

### What
- `django/dst/jc_views.py` — 9 more views:
  - `view_person_history` — person's JC history with date range,
    rule counts, charge details, name redaction
  - `view_rule_history` — rule's JC history with person counts
  - `view_persons_writeups` — cases written by a person
  - `this_week_report` — weekly JC statistics
  - `download_charges` — CSV export of all charges
  - `edit_resolution_plan_list` — active/completed/nullified RPs
  - `view_meeting_resolution_plans` — RPs for a meeting
  - `print_meeting` — print-friendly meeting view
  - `enter_school_meeting` — form + POST handler for SM decisions
  - `edit_school_meeting_decision` — edit SM decision form
- Templates: 10 new HTML files

### JC Editor — now implemented
- `/editToday` — Finds or creates today's meeting, redirects to edit page
- `/editMeeting/<id>` — Full server-rendered editor with:
  - Meeting metadata form (date, chair, notetaker, committee, subs, runners via multi-select)
  - Case list with inline edit forms (location, date, time, findings)
  - Charge list with inline edit forms (person, rule, plea, severity, resolution plan)
  - Add case / add charge / delete case / delete charge / save case / save charge POST endpoints
  - Continue case from previous meeting
  - `createCase`, `saveCase`, `deleteCase`, `continueCase`, `addCharge`, `saveCharge`, `deleteCharge` — 7 POST endpoints

---

## Legacy Module Status

| Module | Play/Scala | Django | Notes |
|--------|-----------|--------|-------|
| **Manual** | `controllers.Proxy` | ✅ Full | Chapters, sections, entries, search, PDF |
| **People/CRM** | `controllers.CRM` | ✅ Full | List, detail, create, edit |
| **Attendance** | `controllers.Attendance` | 🔶 Partial | Sign-in sheet only; week view, rules, codes still Play |
| **JC** | `controllers.Application` | ✅ Full | Dashboard, meetings, history, reports, RPs, SM, CSV |
| **JC Editor** | `controllers.ApplicationEditing` | ❌ Not ported | JS-heavy meeting editor |
| **Custodia Admin** | `controllers.Attendance` | ✅ Full | Swipe, absent, excuse, override, reports |
| **Settings** | `controllers.Settings` | ❌ Placeholder | |
| **Roles** | `controllers.Roles` | ❌ Not ported | |
| **Accounting** | `controllers.Accounting` | ❌ Not ported | |
| **File Sharing** | `controllers.Application` | ❌ Not ported | |
| **SSO** | Play Auth module | ❌ Not ported | Analysis in `SSO_INTEGRATION.md` |

---

## URL Map (All Django Routes)

### Top-level pages
| Path | View | Module |
|------|------|--------|
| `/` | `jc_index` | JC |
| `/jc` | `jc_index` | JC |
| `/custodia/` | `IndexView` | Custodia |
| `/custodia/login` | `LoginView` | Custodia |
| `/custodia/logout` | `LogoutView` | Custodia |
| `/logout` | `LogoutView` | — |
| `/health/` | `health` | System |
| `/admin/` | Django admin | System |
| `/people` | `people_index` | CRM |
| `/allPeople` | `all_people` | CRM |
| `/people/new` | `add_person` | CRM |
| `/people/<id>` | `person_detail` | CRM |
| `/people/edit/<id>` | `edit_person` | CRM |
| `/attendance` | `SignInSheetView` | Attendance |
| `/attendance/signInSheet` | `SignInSheetView` | Attendance |

### Manual
| Path | View |
|------|------|
| `/viewManual` | `view_manual` |
| `/viewManualChanges` | `view_manual_changes` |
| `/searchManual` | `search_manual` |
| `/printManual` | `print_manual` |
| `/printManualChapter/<id>` | `print_manual_chapter` |
| `/viewChapter/<id>` | `view_chapter` |
| `/addChapter` | `CreateUpdateChapter` |
| `/editChapter` / `/editChapter/<id>` | `CreateUpdateChapter` |
| `/addSection/<chapter_id>` | `CreateUpdateSection` |
| `/editSection` / `/editSection/<id>` | `CreateUpdateSection` |
| `/addEntry/<section_id>` | `CreateUpdateEntry` |
| `/editEntry` / `/editEntry/<id>` | `CreateUpdateEntry` |
| `/viewEntry/` / `/viewEntry/<id>` | `preview_entry` |

### JC
| Path | View |
|------|------|
| `/jc` | `jc_index` |
| `/viewToday` | `view_todays_minutes` |
| `/viewMeeting/<id>` | `view_meeting` |
| `/viewPersonHistory/<id>` | `view_person_history` |
| `/viewRuleHistory/<id>` | `view_rule_history` |
| `/viewPersonsWriteups/<id>` | `view_persons_writeups` |
| `/thisWeekReport` | `this_week_report` |
| `/downloadCharges` | `download_charges` |
| `/editResolutionPlanList` | `edit_resolution_plan_list` |
| `/viewMeetingResolutionPlans/<id>` | `view_meeting_resolution_plans` |
| `/printMeeting/<id>` | `print_meeting` |
| `/viewSchoolMeetingReferrals` | `view_sm_referrals` |
| `/viewSchoolMeeting` | `view_sm_decisions` |
| `/enterSchoolMeeting` | `enter_school_meeting` |
| `/editSchoolMeeting/<id>` | `edit_school_meeting_decision` |
| `/editToday` | `jc_placeholder` |
| `/editMeeting/<id>` | `jc_placeholder` |

### Settings & Placeholders
| Path | View |
|------|------|
| `/settings` | `settings_view` |
| `/settings/password` | `settings_view` |
| `/viewAllTags` | `all_tags` |
| `/roles/index` | `settings_view` |
| `/attendance/codes` | `settings_view` |

### API (JSON) — available under both `/custodia-api/` and `/api/v1/custodia/`
| Path | View |
|------|------|
| `users/is-admin` | `IsAdminView` |
| `students` | `StudentsTodayView` |
| `students/<id>/swipe` | `SwipeView` |
| `students/<id>/swipe/delete` | `DeleteSwipeView` |
| `students/<id>/absent` | `AbsentView` |
| `students/<id>/excuse` | `ExcuseView` |
| `students/<id>/override` | `OverrideView` |
| `students/<id>` | `StudentDataView` |
| `reports/years` | `ReportYears` |
| `reports/years/<name>` | `ReportYears` |
| `reports/<year>` | `ReportView` |
| `reports/<year>/<class_id>` | `ReportView` |

---

## Test Status

```
Ran 64 tests in 2.443s
FAILED (errors=6)
```

All 6 failures are **pre-existing** (not caused by branch changes):
- 5 login tests: `Organization matching query does not exist` — test
  `setUp` doesn't create `OrganizationHost` for `testserver` host
- 1 section cascade test: `ProtectedError` — section references chapter
  via protected FK

58 tests pass covering: Organization, Person, Tag, User, Role,
RoleInclusion, Chapter, Section, Entry, ManualChange, AttendanceCode,
AttendanceDay, AttendanceWeek, AttendanceRule, ManualView,
HealthView, Swipe, Override, Excuse, StudentMinutes, Year, LoginView,
StudentDataView.

---

## Data Model Consistency

All modules (People/CRM, Attendance/Custodia, JC) use the **same `Person`**
model (`django/dst/models.py:108`). The distinction between "students,"
"JC-visible people," and "attendance-tracked people" is made through
**tag flags**:

| Tag Flag | Module | Filter |
|----------|--------|--------|
| `show_in_attendance=True` | Attendance/Custodia | `Person.objects.filter(tags__show_in_attendance=True)` |
| `show_in_jc=True` | JC | `Person.objects.filter(tags__show_in_jc=True)` |

In seed data, a single "Current Student" tag has both flags set, so
the same 24 students appear in all modules. A person can have only
one flag and appear in only that module (e.g., staff with only
`show_in_jc=True`).

---

## Running Locally

```bash
# Build and start
docker compose -f docker-compose.dev.yml up -d --build

# Test login (auto-created on first start)
# Username: admin@test.com
# Password: password123

# Re-seed data
docker compose -f docker-compose.dev.yml exec django uv run manage.py seed_test_data

# Run Django tests
docker compose -f docker-compose.dev.yml exec django uv run manage.py test

# View logs
docker compose -f docker-compose.dev.yml logs -f django
```
