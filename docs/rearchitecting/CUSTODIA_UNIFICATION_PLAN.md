# Custodia & Attendance Unification Plan

## Current State

There are two separate systems for attendance tracking:

### Custodia (Real-time Electronic Kiosk)
- **Location**: `react/custodia/js/` (legacy React SPA)
- **Routes**: `react/custodia/js/app.jsx` (HashRouter: `#/students`, `#/students/:id`, `#/reports`)
- **UI**: Bootstrap 3 (CDN) + Font Awesome, class components, Flux-style stores (EventEmitter)
- **Backend**: `django/custodia/views.py` — 12 API endpoints under `/custodia-api/`
- **Models**: Swipe, Override, Excuse, StudentRequiredMinutes, Year
- **Template**: `django/custodia/templates/index.html` (standalone full-page SPA)
- **Bundle**: `custodia-<hash>.js` (built by Vite)

### Attendance Sign-In Sheet (Printable PDF Roster)
- **Location**: `react/pages/SignInSheetPage/` (modern React)
- **Routes**: `react/App.jsx` (BrowserRouter: `/attendance/signInSheet`)
- **UI**: MUI v5, functional components + hooks, client-side PDF via `@react-pdf/renderer`
- **Backend**: `django/dst/attendance_views.py` SignInSheetView (bootstraps data, no API calls)
- **Models**: Person + Tag only (read-only)
- **Template**: `django/dst/templates/sign_in_sheet.html` (embedded in main.html nav)
- **Bundle**: `reactapp-<hash>.js` (built by Vite)

### Integration Point
The `sync_custodia_and_dst()` function in `custodia/views.py` bridges the two:
Custodia swipes are written into `AttendanceDay.start_time`/`end_time`, making
Custodia data visible in the Attendance module.

---

## Problems with Current Architecture

1. **Duplicate frontend frameworks**: Bootstrap 3 (Custodia) vs MUI v5 (modern app).
   Two separate React bundles, different design systems, inconsistent UX.

2. **Legacy state management**: Custodia uses Flux stores with manual EventEmitter
   listeners. No hooks, no context, no modern patterns.

3. **Separate navigation**: Custodia has its own internal nav bar (Home, Reports,
   Logout), while the Attendance sheet uses main.html's tab nav.
   Users see two different navigation systems depending on which tab they click.

4. **Two separate bundles**: Both built by the same Vite config but independent.
   Shared components (PersonPicker, tag filtering, date handling) are duplicated.

5. **No unified attendance dashboard**: A school admin has no single place to see
   "today's attendance overview" — they must toggle between Custodia (live swipes)
   and Attendance (codes, rules, week view, reports).

---

## Unification Strategy

### Phase 1: Modernize Custodia Frontend (3-5 days)

Port the legacy Custodia HashRouter app into the modern React SPA structure.

**Steps:**
1. Create new pages under `react/pages/CustodiaPage/`:
   - `StudentTable` — kiosk dashboard (4-column: Absent/Not Yet In/In/Out)
   - `StudentDetail` — per-student detail with heatmap, swipe listing
   - `StudentReports` — report dashboard with MUI DataGrid
2. Port the Flux stores to React hooks + Context:
   - `useCustodiaApi()` hook wrapping all `/custodia-api/*` calls
   - `useStudentStore()` hook (replaces StudentStore + StudentActionCreator)
   - `useReportStore()` hook (replaces reportstore + reportactioncreator)
3. Use existing shared MUI components from `react/components/`
4. Replace Bootstrap 3 markup with MUI equivalents

**After this phase:**
- Single React bundle (`reactapp`) handles both Custodia and Sign-In Sheet
- Bootstrap 3 is fully removed
- `custodia` entry point can be deleted from vite.config.js
- `custodia_css` entry point can be deleted

### Phase 2: Unified Routing (1-2 days)

Merge Custodia routes into the modern BrowserRouter.

**Steps:**
1. In `react/App.jsx`, add Custodia routes:
   ```jsx
   { path: '/custodia', element: <CustodiaApp /> },
   { path: '/custodia/students', element: <StudentTable /> },
   { path: '/custodia/students/:id', element: <StudentDetail /> },
   { path: '/custodia/reports', element: <StudentReports /> },
   ```
2. Update Django URL config: `/custodia` serves the React app as an embedded page
   (using `render_main_template` instead of the standalone template)
3. Update `main.html` Custodia tab to link to `/custodia` (not standalone)

**After this phase:**
- Custodia appears within the main nav tab system (not standalone)
- Single React app handles everything
- No more HashRouter — clean BrowserRouter URLs

### Phase 3: Unified Dashboard (2-3 days)

Create a central Attendance Dashboard that combines Custodia and Attendance data.

**Steps:**
1. New page at `/attendance` (replacing the current redirect to sign-in sheet):
   - Side-by-side or tabbed view showing:
     - Today's swipe summary (from Custodia)
     - Today's attendance codes (from AttendanceDay)
     - Quick actions: sign in/out, mark absent, excuse, override
     - Links to week view, reports, codes, rules, PINs
2. The existing attendance sub-pages (codes, rules, week, reports, off-campus,
   PINs) remain at their current URLs but get a visual refresh.

**After this phase:**
- `/attendance` is a unified landing page, not just a redirect
- Admin sees both Custodia and Attendance data in one place
- Separate Attendance/Custodia nav tabs can be merged into one "Attendance" tab

### Phase 4: Template Consolidation (1 day)

Remove the standalone Custodia template and use main.html for everything.

**Steps:**
1. Delete `django/custodia/templates/index.html`
2. Delete `django/custodia/templates/login.html` (login is already at `/login`)
3. Create a new Django view `AttendanceDashboardView` at `/attendance` that
   renders the unified dashboard through `render_main_template`
4. Move any remaining Custodia-specific logic into `dst/attendance_views.py`

**After this phase:**
- `django/custodia/templates/` is empty — can be deleted
- All pages use the same `main.html` layout
- Consistent nav, consistent styling

### Phase 5: Cleanup (1 day)

Remove legacy code and update configs.

**Steps:**
1. Remove `custodia` and `custodia_css` entry points from `vite.config.js`
2. Remove `react/custodia/` directory entirely
3. Remove `django/custodia/static/` if any
4. Update Django URL patterns: remove `/custodia/` standalone handler,
   integrate into main attendance router
5. Update AGENTS.md

---

## File Changes Summary

### Files to Create
```
react/pages/CustodiaPage/
  CustodiaPage.jsx       — New Custodia app wrapper
  StudentTable.jsx       — Kiosk dashboard (ported from studenttable.jsx)
  StudentDetail.jsx      — Per-student detail (ported from student.jsx)
  StudentReports.jsx     — Reports dashboard (ported from studentreports.jsx)

react/hooks/
  useCustodiaApi.js      — API hook for /custodia-api/* endpoints
  useStudentStore.js     — Student state management hook
  useReportStore.js      — Report state management hook

django/dst/templates/
  attendance_dashboard.html  — Unified attendance dashboard
```

### Files to Modify
```
react/App.jsx            — Add Custodia routes to BrowserRouter
react/vite.config.js     — Remove custodia/custodia_css entry points

django/demschooltools/urls.py  — Update Custodia route to use main template
django/demschooltools/templates/main.html  — Update Custodia tab link

django/dst/attendance_views.py  — Add AttendanceDashboardView
```

### Files to Delete
```
react/custodia/                     — Entire directory (legacy Flux app)
django/custodia/templates/index.html  — Standalone SPA shell
django/custodia/templates/login.html  — Duplicate login page
```

### Files Unchanged
```
django/custodia/views.py           — API endpoints (still needed)
django/custodia/models.py          — Data models (still needed)
django/custodia/serializers.py     — DRF serializers (still needed)
django/custodia/tests.py           — Tests (still needed)
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Porting Flux stores loses edge cases | Medium | Write tests for each API flow before porting; compare output |
| Bootstrap 3 to MUI visual mismatch | Low | Custodia has simple card/table layouts that map cleanly to MUI |
| Breaking existing Custodia users | High | Keep legacy bundle serving alongside new one during transition |
| Swipe timing/validation bugs | Medium | Wrap swipe logic in `useSwipeLogic` hook with unit tests |
| Missing IE11 support (MUI v5) | Low | Already not supported by modern React app; same applies |

## Rollout Strategy

1. **Phase 1-2 in parallel**: New pages live side by side with legacy
   (both bundles serve simultaneously). Legacy app's HashRouter routes still work.
2. **Phase 3**: Add dashboard with feature flags (show_attendance controls visibility).
3. **Phase 4**: Remove legacy template, switch custodia/ to embedded mode.
4. **Phase 5**: Delete legacy code after verifying no one hits the old URLs.

Total estimated effort: **8-12 days** depending on testing depth.
