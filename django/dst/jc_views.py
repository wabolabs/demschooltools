import csv
import io
from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required as django_login_required
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone

from dst.models import (
    Case,
    CaseReference,
    Charge,
    Entry,
    Meeting,
    Person,
    PersonAtCase,
    PersonAtMeeting,
    Tag,
)
from dst.org_config import get_org_config
from dst.utils import DstHttpRequest, render_main_template


def login_required():
    return django_login_required(login_url="/login")


def get_start_of_year():
    today = timezone.localdate()
    year = today.year
    if today.month < 8:
        year -= 1
    return date(year, 8, 1)


def format_date_short(d):
    return d.strftime("%b %-d")


def yymmdd_date(d):
    return d.strftime("%y-%m-%d")


@login_required()
def jc_index(request: DstHttpRequest):
    meetings = (
        Meeting.objects.filter(organization=request.org)
        .prefetch_related(
            Prefetch(
                "case_set",
                queryset=Case.objects.only("id", "meeting_id", "case_number", "findings"),
            )
        )
        .order_by("-date")
    )

    jc_tags = list(Tag.objects.filter(organization=request.org, show_in_jc=True).values_list("id", flat=True))

    people = (
        Person.objects.filter(organization=request.org, tags__id__in=jc_tags)
        .prefetch_related(
            Prefetch(
                "charge_set",
                queryset=Charge.objects.select_related("case__meeting").filter(
                    case__meeting__organization=request.org
                ),
            ),
            Prefetch(
                "personatcase_set",
                queryset=PersonAtCase.objects.filter(role=PersonAtCase.ROLE_WRITER).select_related(
                    "case__meeting"
                ),
            ),
        )
        .distinct()
        .order_by("display_name", "first_name", "last_name")
    )

    start = get_start_of_year()
    people_data = []
    for p in people:
        this_year_charges = [c for c in p.charge_set.all() if c.case.meeting.date >= start]
        this_year_written = [pac for pac in p.personatcase_set.all() if pac.case.meeting.date >= start]
        people_data.append(
            {
                "person": p,
                "charge_count": len(this_year_charges),
                "written_count": len(this_year_written),
            }
        )

    entries = (
        Entry.objects.filter(
            section__chapter__organization=request.org,
            deleted=False,
            section__deleted=False,
            section__chapter__deleted=False,
        )
        .prefetch_related(
            Prefetch(
                "charge_set",
                queryset=Charge.objects.select_related("case__meeting").filter(
                    case__meeting__organization=request.org
                ),
            ),
        )
        .order_by("section__chapter__num", "section__num", "num")
    )

    entries_with_charges = []
    for e in entries:
        this_year_charges = [c for c in e.charge_set.all() if c.case.meeting.date >= start]
        if this_year_charges:
            entries_with_charges.append(
                {
                    "entry": e,
                    "charge_count": len(this_year_charges),
                }
            )

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "jc_index.html",
            {
                "meetings": meetings,
                "people_data": people_data,
                "entries_with_charges": entries_with_charges,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"{get_org_config(request.org).str_jc_name} — {request.org.short_name or request.org.name}",
        selected_button="jc_home",
    )


@login_required()
def view_meeting(request: DstHttpRequest, meeting_id: int):
    meeting = (
        Meeting.objects.filter(organization=request.org, id=meeting_id)
        .prefetch_related(
            Prefetch(
                "personatmeeting_set",
                queryset=PersonAtMeeting.objects.select_related("person"),
            ),
            Prefetch(
                "case_set",
                queryset=Case.objects.prefetch_related(
                    Prefetch(
                        "charge_set",
                        queryset=Charge.objects.select_related("person", "rule"),
                    ),
                    Prefetch(
                        "personatcase_set",
                        queryset=PersonAtCase.objects.select_related("person"),
                    ),
                ).order_by("case_number"),
            ),
        )
        .first()
    )
    if meeting is None:
        return HttpResponseNotFound()

    chair = meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_CHAIR).first()
    notetaker = meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_NOTE_TAKER).first()
    committee = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_MEMBER))
    subs = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_SUB))
    runners = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_RUNNER))

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "view_meeting.html",
            {
                "meeting": meeting,
                "chair": chair,
                "notetaker": notetaker,
                "committee": committee,
                "subs": subs,
                "runners": runners,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"{get_org_config(request.org).str_jc_name} minutes — {meeting.date}",
    )


@login_required()
def view_todays_minutes(request: DstHttpRequest):
    today = timezone.localdate()
    meeting = Meeting.objects.filter(organization=request.org, date=today).first()
    if meeting:
        return view_meeting(request, meeting.id)
    latest = (
        Meeting.objects.filter(organization=request.org).order_by("-date").first()
    )
    return render_main_template(
        request,
        "jc",
        render_to_string(
            "no_meeting.html",
            {
                "today": today,
                "latest_meeting": latest,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "No meeting today",
        selected_button="jc_home",
    )


@login_required()
def view_sm_referrals(request: DstHttpRequest):
    sm_charges = list(
        Charge.objects.filter(
            case__meeting__organization=request.org,
            referred_to_sm=True,
            sm_decision__isnull=True,
        )
        .select_related("case", "person", "rule")
        .order_by("case__meeting__date")
    )
    return render_main_template(
        request,
        "jc",
        render_to_string(
            "view_sm_referrals.html",
            {
                "sm_charges": sm_charges,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Charges referred to School Meeting",
        selected_button="view_referred",
    )


@login_required()
def view_sm_decisions(request: DstHttpRequest):
    decisions = list(
        Charge.objects.filter(
            case__meeting__organization=request.org,
            referred_to_sm=True,
            sm_decision__isnull=False,
        )
        .select_related("case", "person", "rule")
        .order_by("-sm_decision_date")
    )
    return render_main_template(
        request,
        "jc",
        render_to_string(
            "view_sm_decisions.html",
            {
                "decisions": decisions,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "School Meeting decisions",
        selected_button="view_sm",
    )


@login_required()
def view_person_history(request: DstHttpRequest, person_id: int):
    person = Person.objects.filter(organization=request.org, id=person_id).first()
    if person is None:
        return HttpResponseNotFound()

    start_str = request.GET.get("start_date", "")
    end_str = request.GET.get("end_date", "")
    redact = request.GET.get("redact_names", "false") == "true"

    start = get_start_of_year()
    end = timezone.localdate()
    if start_str:
        try:
            start = date.fromisoformat(start_str)
        except ValueError:
            pass
    if end_str:
        try:
            end = date.fromisoformat(end_str)
        except ValueError:
            pass

    charges = (
        Charge.objects.filter(person=person, case__meeting__date__gte=start, case__meeting__date__lte=end)
        .select_related("case__meeting", "rule")
        .order_by("-case__meeting__date")
    )

    recent_rps = charges[:5]

    charges_by_rule = defaultdict(list)
    for c in charges:
        key = c.rule.id if c.rule else 0
        charges_by_rule[key].append(c)

    rule_records = []
    for rule_id, clist in sorted(charges_by_rule.items()):
        entry = clist[0].rule
        most_recent = max(c.case.meeting.date for c in clist)
        rule_records.append({"entry": entry, "count": len(clist), "most_recent": most_recent})

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "view_person_history.html",
            {
                "person": person,
                "history": {
                    "start_date": start,
                    "end_date": end,
                    "rule_records": rule_records,
                    "charges_by_rule": dict(charges_by_rule),
                    "charges_by_date": list(charges),
                },
                "recent_rps": recent_rps,
                "redact_names": redact,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"{person.get_name()}'s {get_org_config(request.org).str_jc_name_short} history",
    )


@login_required()
def view_rule_history(request: DstHttpRequest, rule_id: int):
    rule = Entry.objects.filter(
        id=rule_id,
        section__chapter__organization=request.org,
        deleted=False,
    ).first()
    if rule is None:
        return HttpResponseNotFound()

    start_str = request.GET.get("start_date", "")
    end_str = request.GET.get("end_date", "")
    start = get_start_of_year()
    end = timezone.localdate()
    if start_str:
        try:
            start = date.fromisoformat(start_str)
        except ValueError:
            pass
    if end_str:
        try:
            end = date.fromisoformat(end_str)
        except ValueError:
            pass

    charges = (
        Charge.objects.filter(rule=rule, case__meeting__date__gte=start, case__meeting__date__lte=end)
        .select_related("case__meeting", "person")
        .order_by("-case__meeting__date")
    )

    recent_rps = list(set(
        c.resolution_plan for c in charges[:10] if c.resolution_plan
    ))

    person_map = defaultdict(list)
    for c in charges:
        person_map[c.person_id].append(c)

    rule_records = []
    for pid, clist in sorted(person_map.items()):
        p = clist[0].person
        most_recent = max(c.case.meeting.date for c in clist)
        rule_records.append({"person": p, "count": len(clist), "most_recent": most_recent})

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "view_rule_history.html",
            {
                "rule": rule,
                "history": {
                    "start_date": start,
                    "end_date": end,
                    "rule_records": rule_records,
                    "charges": list(charges),
                },
                "recent_rps": recent_rps,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"History of {rule.number()} {rule.title}",
    )


@login_required()
def view_persons_writeups(request: DstHttpRequest, person_id: int):
    person = Person.objects.filter(organization=request.org, id=person_id).first()
    if person is None:
        return HttpResponseNotFound()

    start = get_start_of_year()
    cases = (
        Case.objects.filter(
            personatcase__person=person,
            personatcase__role=PersonAtCase.ROLE_WRITER,
            meeting__date__gte=start,
            meeting__organization=request.org,
        )
        .distinct()
        .order_by("-meeting__date")
    )

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "view_persons_writeups.html",
            {
                "person": person,
                "cases": cases,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"Cases written by {person.get_name()}",
    )


@login_required()
def this_week_report(request: DstHttpRequest):
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    charges = list(
        Charge.objects.filter(
            case__meeting__date__gte=start,
            case__meeting__date__lte=end,
            case__meeting__organization=request.org,
        )
        .select_related("case__meeting", "person", "rule")
        .order_by("case__meeting__date")
    )

    cases = list(Case.objects.filter(
        meeting__date__gte=start,
        meeting__date__lte=end,
        meeting__organization=request.org,
    ).distinct().order_by("meeting__date"))

    rule_counts = defaultdict(int)
    for c in charges:
        if c.rule:
            rule_counts[c.rule] += 1

    person_counts = {}
    for c in charges:
        if c.person_id not in person_counts:
            person_counts[c.person_id] = {"person": c.person, "this_week": 0, "this_month": 0, "all_time": 0}
        person_counts[c.person_id]["this_week"] += 1
        person_counts[c.person_id]["this_month"] += 1
        person_counts[c.person_id]["all_time"] += 1

    month_start = today.replace(day=1)
    all_charges = Charge.objects.filter(
        case__meeting__date__gte=month_start,
        case__meeting__organization=request.org,
    ).values("person_id").annotate(count=Count("id"))

    year_start = get_start_of_year()
    all_year_charges = Charge.objects.filter(
        case__meeting__date__gte=year_start,
        case__meeting__organization=request.org,
    ).values("person_id").annotate(count=Count("id"))

    year_month_counts = {}
    for item in all_charges:
        if item["person_id"] in person_counts:
            person_counts[item["person_id"]]["this_month"] = item["count"]
    for item in all_year_charges:
        if item["person_id"] in person_counts:
            person_counts[item["person_id"]]["all_time"] = item["count"]

    jc_tags = list(Tag.objects.filter(organization=request.org, show_in_jc=True).values_list("id", flat=True))
    all_people = Person.objects.filter(organization=request.org, tags__id__in=jc_tags).distinct()
    charged_ids = set(c.person_id for c in charges if c.person_id)
    uncharged = [p for p in all_people if p.id not in charged_ids]

    minor_destinations = list(set(
        c.minor_referral_destination for c in charges if c.minor_referral_destination
    ))

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "jc_weekly_report.html",
            {
                "start_date": start,
                "end_date": end,
                "num_cases": len(cases),
                "num_charges": len(charges),
                "rule_counts": sorted(rule_counts.items(), key=lambda x: -x[1]),
                "person_counts": sorted(person_counts.values(), key=lambda x: -x["this_week"]),
                "uncharged_people": sorted(uncharged, key=lambda p: p.display_name or p.first_name),
                "cases": cases,
                "charges": charges,
                "minor_destinations": minor_destinations,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Weekly report",
        selected_button="weekly_report",
    )


@login_required()
def download_charges(request: DstHttpRequest):
    charges = (
        Charge.objects.filter(case__meeting__organization=request.org)
        .select_related("case__meeting", "person", "rule")
        .order_by("-case__meeting__date")
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Name", "Age", "Grade", "Date", "Case #", "Entry", "Plea", "Resolution Plan", "SM Decision", "Severity"])
    for c in charges:
        age = ""
        if c.person and c.person.dob:
            age = c.case.meeting.date.year - c.person.dob.year
        writer.writerow([
            c.person.get_name() if c.person else "",
            age,
            c.person.grade if c.person else "",
            c.case.meeting.date,
            c.case.case_number,
            c.rule.number() if c.rule else "",
            c.plea,
            c.resolution_plan,
            c.sm_decision or "",
            c.severity,
        ])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="charges_{date.today()}.csv"'
    return response


@login_required()
def edit_resolution_plan_list(request: DstHttpRequest):
    active = list(
        Charge.objects.filter(
            case__meeting__organization=request.org,
            rp_complete=False,
        )
        .exclude(resolution_plan="")
        .select_related("case__meeting", "person", "rule")
        .order_by("-case__meeting__date")
    )
    completed = list(
        Charge.objects.filter(
            case__meeting__organization=request.org,
            rp_complete=True,
            rp_complete_date__isnull=False,
        )
        .exclude(resolution_plan="")
        .select_related("case__meeting", "person", "rule")
        .order_by("-rp_complete_date")[:50]
    )
    nullified = list(
        Charge.objects.filter(
            case__meeting__organization=request.org,
            rp_complete=True,
            rp_complete_date__isnull=True,
        )
        .exclude(resolution_plan="")
        .select_related("case__meeting", "person", "rule")
        .order_by("-case__meeting__date")[:50]
    )

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "edit_rp_list.html",
            {
                "active_rps": active,
                "completed_rps": completed,
                "nullified_rps": nullified,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        get_org_config(request.org).str_res_plans_cap,
        selected_button="rps",
    )


@login_required()
def view_meeting_resolution_plans(request: DstHttpRequest, meeting_id: int):
    meeting = Meeting.objects.filter(organization=request.org, id=meeting_id).first()
    if meeting is None:
        return HttpResponseNotFound()

    charges = list(
        Charge.objects.filter(case__meeting=meeting)
        .exclude(resolution_plan="")
        .select_related("case", "person", "rule")
        .order_by("case__case_number")
    )

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "print_rps.html",
            {
                "meeting": meeting,
                "charges": charges,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"{get_org_config(request.org).str_res_plans_cap} — {meeting.date}",
    )


@login_required()
def print_meeting(request: DstHttpRequest, meeting_id: int):
    meeting = (
        Meeting.objects.filter(organization=request.org, id=meeting_id)
        .prefetch_related(
            Prefetch("personatmeeting_set", queryset=PersonAtMeeting.objects.select_related("person")),
            Prefetch("case_set", queryset=Case.objects.prefetch_related(
                Prefetch("charge_set", queryset=Charge.objects.select_related("person", "rule")),
                Prefetch("personatcase_set", queryset=PersonAtCase.objects.select_related("person")),
            ).order_by("case_number")),
        )
        .first()
    )
    if meeting is None:
        return HttpResponseNotFound()

    chair = meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_CHAIR).first()
    notetaker = meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_NOTE_TAKER).first()
    committee = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_MEMBER))
    subs = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_SUB))
    runners = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_RUNNER))

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "print_meeting.html",
            {
                "meeting": meeting,
                "chair": chair,
                "notetaker": notetaker,
                "committee": committee,
                "subs": subs,
                "runners": runners,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"{get_org_config(request.org).str_jc_name} minutes — {meeting.date}",
    )


@login_required()
def enter_school_meeting(request: DstHttpRequest):
    sm_charges = list(
        Charge.objects.filter(
            case__meeting__organization=request.org,
            referred_to_sm=True,
            sm_decision__isnull=True,
        )
        .select_related("case", "person", "rule")
        .order_by("case__meeting__date")
    )

    if request.method == "POST":
        for c in sm_charges:
            decision = request.POST.get(f"sm_decision_{c.id}")
            decision_date = request.POST.get(f"sm_date_{c.id}")
            if decision:
                c.sm_decision = decision
                if decision_date:
                    try:
                        c.sm_decision_date = date.fromisoformat(decision_date)
                    except ValueError:
                        c.sm_decision_date = timezone.localdate()
                else:
                    c.sm_decision_date = timezone.localdate()
                c.save()
        return redirect("/viewSchoolMeeting")

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "enter_sm_decisions.html",
            {
                "sm_charges": sm_charges,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Record School Meeting decisions",
        selected_button="view_referred",
    )


@login_required()
def edit_today(request: DstHttpRequest):
    today = timezone.localdate()
    meeting = Meeting.objects.filter(organization=request.org, date=today).first()
    if meeting is None:
        meeting = Meeting.objects.create(organization=request.org, date=today)
    return edit_meeting(request, meeting.id)


@login_required()
def edit_meeting(request: DstHttpRequest, meeting_id: int):
    meeting = Meeting.objects.filter(organization=request.org, id=meeting_id).first()
    if meeting is None:
        return HttpResponseNotFound()

    jc_people = Person.objects.filter(
        organization=request.org, tags__id__in=list(
            Tag.objects.filter(organization=request.org, show_in_jc=True).values_list("id", flat=True)
        )
    ).distinct().order_by("display_name", "first_name")

    open_cases = Case.objects.filter(
        meeting__organization=request.org,
        date_closed__isnull=True,
    ).exclude(meeting=meeting).order_by("-meeting__date")

    if request.method == "POST":
        meeting.date = date.fromisoformat(request.POST.get("date", str(meeting.date)))
        meeting.save()

        # Update people at meeting
        PersonAtMeeting.objects.filter(meeting=meeting).delete()
        for role_field, role_val in [
            ("chair", PersonAtMeeting.ROLE_JC_CHAIR),
            ("notetaker", PersonAtMeeting.ROLE_NOTE_TAKER),
            ("committee", PersonAtMeeting.ROLE_JC_MEMBER),
            ("subs", PersonAtMeeting.ROLE_JC_SUB),
            ("runners", PersonAtMeeting.ROLE_RUNNER),
        ]:
            person_ids = request.POST.getlist(role_field)
            for pid in person_ids:
                if pid:
                    PersonAtMeeting.objects.create(
                        meeting=meeting,
                        person_id=int(pid),
                        role=role_val,
                    )

        return redirect(f"/viewMeeting/{meeting.id}")

    chair = meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_CHAIR).first()
    notetaker = meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_NOTE_TAKER).first()
    committee_ids = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_MEMBER).values_list("person_id", flat=True))
    sub_ids = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_JC_SUB).values_list("person_id", flat=True))
    runner_ids = list(meeting.personatmeeting_set.filter(role=PersonAtMeeting.ROLE_RUNNER).values_list("person_id", flat=True))

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "edit_meeting.html",
            {
                "meeting": meeting,
                "jc_people": jc_people,
                "open_cases": open_cases,
                "chair": chair,
                "notetaker": notetaker,
                "committee_ids": committee_ids,
                "sub_ids": sub_ids,
                "runner_ids": runner_ids,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"Edit {get_org_config(request.org).str_jc_name_short} minutes — {meeting.date}",
    )


@login_required()
def create_case(request: DstHttpRequest):
    meeting_id = request.POST.get("meeting_id")
    meeting = Meeting.objects.filter(organization=request.org, id=meeting_id).first()
    if not meeting:
        return HttpResponseNotFound()

    case_count = meeting.case_set.count()
    next_num = f"{case_count + 1:02d}"
    case_num = f"{meeting.date.strftime('%y%m%d')}-{next_num}"

    case = Case.objects.create(
        case_number=case_num,
        meeting=meeting,
        findings=request.POST.get("findings", ""),
        location=request.POST.get("location", ""),
        date=date.fromisoformat(request.POST.get("date", str(meeting.date))) if request.POST.get("date") else meeting.date,
        time=request.POST.get("time", ""),
    )
    return redirect(f"/editMeeting/{meeting.id}")


@login_required()
def save_case(request: DstHttpRequest, case_id: int):
    case = Case.objects.filter(id=case_id, meeting__organization=request.org).first()
    if not case:
        return HttpResponseNotFound()

    case.findings = request.POST.get("findings", case.findings)
    case.location = request.POST.get("location", case.location)
    case.time = request.POST.get("time", case.time)
    if request.POST.get("date"):
        try:
            case.date = date.fromisoformat(request.POST["date"])
        except ValueError:
            pass
    case.save()
    return redirect(f"/editMeeting/{case.meeting.id}")


@login_required()
def delete_case(request: DstHttpRequest, case_id: int):
    case = Case.objects.filter(id=case_id, meeting__organization=request.org).first()
    if case:
        meeting_id = case.meeting.id
        case.delete()
        return redirect(f"/editMeeting/{meeting_id}")
    return HttpResponseNotFound()


@login_required()
def add_charge(request: DstHttpRequest, case_id: int):
    case = Case.objects.filter(id=case_id, meeting__organization=request.org).first()
    if not case:
        return HttpResponseNotFound()

    person_id = request.POST.get("person_id")
    rule_id = request.POST.get("rule_id")
    Charge.objects.create(
        case=case,
        person_id=person_id if person_id else None,
        rule_id=rule_id if rule_id else None,
        plea=request.POST.get("plea", ""),
        resolution_plan=request.POST.get("resolution_plan", ""),
        severity=request.POST.get("severity", ""),
        referred_to_sm=request.POST.get("referred_to_sm") == "on",
    )
    return redirect(f"/editMeeting/{case.meeting.id}")


@login_required()
def save_charge(request: DstHttpRequest, charge_id: int):
    charge = Charge.objects.filter(id=charge_id, case__meeting__organization=request.org).first()
    if not charge:
        return HttpResponseNotFound()

    person_id = request.POST.get("person_id")
    rule_id = request.POST.get("rule_id")
    charge.person_id = int(person_id) if person_id else None
    charge.rule_id = int(rule_id) if rule_id else None
    charge.plea = request.POST.get("plea", charge.plea)
    charge.resolution_plan = request.POST.get("resolution_plan", charge.resolution_plan)
    charge.severity = request.POST.get("severity", charge.severity)
    charge.referred_to_sm = request.POST.get("referred_to_sm") == "on"
    charge.save()
    return redirect(f"/editMeeting/{charge.case.meeting.id}")


@login_required()
def delete_charge(request: DstHttpRequest, charge_id: int):
    charge = Charge.objects.filter(id=charge_id, case__meeting__organization=request.org).first()
    if charge:
        meeting_id = charge.case.meeting.id
        charge.delete()
        return redirect(f"/editMeeting/{meeting_id}")
    return HttpResponseNotFound()


@login_required()
def continue_case(request: DstHttpRequest, meeting_id: int, case_id: int):
    meeting = Meeting.objects.filter(organization=request.org, id=meeting_id).first()
    old_case = Case.objects.filter(id=case_id, meeting__organization=request.org, date_closed__isnull=True).first()
    if not meeting or not old_case or old_case.meeting == meeting:
        return HttpResponseNotFound()
    case_count = meeting.case_set.count()
    next_num = f"{case_count + 1:02d}"
    case_num = f"{meeting.date.strftime('%y%m%d')}-{next_num}"
    Case.objects.create(
        case_number=case_num,
        meeting=meeting,
        findings=f"Continued from case #{old_case.case_number}: {old_case.findings}",
        location=old_case.location,
    )
    return redirect(f"/editMeeting/{meeting.id}")


@login_required()
def edit_school_meeting_decision(request: DstHttpRequest, charge_id: int):
    charge = Charge.objects.filter(
        id=charge_id,
        case__meeting__organization=request.org,
        referred_to_sm=True,
    ).select_related("case", "person", "rule").first()
    if charge is None:
        return HttpResponseNotFound()

    if request.method == "POST":
        decision = request.POST.get("sm_decision", "")
        decision_date = request.POST.get("sm_date", "")
        if decision:
            charge.sm_decision = decision
            if decision_date:
                try:
                    charge.sm_decision_date = date.fromisoformat(decision_date)
                except ValueError:
                    pass
            charge.save()
        return redirect("/viewSchoolMeeting")

    return render_main_template(
        request,
        "jc",
        render_to_string(
            "sm_decision_form.html",
            {
                "charge": charge,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Edit School Meeting decision",
    )
