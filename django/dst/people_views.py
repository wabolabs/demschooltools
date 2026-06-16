from django.contrib.auth.decorators import login_required as django_login_required
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from dst.models import Comment, Organization, Person, PersonTagChange, PhoneNumber, Tag, Task, TaskList, User, UserRole
from dst.org_config import get_org_config
from dst.utils import DstHttpRequest, render_main_template


def login_required():
    return django_login_required(login_url="/login")


@login_required()
def people_index(request: DstHttpRequest):
    recent_comments = list(
        Comment.objects.filter(person__organization=request.org)
        .select_related("person", "user")
        .order_by("-created")[:20]
    )
    people = list(
        Person.objects.filter(organization=request.org).order_by("last_name", "first_name")
    )
    return render_main_template(
        request,
        "crm",
        render_to_string(
            "crm_index.html",
            {
                "people": people,
                "recent_comments": recent_comments,
            },
            request=request,
        ),
        f"All people — {request.org.short_name or request.org.name}",
        selected_button="recent_comments",
    )


@login_required()
def all_people(request: DstHttpRequest):
    people = (
        Person.objects.filter(organization=request.org)
        .prefetch_related("phonenumber_set")
        .order_by("last_name", "first_name")
    )
    return render_main_template(
        request,
        "crm",
        render_to_string(
            "all_people.html",
            {
                "people": people,
            },
            request=request,
        ),
        f"All people — {request.org.short_name or request.org.name}",
        selected_button="all_people",
    )


@login_required()
def person_detail(request: DstHttpRequest, person_id: int):
    person = Person.objects.filter(
        organization=request.org, id=person_id
    ).prefetch_related("tags", "phonenumber_set").first()
    if person is None:
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound()

    family_members = (
        Person.objects.filter(
            organization=request.org,
            family_person_id=person.family_person_id,
        )
        .exclude(id=person.id)
        .all()
        if person.family_person_id
        else []
    )
    all_comments = list(
        Comment.objects.filter(person=person)
        .select_related("user")
        .order_by("-created")
    )
    family_person = (
        Person.objects.filter(id=person.family_person_id).first()
        if person.family_person_id
        else None
    )

    return render_main_template(
        request,
        "crm",
        render_to_string(
            "person_detail.html",
            {
                "person": person,
                "family_members": family_members,
                "family_person": family_person,
                "all_comments": all_comments,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"{person.get_name()}",
    )


@login_required()
def add_person(request: DstHttpRequest):
    from django import forms

    class PersonForm(forms.Form):
        first_name = forms.CharField(max_length=255, required=True, label="First Name")
        last_name = forms.CharField(max_length=255, required=False, label="Last Name")
        display_name = forms.CharField(max_length=255, required=False, label="Short Name")
        email = forms.CharField(max_length=255, required=False, label="Email")
        gender = forms.ChoiceField(
            choices=[("Unknown", "Unknown"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
            required=False,
            label="Gender",
        )
        address = forms.CharField(max_length=255, required=False, label="Address")
        city = forms.CharField(max_length=255, required=False, label="City")
        state = forms.CharField(max_length=255, required=False, label="State")
        zip = forms.CharField(max_length=255, required=False, label="Zip")
        neighborhood = forms.CharField(max_length=255, required=False, label="Neighborhood")
        notes = forms.CharField(widget=forms.Textarea, required=False, label="Notes")
        grade = forms.CharField(max_length=255, required=False, label="Current Grade")
        previous_school = forms.CharField(max_length=255, required=False, label="Previous School")
        school_district = forms.CharField(max_length=255, required=False, label="School District")
        phone = forms.CharField(max_length=255, required=False, label="Phone")
        phone_comment = forms.CharField(max_length=255, required=False, label="Phone Comment")

    if request.method == "POST":
        form = PersonForm(request.POST)
        if form.is_valid():
            with atomic():
                person = Person.objects.create(
                    organization=request.org,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data.get("last_name", ""),
                    display_name=form.cleaned_data.get("display_name", ""),
                    email=form.cleaned_data.get("email", ""),
                    gender=form.cleaned_data.get("gender", "Unknown"),
                    address=form.cleaned_data.get("address", ""),
                    city=form.cleaned_data.get("city", ""),
                    state=form.cleaned_data.get("state", ""),
                    zip=form.cleaned_data.get("zip", ""),
                    neighborhood=form.cleaned_data.get("neighborhood", ""),
                    notes=form.cleaned_data.get("notes", ""),
                    grade=form.cleaned_data.get("grade", ""),
                    previous_school=form.cleaned_data.get("previous_school", ""),
                    school_district=form.cleaned_data.get("school_district", ""),
                )
                if phone := form.cleaned_data.get("phone"):
                    PhoneNumber.objects.create(
                        person=person,
                        number=phone,
                        comment=form.cleaned_data.get("phone_comment", ""),
                    )
            return redirect(f"/people/{person.id}")
    else:
        form = PersonForm()

    return render_main_template(
        request,
        "crm",
        render_to_string(
            "person_form.html",
            {
                "form": form,
                "is_new": True,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        "Add a new person",
    )


@login_required()
def edit_person(request: DstHttpRequest, person_id: int):
    person = Person.objects.filter(organization=request.org, id=person_id).first()
    if person is None:
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound()

    from django import forms

    class PersonEditForm(forms.Form):
        first_name = forms.CharField(max_length=255, required=True, label="First Name")
        last_name = forms.CharField(max_length=255, required=False, label="Last Name")
        display_name = forms.CharField(max_length=255, required=False, label="Short Name")
        email = forms.CharField(max_length=255, required=False, label="Email")
        gender = forms.ChoiceField(
            choices=[("Unknown", "Unknown"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
            required=False,
            label="Gender",
        )
        address = forms.CharField(max_length=255, required=False, label="Address")
        city = forms.CharField(max_length=255, required=False, label="City")
        state = forms.CharField(max_length=255, required=False, label="State")
        zip = forms.CharField(max_length=255, required=False, label="Zip")
        neighborhood = forms.CharField(max_length=255, required=False, label="Neighborhood")
        notes = forms.CharField(widget=forms.Textarea, required=False, label="Notes")
        grade = forms.CharField(max_length=255, required=False, label="Current Grade")
        previous_school = forms.CharField(max_length=255, required=False, label="Previous School")
        school_district = forms.CharField(max_length=255, required=False, label="School District")
        phone = forms.CharField(max_length=255, required=False, label="Phone")
        phone_comment = forms.CharField(max_length=255, required=False, label="Phone Comment")

    if request.method == "POST":
        form = PersonEditForm(request.POST)
        if form.is_valid():
            with atomic():
                person.first_name = form.cleaned_data["first_name"]
                person.last_name = form.cleaned_data.get("last_name", "")
                person.display_name = form.cleaned_data.get("display_name", "")
                person.email = form.cleaned_data.get("email", "")
                person.gender = form.cleaned_data.get("gender", "Unknown")
                person.address = form.cleaned_data.get("address", "")
                person.city = form.cleaned_data.get("city", "")
                person.state = form.cleaned_data.get("state", "")
                person.zip = form.cleaned_data.get("zip", "")
                person.neighborhood = form.cleaned_data.get("neighborhood", "")
                person.notes = form.cleaned_data.get("notes", "")
                person.grade = form.cleaned_data.get("grade", "")
                person.previous_school = form.cleaned_data.get("previous_school", "")
                person.school_district = form.cleaned_data.get("school_district", "")
                person.save()

                existing_phone = person.phonenumber_set.first()
                if phone := form.cleaned_data.get("phone"):
                    if existing_phone:
                        existing_phone.number = phone
                        existing_phone.comment = form.cleaned_data.get("phone_comment", "")
                        existing_phone.save()
                    else:
                        PhoneNumber.objects.create(
                            person=person,
                            number=phone,
                            comment=form.cleaned_data.get("phone_comment", ""),
                        )
                elif existing_phone:
                    existing_phone.delete()

            return redirect(f"/people/{person.id}")
    else:
        first_phone = person.phonenumber_set.first()
        form = PersonEditForm(
            initial={
                "first_name": person.first_name,
                "last_name": person.last_name,
                "display_name": person.display_name,
                "email": person.email,
                "gender": person.gender,
                "address": person.address,
                "city": person.city,
                "state": person.state,
                "zip": person.zip,
                "neighborhood": person.neighborhood,
                "notes": person.notes,
                "grade": person.grade,
                "previous_school": person.previous_school,
                "school_district": person.school_district,
                "phone": first_phone.number if first_phone else "",
                "phone_comment": first_phone.comment if first_phone else "",
            }
        )

    return render_main_template(
        request,
        "crm",
        render_to_string(
            "person_form.html",
            {
                "form": form,
                "is_new": False,
                "person": person,
                "org_config": get_org_config(request.org),
            },
            request=request,
        ),
        f"Edit {person.get_name()}",
    )


@login_required()
def settings_view(request: DstHttpRequest, **kwargs):
    from django.template.loader import render_to_string
    return render_main_template(
        request,
        "settings",
        render_to_string("settings.html", request=request),
        "Settings",
    )


@login_required()
def all_tags(request: DstHttpRequest):
    from django.template.loader import render_to_string
    from dst.models import Tag
    tags = Tag.objects.filter(organization=request.org).order_by("title")
    return render_main_template(
        request,
        "crm",
        render_to_string("all_tags.html", {"tags": tags}, request=request),
        "All Tags",
        selected_button="all_tags",
    )


@login_required()
def json_people(request: DstHttpRequest):
    term = request.GET.get("term", "")
    people = Person.objects.filter(organization=request.org)
    if term:
        people = people.filter(
            Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(display_name__icontains=term) | Q(email__icontains=term)
        )
    results = [{"id": p.id, "label": p.get_name() + " " + p.last_name, "value": p.get_name()} for p in people.order_by("display_name", "first_name")[:20]]
    return JsonResponse(results, safe=False)


@login_required()
def json_tags(request: DstHttpRequest, person_id: int):
    person = Person.objects.filter(organization=request.org, id=person_id).first()
    if not person:
        return JsonResponse([], safe=False)
    tags = person.tags.values("id", "title")
    return JsonResponse(list(tags), safe=False)


@login_required()
def add_tag(request: DstHttpRequest, person_id: int):
    person = Person.objects.filter(organization=request.org, id=person_id).first()
    if not person:
        return JsonResponse({"error": "not found"}, status=404)
    title = request.POST.get("title", "")
    tag_id = request.POST.get("tagId", "")
    if tag_id:
        tag = Tag.objects.filter(id=tag_id, organization=request.org).first()
    elif title:
        tag, _ = Tag.objects.get_or_create(title=title, organization=request.org)
    else:
        return JsonResponse({"error": "no tag"}, status=400)
    if tag:
        person.tags.add(tag)
        TagChange.objects.create(person=person, tag=tag, creator=request.user, was_add=True)
    return JsonResponse({"id": tag.id, "title": tag.title})


@login_required()
def remove_tag(request: DstHttpRequest, person_id: int, tag_id: int):
    person = Person.objects.filter(organization=request.org, id=person_id).first()
    tag = Tag.objects.filter(id=tag_id, organization=request.org).first()
    if person and tag:
        person.tags.remove(tag)
        TagChange.objects.create(person=person, tag=tag, creator=request.user, was_add=False)
    return JsonResponse({"ok": True})


@login_required()
def view_tag(request: DstHttpRequest, tag_id: int):
    tag = Tag.objects.filter(organization=request.org, id=tag_id).first()
    if not tag:
        return HttpResponseNotFound()
    members = Person.objects.filter(organization=request.org, tags=tag).order_by("display_name", "first_name")
    return render_main_template(
        request, "crm",
        render_to_string("view_tag.html", {"tag": tag, "members": members, "org_config": get_org_config(request.org)}, request=request),
        f"Tag: {tag.title}",
    )


@login_required()
def edit_tag(request: DstHttpRequest, tag_id: int):
    tag = Tag.objects.filter(organization=request.org, id=tag_id).first()
    if not tag:
        return HttpResponseNotFound()
    if request.method == "POST":
        tag.title = request.POST.get("title", tag.title)
        tag.show_in_jc = request.POST.get("show_in_jc") == "on"
        tag.show_in_attendance = request.POST.get("show_in_attendance") == "on"
        tag.save()
        return redirect(f"/viewTag/{tag.id}")
    return render_main_template(
        request, "crm",
        render_to_string("edit_tag.html", {"tag": tag, "org_config": get_org_config(request.org)}, request=request),
        f"Edit tag: {tag.title}",
    )


@login_required()
def view_task_list(request: DstHttpRequest, task_list_id: int):
    tl = TaskList.objects.filter(organization=request.org, id=task_list_id).first()
    if not tl:
        return HttpResponseNotFound()
    tasks = Task.objects.filter(task_list=tl).order_by("sort_order")
    return render_main_template(
        request, "crm",
        render_to_string("view_task_list.html", {"task_list": tl, "tasks": tasks, "org_config": get_org_config(request.org)}, request=request),
        f"Task list: {tl.title}",
    )


@login_required()
def add_comment(request: DstHttpRequest):
    person_id = request.POST.get("person", "")
    message = request.POST.get("message", "")
    if person_id and message:
        try:
            person = Person.objects.get(id=person_id, organization=request.org)
            Comment.objects.create(person=person, user=request.user, message=message)
        except Person.DoesNotExist:
            pass
    ref = request.POST.get("ref", "")
    if ref:
        return redirect(ref)
    return redirect("/people")
