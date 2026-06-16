from django.contrib.auth.decorators import login_required as django_login_required
from django.db.transaction import atomic
from django.shortcuts import redirect
from django.template.loader import render_to_string

from dst.models import AllowedIp, User, UserRole
from dst.org_config import get_org_config
from dst.utils import DstHttpRequest, render_main_template


def login_required():
    return django_login_required(login_url="/login")


@login_required()
def settings_index(request: DstHttpRequest):
    return render_main_template(
        request,
        "settings",
        render_to_string("settings.html", request=request),
        "Settings",
    )


@login_required()
def settings_access(request: DstHttpRequest):
    from django import forms

    class NewUserForm(forms.Form):
        name = forms.CharField(max_length=255, label="Name")
        email = forms.CharField(max_length=255, label="Email")

    users = User.objects.filter(organization=request.org).order_by("name")
    active_users = []
    inactive_users = []
    for u in users:
        user_roles = set(UserRole.objects.filter(user=u).values_list("role", flat=True))
        entry = {"user": u, "roles": user_roles}
        if u.is_active:
            active_users.append(entry)
        else:
            inactive_users.append(entry)

    allowed_ips = AllowedIp.objects.filter(organization=request.org)

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "add_user":
            name = request.POST.get("name", "")
            email = request.POST.get("email", "")
            if name and email:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password="changeme",
                    name=name,
                    organization=request.org,
                )
                return redirect("/settings/access")
        elif action == "save_ip":
            ip = request.POST.get("allowed_ip", "").strip()
            AllowedIp.objects.filter(organization=request.org).delete()
            if ip:
                AllowedIp.objects.create(ip=ip, organization=request.org)
            return redirect("/settings/access")
        elif action == "toggle_role":
            user_id = request.POST.get("user_id")
            role = request.POST.get("role")
            if user_id and role:
                try:
                    u = User.objects.get(id=user_id, organization=request.org)
                except User.DoesNotExist:
                    pass
                else:
                    if u.hasRole(role):
                        UserRole.objects.filter(user=u, role=role).delete()
                    else:
                        UserRole.objects.create(user=u, role=role)
            return redirect("/settings/access")
        elif action == "toggle_active":
            user_id = request.POST.get("user_id")
            if user_id:
                try:
                    u = User.objects.get(id=user_id, organization=request.org)
                except User.DoesNotExist:
                    pass
                else:
                    u.is_active = not u.is_active
                    u.save()
            return redirect("/settings/access")

    all_roles = [
        ("accounting", "Accounting"),
        ("edit-roles", "Roles"),
        ("view-jc", "View JC"),
        ("edit-rps", "Edit RPs"),
        ("edit-recent-jc", "Edit 7d JC"),
        ("edit-recent-31-jc", "Edit 31d JC"),
        ("edit-all-jc", "Edit All JC"),
        ("edit-manual", "Edit Manual"),
        ("attendance", "Attendance"),
        ("all-access", "All Access"),
        ("checkin-app", "Check-in App"),
    ]

    return render_main_template(
        request,
        "settings",
        render_to_string(
            "settings_access.html",
            {
                "active_users": active_users,
                "inactive_users": inactive_users,
                "allowed_ips": allowed_ips,
                "all_roles": all_roles,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Users & Access",
        selected_button="settings_access",
    )


@login_required()
def settings_password(request: DstHttpRequest):
    error = ""
    success = ""
    if request.method == "POST":
        current = request.POST.get("current_password", "")
        new_pass = request.POST.get("new_password", "")
        confirm = request.POST.get("confirm_password", "")
        if not request.user.check_password(current):
            error = "Current password is incorrect."
        elif not new_pass:
            error = "New password cannot be empty."
        elif new_pass != confirm:
            error = "Passwords do not match."
        else:
            request.user.set_password(new_pass)
            request.user.save()
            success = "Password changed successfully."

    return render_main_template(
        request,
        "settings",
        render_to_string(
            "settings_password.html",
            {
                "error": error,
                "success": success,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Change Password",
    )


@login_required()
def settings_view(request: DstHttpRequest, **kwargs):
    return settings_index(request)
