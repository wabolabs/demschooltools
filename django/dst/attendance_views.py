import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from dst.models import AttendanceCode, AttendanceRule, Person, Tag, UserRole
from dst.org_config import get_org_config
from dst.utils import DstHttpRequest, render_main_template


class AttendanceView(LoginRequiredMixin, View):
    login_url = "/login"


class SignInSheetView(AttendanceView):
    def get(self, request: DstHttpRequest):
        if not request.user.hasRole(UserRole.ATTENDANCE):
            raise PermissionError("You don't have privileges to access this item")

        org = request.org

        # Get people with attendance tags (with their tags)
        people_with_tags = []
        for person in (
            Person.objects.filter(
                tags__show_in_attendance=True,
                tags__organization=org,
            )
            .distinct()
            .prefetch_related("tags")
            .order_by("display_name", "first_name")
        ):
            people_with_tags.append(
                {
                    "id": person.id,
                    "label": person.get_name() + " " + person.last_name,
                    "tags": [tag.id for tag in person.tags.all()],
                }
            )

        # Get attendance tags
        tags = []
        for tag in Tag.objects.filter(
            organization=org, show_in_attendance=True
        ).order_by("title"):
            tags.append(
                {
                    "id": tag.id,
                    "label": tag.title,
                }
            )

        # Get all people (for guest selection)
        all_people = []
        for person in (
            Person.objects.filter(organization=org, is_family=False)
            .exclude(first_name="", last_name="", display_name="")
            .only("display_name", "first_name", "last_name")
            .distinct()
        ):
            all_people.append(
                {
                    "id": person.id,
                    "label": person.get_name() + " " + person.last_name,
                }
            )
        all_people.sort(key=lambda x: x["label"])

        return render_main_template(
            request,
            "attendance",
            render_to_string(
                "sign_in_sheet.html",
                {
                    "people_json": json.dumps(people_with_tags),
                    "tags_json": json.dumps(tags),
                    "all_people_json": json.dumps(all_people),
                    "request": request,
                },
            ),
            "Sign in sheet",
            "sign_in_sheet",
        )


class AttendanceCodesView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        codes = AttendanceCode.objects.filter(organization=request.org).order_by("code")
        return render_main_template(
            request,
            "attendance",
            render_to_string(
                "attendance_codes.html",
                {
                    "codes": codes,
                    "org_config": get_org_config(request.org),
                },
                request=request,
            ),
            "Attendance codes",
            "attendance_codes",
        )

    def post(self, request: DstHttpRequest):
        code = request.POST.get("code", "")
        description = request.POST.get("description", "")
        color = request.POST.get("color", "#ccc")
        if code:
            AttendanceCode.objects.create(
                organization=request.org,
                code=code,
                description=description,
                color=color,
                counts_toward_attendance=request.POST.get("counts_toward_attendance") == "on",
                not_counted=request.POST.get("not_counted") == "on",
            )
        return redirect("/attendance/codes")


class AttendanceRulesView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        today = timezone.localdate()
        rules = AttendanceRule.objects.filter(organization=request.org).order_by("start_date")
        codes_map = {c.code: c.color for c in AttendanceCode.objects.filter(organization=request.org)}

        def annotate(r):
            return {"rule": r, "code_color": codes_map.get(r.absence_code, "")}

        current = [annotate(r) for r in rules if r.start_date <= today and (r.end_date is None or r.end_date >= today)]
        future = [annotate(r) for r in rules if r.start_date > today]
        past = [annotate(r) for r in rules if r.end_date is not None and r.end_date < today]
        return render_main_template(
            request,
            "attendance",
            render_to_string(
                "attendance_rules.html",
                {
                    "current_rules": current,
                    "future_rules": future,
                    "past_rules": past,
                    "codes_map": codes_map,
                    "org_config": get_org_config(request.org),
                },
                request=request,
            ),
            "Attendance rules",
            "rules",
        )
