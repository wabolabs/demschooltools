"""
E2E smoke tests using Playwright.

Checks that all major application routes return HTTP 200 and contain
expected content. Run against the dev server:

    uv run python tests/e2e_smoke.py

Requires: playwright (installed in venv)
"""
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'demschooltools.settings_ci'

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
LOGIN = "admin@test.com"
PASS = "password123"

ROUTES = {
    "JC": [
        ("/jc", "Minutes"),
        ("/viewToday", None),
        ("/viewMeeting/1", "minutes"),
        ("/viewPersonHistory/1", "history"),
        ("/thisWeekReport", "Weekly"),
        ("/editResolutionPlanList", "Resolution"),
        ("/viewSchoolMeetingReferrals", "School"),
        ("/viewSchoolMeeting", "School"),
        ("/editMeeting/1", "minutes"),
    ],
    "People": [
        ("/people", "Recent"),
        ("/allPeople", "people"),
        ("/people/1", None),
    ],
    "Attendance": [
        ("/attendance", None),
        ("/attendance/codes", "Absence"),
        ("/attendance/rules", "Attendance"),
        ("/attendance/viewWeek", "Week"),
        ("/attendance/pins", "PINs"),
        ("/attendance/offCampusTime", "Off"),
        ("/attendance/reports", "Reports"),
    ],
    "Other": [
        ("/roles/index", "Roles"),
        ("/settings/access", "Users"),
        ("/settings/password", "Change"),
        ("/settings/notifications", "Notification"),
        ("/viewManual", "Manual"),
        ("/viewAllTags", "Tags"),
        ("/misc/viewFiles", "Shared"),
    ],
}


def run():
    failed = []

    def check(page, url, expect_text=None):
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" and "favicon" not in msg.text.lower() else None)
        resp = page.goto(f"{BASE}{url}", wait_until="networkidle", timeout=15000)
        status = resp.status if resp else 0
        if status != 200:
            failed.append(f"{url}: HTTP {status}")
            return status
        if expect_text:
            try:
                page.locator(f"h3:has-text('{expect_text}')").wait_for(timeout=3000)
            except:
                try:
                    page.locator(f"h2:has-text('{expect_text}')").wait_for(timeout=2000)
                except:
                    page.locator(f"h1:has-text('{expect_text}')").wait_for(timeout=2000)
        if errors:
            js_errs = [e for e in errors if "404" not in e]
            if js_errs:
                failed.append(f"{url}: JS errors: {js_errs[:2]}")
        return status

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)

        # Login
        print("Logging in...", end=" ")
        page.goto(f"{BASE}/custodia/login")
        page.fill("#username", LOGIN)
        page.fill("#password", PASS)
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        if "/jc" in page.url:
            print("OK")
        else:
            failed.append(f"Login failed: landed on {page.url}")
            print(f"FAILED: {page.url}")

        # Test all route groups
        for group, routes in ROUTES.items():
            print(f"\n{group}:")
            for url, text in routes:
                s = check(page, url, expect_text=text)
                status = "OK" if s == 200 else f"FAIL({s})"
                print(f"  {url:40s} {status}")

        # Test nav links from JC page
        print("\nNav links from /jc:")
        page.goto(f"{BASE}/jc", wait_until="networkidle")
        hrefs = page.eval_on_selector_all("a[href^='/']", "els => els.map(e => e.getAttribute('href')).filter(h => h && !h.includes('static') && h !== '#' && h !== '/logout' && h !== '/login')")
        broken = 0
        for href in set(hrefs):
            resp = page.goto(f"{BASE}{href}", wait_until="networkidle")
            if resp and resp.status == 404:
                print(f"  BROKEN: {href}")
                broken += 1
        print(f"  Checked {len(set(hrefs))} links, {broken} broken" if broken == 0 else f"  {broken} broken links found!")

        browser.close()

    print(f"\n{'='*40}")
    if failed:
        print(f"FAILURES ({len(failed)}):")
        for f in failed:
            print(f"  - {f}")
        return 1
    else:
        print("ALL TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(run())
