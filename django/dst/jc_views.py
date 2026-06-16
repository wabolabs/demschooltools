from datetime import date, timedelta

from django.contrib.auth.decorators import login_required as django_login_required
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils import timezone

from dst.models import (
    Case,
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
