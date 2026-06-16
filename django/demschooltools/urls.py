"""demschooltools URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import logging

from django.conf import settings
from django.contrib import admin
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import include, path, register_converter

from dst.models import Person, Tag
from dst.org_config import get_org_config
from dst.utils import DstHttpRequest, render_main_template

LOGGER = logging.getLogger(__name__)


def login_view(request):
    return redirect("/custodia/login")


def feedback_email(request):
    if request.method == "POST":
        name = request.POST.get("name", "")
        email = request.POST.get("email", "")
        message = request.POST.get("message", "")
        try:
            send_mail(
                f"DemSchoolTools feedback from {name}",
                f"From: {name} <{email}>\n\n{message}",
                email or "noreply@demschooltools.com",
                ["schmave@gmail.com"],
                fail_silently=True,
            )
        except Exception as e:
            LOGGER.error("Failed to send feedback email: %s", e)
    return redirect("/")


def misc_view_files(request: DstHttpRequest):
    return render_main_template(
        request,
        "misc",
        render_to_string("misc_files.html", {"org_config": get_org_config(request.org)}, request=request),
        "Shared Files",
        selected_button="view_files",
    )


def misc_file_sharing(request: DstHttpRequest):
    return render_main_template(
        request,
        "misc",
        render_to_string("misc_files.html", {"org_config": get_org_config(request.org)}, request=request),
        "File Sharing",
        selected_button="file_sharing",
    )


from custodia.views import (
    AbsentView,
    DeleteSwipeView,
    ErrorTestView,
    ExcuseView,
    IndexView,
    IsAdminView,
    LoginView,
    LogoutView,
    OverrideView,
    ReportView,
    ReportYears,
    StudentDataView,
    StudentsTodayView,
    SwipeView,
)
from dst.attendance_views import (
    AttendanceCodesView,
    AttendanceDeleteRuleView,
    AttendanceDownloadView,
    AttendanceNewRuleView,
    AttendanceOffCampusView,
    AttendancePersonReportView,
    AttendancePinsView,
    AttendanceReportsView,
    AttendanceRuleEditView,
    AttendanceRulesView,
    AttendanceSaveDayView,
    AttendanceSaveWeekView,
    AttendanceWeekView,
    SignInSheetView,
    json_people,
)
from dst.health_views import health
from dst.manual_views import (
    CreateUpdateChapter,
    CreateUpdateEntry,
    CreateUpdateSection,
    preview_entry,
    print_manual,
    print_manual_chapter,
    search_manual,
    view_chapter,
    view_manual,
    view_manual_changes,
)
from dst.jc_views import (
    add_charge,
    continue_case,
    create_case,
    delete_case,
    delete_charge,
    download_charges,
    edit_meeting,
    edit_resolution_plan_list,
    edit_school_meeting_decision,
    edit_today,
    enter_school_meeting,
    jc_index,
    print_meeting,
    save_case,
    save_charge,
    this_week_report,
    view_meeting,
    view_meeting_resolution_plans,
    view_person_history,
    view_persons_writeups,
    view_rule_history,
    view_sm_decisions,
    view_sm_referrals,
    view_todays_minutes,
)
from dst.people_views import (
    add_comment,
    add_person,
    add_tag,
    all_people,
    all_tags,
    edit_person,
    edit_tag,
    json_people,
    json_tags,
    people_index,
    person_detail,
    remove_tag,
    view_tag,
    view_task_list,
)
from dst.roles_views import (
    roles_index,
    roles_new,
    roles_records,
)
from dst.settings_views import (
    settings_access,
    settings_index,
    settings_password,
    settings_view,
)


class NegativeIntConverter:
    regex = r"-?\d+"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return "%d" % value


register_converter(NegativeIntConverter, "negint")


custodia_api_patterns = [
    path("users/is-admin", IsAdminView.as_view()),
    path("students", StudentsTodayView.as_view()),
    path("students/<int:person_id>/swipe/delete", DeleteSwipeView.as_view()),
    path("students/<int:person_id>/swipe", SwipeView.as_view()),
    path("students/<int:person_id>/absent", AbsentView.as_view()),
    path("students/<int:person_id>/excuse", ExcuseView.as_view()),
    path("students/<int:person_id>/override", OverrideView.as_view()),
    path("students/<int:person_id>", StudentDataView.as_view()),
    path("reports/years/<str:year_name>", ReportYears.as_view()),
    path("reports/years", ReportYears.as_view()),
    path("reports/<str:year_name>/<negint:class_id>", ReportView.as_view()),
    path("reports/<str:year_name>", ReportView.as_view()),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("custodia-api/", (custodia_api_patterns, "custodia-api", "custodia-api")),
    path("api/v1/custodia/", (custodia_api_patterns, "api-v1-custodia", "api-v1-custodia")),
    path("attendance/signInSheet", SignInSheetView.as_view()),
    path("viewManual", view_manual),
    path("viewManualChanges", view_manual_changes),
    path("searchManual", search_manual),
    path("printManual", print_manual),
    path("printManualChapter/<negint:chapter_id>", print_manual_chapter),
    # chapters
    path("viewChapter/<int:chapter_id>", view_chapter),
    path("addChapter", CreateUpdateChapter.as_view()),
    path("editChapter", CreateUpdateChapter.as_view()),
    path("editChapter/<int:object_id>", CreateUpdateChapter.as_view()),
    # sections
    path("addSection/<int:chapter_id>", CreateUpdateSection.as_view()),
    path("editSection", CreateUpdateSection.as_view()),
    path("editSection/<int:object_id>", CreateUpdateSection.as_view()),
    # entries
    path("addEntry/<int:section_id>", CreateUpdateEntry.as_view()),
    path("editEntry", CreateUpdateEntry.as_view()),
    path("editEntry/<int:object_id>", CreateUpdateEntry.as_view()),
    path("viewEntry/", preview_entry),
    path("viewEntry/<int:object_id>", preview_entry),
    # JC routes
    path("", jc_index),
    path("jc", jc_index),
    path("viewToday", view_todays_minutes),
    path("viewMeeting/<int:meeting_id>", view_meeting),
    path("viewSchoolMeetingReferrals", view_sm_referrals),
    path("viewSchoolMeeting", view_sm_decisions),
    path("viewPersonHistory/<int:person_id>", view_person_history),
    path("viewRuleHistory/<int:rule_id>", view_rule_history),
    path("viewPersonsWriteups/<int:person_id>", view_persons_writeups),
    path("thisWeekReport", this_week_report),
    path("downloadCharges", download_charges),
    path("editResolutionPlanList", edit_resolution_plan_list),
    path("viewMeetingResolutionPlans/<int:meeting_id>", view_meeting_resolution_plans),
    path("printMeeting/<int:meeting_id>", print_meeting),
    path("enterSchoolMeeting", enter_school_meeting),
    path("editSchoolMeeting/<int:charge_id>", edit_school_meeting_decision),
    path("editToday", edit_today),
    path("editMeeting/<int:meeting_id>", edit_meeting),
    path("createCase", create_case),
    path("saveCase/<int:case_id>", save_case),
    path("deleteCase/<int:case_id>", delete_case),
    path("continueCase/<int:meeting_id>/<int:case_id>", continue_case),
    path("addCharge/<int:case_id>", add_charge),
    path("saveCharge/<int:charge_id>", save_charge),
    path("deleteCharge/<int:charge_id>", delete_charge),
    # Custodia routes
    path("custodia/", IndexView.as_view()),
    path("custodia/error-test", ErrorTestView.as_view()),
    path("custodia/login", LoginView.as_view()),
    path("custodia/logout", LogoutView.as_view()),
    path("health/", health),
    path("login", login_view),
    path("logout", LogoutView.as_view()),
    path("attendance", lambda r: redirect("/attendance/signInSheet")),
    path("attendance/", lambda r: redirect("/attendance/signInSheet")),
    path("attendance/jsonPeople", json_people),
    path("attendance/viewWeek", AttendanceWeekView.as_view()),
    path("attendance/editWeek", AttendanceWeekView.as_view()),
    path("attendance/reports", AttendanceReportsView.as_view()),
    path("attendance/pins", AttendancePinsView.as_view()),
    path("attendance/offCampusTime", AttendanceOffCampusView.as_view()),
    path("attendance/download", AttendanceDownloadView.as_view()),
    path("attendance/forPerson/<int:person_id>", AttendancePersonReportView.as_view()),
    path("attendance/newRule", AttendanceNewRuleView.as_view()),
    path("attendance/rule/<int:rule_id>", AttendanceRuleEditView.as_view()),
    path("attendance/saveRule", lambda r: redirect("/attendance/rules")),
    path("attendance/deleteRule/<int:rule_id>", AttendanceDeleteRuleView.as_view()),
    path("attendance/saveDay", AttendanceSaveDayView.as_view()),
    path("attendance/saveWeek", AttendanceSaveWeekView.as_view()),
    path("attendance/codes", AttendanceCodesView.as_view()),
    path("attendance/rules", AttendanceRulesView.as_view()),
    path("people", people_index),
    path("people/", people_index),
    path("allPeople", all_people),
    path("people/new", add_person),
    path("people/<int:person_id>", person_detail),
    path("people/edit/<int:person_id>", edit_person),
    path("settings", settings_index),
    path("settings/", settings_index),
    path("settings/password", settings_password),
    path("settings/access", settings_access),
    path("settings/checklists", settings_view),
    path("viewAllTags", all_tags),
    path("jsonPeople", json_people),
    path("jsonTags/<int:person_id>", json_tags),
    path("addTag/<int:person_id>", add_tag),
    path("removeTag/<int:person_id>/<int:tag_id>", remove_tag),
    path("viewTag/<int:tag_id>", view_tag),
    path("editTag/<int:tag_id>", edit_tag),
    path("saveTag", lambda r: redirect("/viewAllTags")),
    path("viewTaskList/<int:task_list_id>", view_task_list),
    path("addComment", add_comment),
    path("sendFeedbackEmail", feedback_email),
    path("misc/viewFiles", misc_view_files),
    path("misc/fileSharing", misc_file_sharing),
    path("misc/saveFileSharingSettings", lambda r: redirect("/misc/fileSharing")),
    path("misc/uploadFileShare", lambda r: redirect("/misc/viewFiles")),
    path("misc/emailFile", lambda r: redirect("/misc/viewFiles")),
    path("misc/deleteFile", lambda r: redirect("/misc/viewFiles")),
    path("roles/index", roles_index),
    path("roles/newRole", roles_new),
    path("roles/records", roles_records),
]

if settings.SILK_ENABLED:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
