# Unification Plan — Migration Status

## Current Architecture (After Proxy Flip)

Browser -> Play/Scala (port 9000)
              |
              +-- Proxy -> Django (port 8000) -> ~90% of routes
              |     /, /jc*, /viewMeeting*, etc. (all JC)
              |     /attendance*, /attendance/* (all attendance)
              |     /roles/* (all roles)
              |     /people*, /jsonPeople*, /viewTag*, etc. (all CRM)
              |     /settings*, /settings/* (all settings)
              |     /misc/* (file sharing)
              |     /custodia*, /custodia-api*, /custodia-admin
              |     /viewManual*, /editChapter*, etc. (manual)
              |     /admin*, /silk*, /django-static*
              |     /health/, /login, /logout
              |
              +-- Direct (Play controllers)
              |     /accounting/* (19 routes - intentionally skipped)
              |     /authenticate/*, /fb-delete-info, /login (SSO/auth)
              |
              +-- Static assets
                    /assets/* (Play's public directory)

All routes except Accounting and SSO now proxy to Django.
The Play server is only needed for Accounting, SSO callbacks, and
as a reverse proxy.

## What's Fully in Django (100% ported)

| Module | Routes | Django Views |
|--------|--------|-------------|
| Manual | ~15 | view_manual, edit chapter/section/entry, search, print, PDF |
| People/CRM | ~25 | index, all, detail, create, edit, tags CRUD, task lists, comments, JSON autocomplete |
| JC | ~40 | dashboard, meetings, person/rule history, writeups, weekly report, resolution plans, SM referrals/decisions, editor with POST endpoints, CSV download, AJAX endpoints |
| Custodia | ~15 | React SPA shell, login/logout, swipe API, absent/excuse/override, reports, years |
| Attendance | ~20 | sign-in sheet (React), codes CRUD, rules CRUD, week view, reports, PINs, off-campus, download, per-person report, check-in view |
| Roles | ~6 | index with listing, new role, records, AJAX update/delete |
| Settings | ~10 | index, password change, access control (users/roles/IPs), notifications, checklists, user edit |
| Misc/File Sharing | ~6 | file sharing index, view files (stubs) |
| Health | 1 | JSON health check |
| Login/Logout | 3 | login form, logout handler, /login redirect |

## What Remains in Play

### Accounting (19 routes - intentionally skipped)
All `/accounting/*` routes - balances, transactions, accounts, reports.

### SSO / Auth (5 routes - Play-auth module dependency)
- `/authenticate/:provider` - Facebook/Google SSO callbacks
- `/authenticate/:provider/denied` - OAuth denial
- `/fb-delete-info` - Facebook data deletion
- `/login` - Play's own login form (POST handler)
- `/logout` - Play-auth logout (Django also handles this at /logout)

### Static Assets (2 routes)
- `/assets/*file` - Play's public directory (images, fonts from legacy)
- `/robots.txt` - robots.txt

## Migration Summary

| Phase | What | Status | Routes |
|-------|------|--------|--------|
| 1 | Attendance proxy flip | Done | 24 attendance routes |
| 2 | Check-in app views | Done | 4 check-in routes (basic views) |
| 3 | Roles proxy flip | Done | 6 roles routes |
| 4 | People/CRM proxy flip | Done | 25 people routes |
| 5 | Settings proxy flip | Done | 18 settings routes |
| 6 | Remove Play dependency | Not started | Requires Play to be removed from Docker/CI |

## Next Steps to Remove Play Dependency

1. Migrate SSO to django-allauth (see SSO_INTEGRATION.md)
2. Migrate Accounting module (when desired)
3. Copy static assets from app/assets/ to django/static/
4. Update docker-compose.yml to remove Play service
5. Update nginx config to point directly at Django
6. Update CI/CD pipeline to skip Play build
7. Delete legacy app/, project/, modelsLibrary/, conf/ directories
