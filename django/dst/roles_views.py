from django.contrib.auth.decorators import login_required as django_login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone

from dst.models import Person, Role, RoleRecord, RoleRecordMember, UserRole
from dst.org_config import get_org_config
from dst.utils import DstHttpRequest, render_main_template

ROLE_TYPES = [(0, "Individual"), (1, "Committee"), (2, "Group")]
ELIGIBILITY = [(0, "Anyone"), (1, "Staff Only"), (2, "Student Only")]


def login_required():
    return django_login_required(login_url="/login")


@login_required()
def roles_index(request: DstHttpRequest):
    org_config = get_org_config(request.org)
    individual_term = getattr(org_config.org, "roles_individual_term", "Individual") or "Individual"
    committee_term = getattr(org_config.org, "roles_committee_term", "Committee") or "Committee"
    group_term = getattr(org_config.org, "roles_group_term", "Group") or "Group"
    type_labels = {0: individual_term, 1: committee_term, 2: group_term}
    elig_labels = {0: "Anyone", 1: "Staff Only", 2: "Student Only"}

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "create":
            name = request.POST.get("name", "")
            rtype = int(request.POST.get("type", 0))
            eligibility = int(request.POST.get("eligibility", 0))
            notes = request.POST.get("notes", "")
            description = request.POST.get("description", "")
            if name:
                Role.objects.create(
                    organization=request.org,
                    name=name,
                    type=rtype,
                    eligibility=eligibility,
                    notes=notes,
                    description=description,
                )
        elif action == "update":
            role_id = request.POST.get("role_id")
            try:
                role = Role.objects.get(id=role_id, organization=request.org)
            except Role.DoesNotExist:
                pass
            else:
                role.name = request.POST.get("name", role.name)
                role.type = int(request.POST.get("type", role.type))
                role.eligibility = int(request.POST.get("eligibility", role.eligibility))
                role.notes = request.POST.get("notes", role.notes)
                role.description = request.POST.get("description", role.description)
                role.save()
        elif action == "delete":
            role_id = request.POST.get("role_id")
            Role.objects.filter(id=role_id, organization=request.org).delete()
        elif action == "toggle_active":
            role_id = request.POST.get("role_id")
            try:
                role = Role.objects.get(id=role_id, organization=request.org)
            except Role.DoesNotExist:
                pass
            else:
                role.is_active = not role.is_active
                role.save()
        return redirect("/roles/index")

    roles = Role.objects.filter(organization=request.org).order_by("type", "name")
    people = Person.objects.filter(organization=request.org).order_by("display_name", "first_name")

    return render_main_template(
        request,
        "roles",
        render_to_string(
            "roles_index.html",
            {
                "roles": roles,
                "people": people,
                "type_labels": type_labels,
                "elig_labels": elig_labels,
                "org_config": org_config,
                "can_edit": request.user.hasRole(UserRole.ROLES),
            },
            request=request,
        ),
        "Roles",
        selected_button="roles_index",
    )


@login_required()
def roles_records(request: DstHttpRequest):
    person_id = request.GET.get("person_id")
    person = None
    entries = []
    if person_id:
        try:
            person = Person.objects.get(id=person_id, organization=request.org)
        except Person.DoesNotExist:
            pass
        if person:
            memberships = RoleRecordMember.objects.filter(person=person).select_related("role_record__role")
            role_map = {}
            for m in memberships:
                rr = m.role_record
                key = rr.role_id
                if key not in role_map:
                    role_map[key] = {
                        "role_name": rr.role_name,
                        "records": [],
                    }
                role_map[key]["records"].append({
                    "start_date": rr.date_created,
                    "person_name": m.person_name or (person.get_name() if person else ""),
                })
            entries = list(role_map.values())

    people = Person.objects.filter(organization=request.org).order_by("display_name", "first_name")
    return render_main_template(
        request,
        "roles",
        render_to_string(
            "roles_records.html",
            {
                "person": person,
                "entries": entries,
                "people": people,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Roles Records",
        selected_button="roles_records",
    )


@login_required()
def roles_new(request: DstHttpRequest):
    org_config = get_org_config(request.org)
    if request.method == "POST":
        name = request.POST.get("name", "")
        rtype = int(request.POST.get("type", 0))
        eligibility = int(request.POST.get("eligibility", 0))
        notes = request.POST.get("notes", "")
        description = request.POST.get("description", "")
        if name:
            Role.objects.create(
                organization=request.org,
                name=name,
                type=rtype,
                eligibility=eligibility,
                notes=notes,
                description=description,
            )
        return redirect("/roles/index")

    return render_main_template(
        request,
        "roles",
        render_to_string(
            "roles_new.html",
            {
                "org_config": org_config,
            },
            request=request,
        ),
        "New Role",
        selected_button="roles_new",
    )


@login_required()
def roles_update(request: DstHttpRequest, role_id: int):
    try:
        role = Role.objects.get(id=role_id, organization=request.org)
    except Role.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    role.name = request.POST.get("name", role.name)
    role.notes = request.POST.get("notes", role.notes)
    role.description = request.POST.get("description", role.description)
    role.save()
    return JsonResponse({"ok": True})


@login_required()
def roles_delete(request: DstHttpRequest, role_id: int):
    Role.objects.filter(id=role_id, organization=request.org).delete()
    return JsonResponse({"ok": True})
