import json

import csv
import io
import json
from datetime import date, datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from dst.models import AttendanceCode, AttendanceDay, AttendanceRule, AttendanceWeek, Person, Tag, UserRole
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


def json_people(request: DstHttpRequest):
    term = request.GET.get("term", "")
    people = Person.objects.filter(organization=request.org)
    if term:
        people = people.filter(
            Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(display_name__icontains=term) | Q(email__icontains=term)
        )
    results = []
    for p in people.order_by("display_name", "first_name")[:20]:
        results.append({"id": p.id, "label": p.get_name() + " " + p.last_name, "value": p.get_name()})
    return JsonResponse(results, safe=False)


class AttendanceWeekView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        date_str = request.GET.get("date", "")
        if date_str:
            try:
                day = date.fromisoformat(date_str)
            except ValueError:
                day = timezone.localdate()
        else:
            day = timezone.localdate()
        monday = day - timedelta(days=day.weekday())
        people = Person.objects.filter(organization=request.org, tags__show_in_attendance=True).distinct().order_by("display_name", "first_name")
        days = [monday + timedelta(days=i) for i in range(5)]
        week_data = []
        for p in people:
            row = {"person": p, "days": []}
            for d in days:
                ad = AttendanceDay.objects.filter(person=p, day=d).first()
                row["days"].append(ad)
            week_data.append(row)
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_week.html", {
                "monday": monday, "days": days, "week_data": week_data,
                "org_config": get_org_config(request.org),
            }, request=request),
            f"Week of {monday}",
            "week",
        )


class AttendanceReportsView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_reports.html", {
                "org_config": get_org_config(request.org),
            }, request=request),
            "Attendance Reports",
            "reports",
        )


class AttendancePinsView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        people = Person.objects.filter(organization=request.org, tags__show_in_attendance=True).distinct().order_by("display_name", "first_name")
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_pins.html", {
                "people": people,
                "org_config": get_org_config(request.org),
            }, request=request),
            "Assign PINs",
            "attendance_pins",
        )

    def post(self, request: DstHttpRequest):
        for key, value in request.POST.items():
            if key.startswith("pin_"):
                person_id = key.replace("pin_", "")
                try:
                    p = Person.objects.get(id=person_id, organization=request.org)
                    p.pin = value.strip()
                    p.save()
                except (Person.DoesNotExist, ValueError):
                    pass
        return redirect("/attendance/pins")


class AttendanceOffCampusView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        people = Person.objects.filter(organization=request.org, tags__show_in_attendance=True).distinct().order_by("display_name", "first_name")
        records = AttendanceDay.objects.filter(
            person__organization=request.org,
            off_campus_departure_time__isnull=False,
        ).select_related("person").order_by("-day")[:100]
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_off_campus.html", {
                "people": people, "records": records,
                "org_config": get_org_config(request.org),
            }, request=request),
            "Off Campus Time",
            "off_campus_time",
        )

    def post(self, request: DstHttpRequest):
        action = request.POST.get("action", "")
        if action == "add":
            person_id = request.POST.get("person_id")
            day_str = request.POST.get("day")
            dep_time = request.POST.get("departure_time")
            ret_time = request.POST.get("return_time")
            if person_id and day_str:
                try:
                    ad, _ = AttendanceDay.objects.get_or_create(
                        person_id=int(person_id),
                        day=date.fromisoformat(day_str),
                    )
                    if dep_time:
                        ad.off_campus_departure_time = datetime.strptime(dep_time, "%H:%M").time()
                    if ret_time:
                        ad.off_campus_return_time = datetime.strptime(ret_time, "%H:%M").time()
                    ad.save()
                except (ValueError, Person.DoesNotExist):
                    pass
        elif action == "delete":
            day_id = request.POST.get("day_id")
            AttendanceDay.objects.filter(id=day_id, person__organization=request.org).update(
                off_campus_departure_time=None, off_campus_return_time=None, off_campus_minutes_exempted=None,
            )
        return redirect("/attendance/offCampusTime")


class AttendanceDownloadView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Name", "Date", "Start", "End", "Code", "Off-Campus Dep", "Off-Campus Ret"])
        records = AttendanceDay.objects.filter(person__organization=request.org).select_related("person").order_by("-day", "person__display_name")[:1000]
        for r in records:
            writer.writerow([
                r.person.get_name(),
                r.day,
                r.start_time.strftime("%H:%M") if r.start_time else "",
                r.end_time.strftime("%H:%M") if r.end_time else "",
                r.code or "",
                r.off_campus_departure_time.strftime("%H:%M") if r.off_campus_departure_time else "",
                r.off_campus_return_time.strftime("%H:%M") if r.off_campus_return_time else "",
            ])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="attendance_{date.today()}.csv"'
        return response


class AttendancePersonReportView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest, person_id: int):
        person = Person.objects.filter(organization=request.org, id=person_id).first()
        if not person:
            return HttpResponseNotFound()
        records = AttendanceDay.objects.filter(person=person).order_by("-day")[:100]
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_person.html", {
                "person": person, "records": records,
                "org_config": get_org_config(request.org),
            }, request=request),
            f"Attendance for {person.get_name()}",
            "person",
        )


class AttendanceRuleEditView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request: DstHttpRequest, rule_id: int):
        rule = AttendanceRule.objects.filter(organization=request.org, id=rule_id).first()
        if not rule:
            return HttpResponseNotFound()
        codes = AttendanceCode.objects.filter(organization=request.org)
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_rule_form.html", {
                "rule": rule, "codes": codes, "is_new": False,
                "org_config": get_org_config(request.org),
            }, request=request),
            f"Edit rule #{rule.id}",
        )

    def post(self, request: DstHttpRequest, rule_id: int):
        rule = AttendanceRule.objects.filter(organization=request.org, id=rule_id).first()
        if not rule:
            return HttpResponseNotFound()
        self._save_rule(rule, request)
        return redirect("/attendance/rules")

    def _save_rule(self, rule, request):
        rule.category = request.POST.get("category", "")
        rule.absence_code = request.POST.get("absence_code", "") or None
        rule.monday = request.POST.get("monday") == "on"
        rule.tuesday = request.POST.get("tuesday") == "on"
        rule.wednesday = request.POST.get("wednesday") == "on"
        rule.thursday = request.POST.get("thursday") == "on"
        rule.friday = request.POST.get("friday") == "on"
        rule.exempt_from_fees = request.POST.get("exempt_from_fees") == "on"
        if request.POST.get("person_id"):
            try:
                rule.person_id = int(request.POST.get("person_id"))
            except ValueError:
                pass
        if request.POST.get("start_date"):
            rule.start_date = date.fromisoformat(request.POST["start_date"])
        if request.POST.get("end_date"):
            rule.end_date = date.fromisoformat(request.POST["end_date"])
        if request.POST.get("min_hours"):
            try:
                rule.min_hours = float(request.POST["min_hours"])
            except ValueError:
                pass
        rule.save()


class AttendanceNewRuleView(AttendanceRuleEditView):
    def get(self, request: DstHttpRequest):
        codes = AttendanceCode.objects.filter(organization=request.org)
        return render_main_template(
            request,
            "attendance",
            render_to_string("attendance_rule_form.html", {
                "rule": None, "codes": codes, "is_new": True,
                "org_config": get_org_config(request.org),
            }, request=request),
            "New attendance rule",
        )

    def post(self, request: DstHttpRequest):
        rule = AttendanceRule(organization=request.org)
        self._save_rule(rule, request)
        return redirect("/attendance/rules")


class AttendanceDeleteRuleView(LoginRequiredMixin, View):
    login_url = "/login"

    def post(self, request: DstHttpRequest, rule_id: int):
        AttendanceRule.objects.filter(organization=request.org, id=rule_id).delete()
        return redirect("/attendance/rules")


class AttendanceSaveDayView(LoginRequiredMixin, View):
    login_url = "/login"

    def post(self, request: DstHttpRequest):
        day_id = request.POST.get("day_id")
        ad = AttendanceDay.objects.filter(id=day_id, person__organization=request.org).first()
        if ad:
            code = request.POST.get("code", "")
            start = request.POST.get("startTime", "")
            end = request.POST.get("endTime", "")
            if code:
                ad.code = code
            if start:
                try:
                    ad.start_time = datetime.strptime(start, "%H:%M").time()
                except ValueError:
                    pass
            if end:
                try:
                    ad.end_time = datetime.strptime(end, "%H:%M").time()
                except ValueError:
                    pass
            ad.save()
        return redirect(request.META.get("HTTP_REFERER", "/attendance"))


class AttendanceSaveWeekView(LoginRequiredMixin, View):
    login_url = "/login"

    def post(self, request: DstHttpRequest):
        week_id = request.POST.get("week_id")
        extra = request.POST.get("extraHours")
        aw = AttendanceWeek.objects.filter(id=week_id, person__organization=request.org).first()
        if aw and extra:
            try:
                aw.extra_hours = float(extra)
                aw.save()
            except ValueError:
                pass
        return redirect(request.META.get("HTTP_REFERER", "/attendance"))
