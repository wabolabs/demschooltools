# SSO Integration Analysis

> Branch: `analysis/project-audit-and-improvements`
> Date: 2026-06-15

---

## Current State

The project has **two parallel auth systems**:

```
┌──────────────┐     PLAY_SESSION JWT cookie      ┌──────────────┐
│  Play/Scala  │ ───────────────────────────────►  │   Django     │
│  (port 9000) │      HS256 signed, contains       │  (port 8000) │
│              │      pa.u.id + pa.p.id            │              │
│              │                                    │              │
│  Auth methods:                                   │  Auth reads: │
│  • Email/password (EvanAuthProvider)             │  • JWT cookie │
│  • Google OAuth2 (GoogleAuthProvider)             │  • IP whitelist
│  • Facebook OAuth2 (FacebookAuthProvider)        │              │
└──────────────┘                                   └──────────────┘
```

**Key detail**: All SSO flows currently route through Play's `play-authenticate` module. The browser never talks to Google/Facebook directly for auth — Play handles the OAuth redirects and token exchange, then writes the `PLAY_SESSION` cookie.

### Existing infrastructure

| Component | State |
|-----------|-------|
| Google OAuth client ID | `477883553858.apps.googleusercontent.com` (from `conf/play-authenticate/mine.conf`) |
| Google OAuth client secret | Env var `GOOGLE_CLIENT_SECRET` |
| Facebook OAuth app ID | `306846672797935` |
| Facebook OAuth secret | Env var `FACEBOOK_CLIENT_SECRET` |
| Django `LinkedAccount` model | Maps `(provider_key, provider_user_id)` → `User` |
| Django `User.email` | Used for "evan-auth-provider" lookups |
| Django `LoginView` | Now handles email/password auth natively (decoupled in P1) |

---

## Option A: django-allauth (Recommended for Quickest Path)

[`django-allauth`](https://docs.allauth.org/) is the de facto standard Django social auth library. Actively maintained, supports 50+ providers, built-in email verification, and MFA.

### Implementation Plan

#### Step 1: Install & Configure

```bash
cd django
uv add "django-allauth~=65.0"
```

Add to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
]
```

Add to `AUTHENTICATION_BACKENDS` in `settings.py`:

```python
AUTHENTICATION_BACKENDS = [
    "demschooltools.auth.PlaySessionBackend",
    "allauth.account.auth_backends.AuthenticationBackend",  # new
]
```

Add `allauth` URLs:

```python
# urls.py
urlpatterns += [
    path("accounts/", include("allauth.urls")),
]
```

#### Step 2: Create Custom Social Adapter

`django-allauth` needs to map social accounts to the project's custom `User` model and the `LinkedAccount` table. Create `django/dst/social_adapter.py`:

```python
import uuid

import jwt
from allauth.account.utils import perform_login
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect
from django.shortcuts import redirect

from dst.models import LinkedAccount


class DstSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Maps allauth social logins to the DST User + LinkedAccount model."""

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        if sociallogin.is_existing:
            return user

        # Check if a user with this email already exists
        existing = self._get_user_model().objects.filter(email=user.email).first()
        if existing:
            user = existing

        user.save()

        # Create or update LinkedAccount for PlaySession compatibility
        provider = sociallogin.account.provider
        uid = sociallogin.account.uid
        LinkedAccount.objects.get_or_create(
            provider_key=provider,
            provider_user_id=uid,
            defaults={"user": user},
        )

        sociallogin.user = user
        return user

    def on_authentication_error(self, request, provider, error, exception, extra_context):
        # Log the error via Rollbar
        import rollbar
        rollbar.report_message(f"Social auth error: {provider.id} - {error}")
        return super().on_authentication_error(
            request, provider, error, exception, extra_context
        )
```

Wire it in `settings.py`:

```python
SOCIALACCOUNT_ADAPTER = "dst.social_adapter.DstSocialAccountAdapter"
```

#### Step 3: Generate PLAY_SESSION JWT After SSO Login

Create a signal handler that fires after a successful social login, so the `PlaySessionMiddleware` still works:

```python
# django/dst/social_signals.py
import uuid

import jwt
from allauth.socialaccount.signals import social_account_added
from django.conf import settings
from django.dispatch import receiver
from django.shortcuts import redirect


@receiver(social_account_added)
def handle_social_login(request, sociallogin, **kwargs):
    """Set PLAY_SESSION cookie after social login."""
    user = sociallogin.user
    token = jwt.encode(
        {
            "data": {
                "pa.u.id": user.email,
                "pa.p.id": "evan-auth-provider",
                "pa.s.id": str(uuid.uuid4()),
            },
        },
        settings.APPLICATION_SECRET,
        algorithm="HS256",
    )
    response = redirect("/custodia")
    response.set_cookie("PLAY_SESSION", token)
    raise ImmediateHttpResponse(response)
```

#### Step 4: Add SSO Buttons to Login Template

Add to `django/custodia/templates/login.html` (inside the panel):

```html
<div class="panel panel-default">
  <div class="panel-heading">Sign in with:</div>
  <div class="panel-body">
    <a href="{% url 'google_login' %}" class="btn btn-danger">
      Google
    </a>
    <a href="{% url 'facebook_login' %}" class="btn btn-primary">
      Facebook
    </a>
  </div>
</div>
```

(allauth automatically creates URL names like `google_login`, `facebook_login` when providers are registered.)

#### Step 5: Configure Google OAuth Credentials

In the Django admin (`/admin/socialaccount/socialapp/`), create a SocialApp entry:

- Provider: Google
- Client ID: `477883553858.apps.googleusercontent.com`
- Secret key: `$GOOGLE_CLIENT_SECRET`
- Sites: (add the school's site)

Also update the Google OAuth consent screen to include the new redirect URI:
```
https://<school>.demschooltools.com/accounts/google/login/callback/
```

#### Step 6: Database Migration

Create a migration to add allauth's tables:

```bash
uv run manage.py makemigrations
uv run manage.py migrate
```

#### Step 7: Testing

```python
# django/dst/tests/test_social_auth.py
from django.test import TestCase
from django.urls import reverse


class SocialAuthTests(TestCase):
    def test_google_login_url_resolves(self):
        url = reverse("google_login")
        self.assertIn("accounts/google/login", url)

    def test_login_page_contains_sso_links(self):
        response = self.client.get("/custodia/login")
        self.assertContains(response, "Google")
        self.assertContains(response, "google_login")
```

### Considerations

- **`SOCIALACCOUNT_EMAIL_REQUIRED`**: Set to `True` to enforce email from provider.
- **`SOCIALACCOUNT_EMAIL_VERIFICATION`**: Set to `"none"` since Google already verifies.
- **Organization assignment**: For new users created via SSO, you'll need to determine which organization they belong to (using the host header, similar to `PlaySessionMiddleware`).

---

## Option B: Authentik (Recommended for Multi-App / Future-Proof)

[Authentik](https://goauthentik.io/) is a self-hosted identity provider that can sit **in front of** both Play and Django, eventually replacing both as the auth layer.

### Architecture

```
┌──────────┐
│  Browser │
└────┬─────┘
     │
     ▼
┌──────────────────────────────────────────────┐
│           Authentik (port 443)                │
│  • OIDC Provider                              │
│  • LDAP / SAML / Proxy                        │
│  • MFA / RBAC / Event logging                 │
└──┬───────────────────────┬───────────────────┘
   │                       │
   ▼                       ▼
┌──────────────┐   ┌──────────────┐
│   Django     │   │  Play/Scala  │
│  (via OIDC)  │   │ (via OIDC or │
│              │   │  proxy auth) │
└──────────────┘   └──────────────┘
```

### Implementation Plan

#### Setup Authentik

Add to `docker-compose.yml`:

```yaml
services:
  authentik:
    image: ghcr.io/goauthentik/server:latest
    command: server
    environment:
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY}
      AUTHENTIK_BOOTSTRAP_EMAIL: admin@demschooltools.com
      AUTHENTIK_BOOTSTRAP_PASSWORD: ${AUTHENTIK_BOOTSTRAP_PASSWORD}
    volumes:
      - authentik_data:/data
    ports:
      - "443:443"
      - "9000:9000"

  authentik-worker:
    image: ghcr.io/goauthentik/server:latest
    command: worker
    environment:
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY}
    volumes:
      - authentik_data:/data
    depends_on:
      - authentik

volumes:
  authentik_data:
```

#### Configure Authentik OIDC Provider

1. Create an OIDC provider in Authentik for Django
2. Create an application linked to that provider
3. Note the Client ID and Client Secret

#### Wire Django to Authentik via django-allauth

Use allauth's generic OIDC provider:

```python
INSTALLED_APPS += [
    "allauth.socialaccount.providers.openid_connect",
]
```

Set the provider configuration in settings (or via admin):

```python
SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "authentik",
                "name": "Authentik",
                "client_id": os.environ["AUTHENTIK_CLIENT_ID"],
                "secret": os.environ["AUTHENTIK_CLIENT_SECRET"],
                "settings": {
                    "server_url": os.environ.get(
                        "AUTHENTIK_SERVER_URL",
                        "https://auth.demschooltools.com/application/o/django/.well-known/openid-configuration",
                    ),
                },
            },
        ],
    },
}
```

#### Migrate Users

Authentik can import existing users via CSV or LDAP. After migration:
1. Each DST User gets an Authentik account
2. The `LinkedAccount` table is populated with `provider_key="authentik"` and `provider_user_id=authentik_user_uuid`
3. Django's `PlaySessionMiddleware` still works (PLAY_SESSION JWT is generated post-login)

### Considerations

- **Self-hosted**: You run Authentik on your infrastructure. Adds operational complexity but gives full control.
- **Cost**: Free & open source (no per-user licensing).
- **Features**: MFA (TOTP, WebAuthn), LDAP, SAML, RBAC, event logging, password policies.
- **Migration path**: Can run alongside Play auth during transition. Start with new users in Authentik, migrate existing ones gradually.

---

## Option C: Minimal — Direct Google OAuth without a Library

If you want to minimize dependencies, you can implement Google OAuth directly using `requests` and `pyjwt` (both already in the project).

### Approach

1. Add a `GoogleLoginView` that:
   - Redirects to Google's authorization URL
   - Handles the callback (exchanges code for token)
   - Fetches user info from Google
   - Creates/finds the User and LinkedAccount
   - Generates PLAY_SESSION JWT
   - Redirects to /custodia

2. No new dependencies. Total ~150 lines of new code.

### Pros/Cons

| Pro | Con |
|-----|-----|
| Zero new dependencies | Manual OAuth state handling |
| Total control over the flow | No built-in CSRF protection for the callback |
| Directly uses existing `LinkedAccount` model | Need to implement token refresh yourself |
| | No Facebook support without duplicating effort |

**Not recommended** unless you only need Google and want zero library risk. django-allauth is more maintainable.

---

## Comparison Matrix

| Criteria | django-allauth (A) | Authentik (B) | Direct OAuth (C) |
|----------|-------------------|---------------|-------------------|
| **Effort** | 2–3 days | 1–2 weeks | 1 day |
| **New dependencies** | `django-allauth` | Authentik containers, `django-allauth` | None |
| **Google SSO** | ✅ Built-in provider | ✅ Via OIDC | ✅ Manual |
| **Facebook SSO** | ✅ Built-in provider | ✅ Via OIDC | ❌ Manual |
| **MFA** | Via allauth 2FA | ✅ Built-in (TOTP, WebAuthn) | ❌ |
| **User management UI** | Admin only | ✅ Self-service portal | ❌ |
| **Event audit log** | Limited | ✅ Full audit trail | ❌ |
| **LDAP / AD sync** | ❌ | ✅ | ❌ |
| **Play decommission** | Still need Play for Play→Django auth | Could fully replace Play auth | Still need Play for Facebook |
| **Operational cost** | Low | Medium (run Authentik) | Low |
| **Migration risk** | Low | Medium | Low |

---

## Recommended Migration Path

### Phase 1 (Current): Django handles email/password login ✅ Done
LoginView no longer proxies to Play. Users can log in with email/password directly via Django.

### Phase 2: Add django-allauth with Google SSO (2–3 days)
**Recommended**: Add Google login buttons. Users can choose email/password or Google.
- Keep Play running for Facebook SSO users.
- New users created via Google SSO get proper organization assignment.
- Allauth tables live alongside existing `LinkedAccount` table.

### Phase 3: Evaluate Authentik (if multi-app SSO is needed)
If you want to:
- Decommission Play entirely
- Offer MFA to schools
- Centralize user management across multiple apps
- Have a self-service password reset portal

Then deploy Authentik, migrate users, and configure OIDC for Django.

### Phase 4: Decommission Play auth
Once all users have migrated to email/password (Django) or SSO (allauth/Authentik), the Play server is no longer needed for auth. The `PLAY_SESSION` JWT generation moves fully to Django.

---

## Open Questions

1. **Organization assignment**: When a new user signs up via Google SSO, how do we determine which school they belong to? Options:
   a. Use the request hostname (as `PlaySessionMiddleware` does)
   b. Let the user choose from a list
   c. Require admin approval

2. **User provisioning**: Should SSO create User accounts automatically, or should an admin pre-provision them?

3. **Facebook SSO**: Do any schools actively use it? (The Play config shows it's configured, but it may have low usage.)

4. **Play decommission timeline**: Is there a target date for removing the Play server? This affects whether Authentik is worth the investment now.

5. **Redirect URIs**: The Google OAuth credentials are shared across all schools. After migration, each school's subdomain needs to be added to the Google Cloud Console "Authorized redirect URIs" list (e.g., `https://tcs.demschooltools.com/accounts/google/login/callback/`).
