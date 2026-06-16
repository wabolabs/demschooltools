from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from dst.models import (
    AttendanceCode,
    AttendanceDay,
    AttendanceRule,
    AttendanceWeek,
    Chapter,
    Entry,
    ManualChange,
    Organization,
    OrganizationHost,
    Person,
    Section,
    Tag,
    UserRole,
    role_includes,
)

UserModel = get_user_model()


def create_test_org(name="Test School"):
    return Organization.objects.create(name=name, short_name="TS")


def create_test_user(org, username="test@example.com", role=UserRole.ALL_ACCESS):
    user = UserModel.objects.create_user(
        username=username,
        email=username,
        password="testpass123",
        organization=org,
    )
    UserRole.objects.create(user=user, role=role)
    return user


class OrganizationTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_str(self):
        self.assertEqual(str(self.org), f"{self.org.id}-Test School")

    def test_default_timezone(self):
        self.assertEqual(self.org.timezone, "America/New_York")

    def test_late_time_null_by_default(self):
        self.assertIsNone(self.org.late_time)


class OrganizationHostTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.host = OrganizationHost.objects.create(
            host="test.example.com", organization=self.org
        )

    def test_host_lookup(self):
        found = Organization.objects.get(hosts__host="test.example.com")
        self.assertEqual(found, self.org)

    def test_host_primary_key(self):
        self.assertEqual(self.host.pk, "test.example.com")


class TagTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_unique_title_per_org(self):
        Tag.objects.create(title="Students", organization=self.org)
        with self.assertRaises(Exception):
            Tag.objects.create(title="Students", organization=self.org)

    def test_same_title_different_org(self):
        other = create_test_org("Other School")
        Tag.objects.create(title="Students", organization=self.org)
        Tag.objects.create(title="Students", organization=other)

    def test_defaults(self):
        t = Tag.objects.create(title="Staff", organization=self.org)
        self.assertFalse(t.show_in_jc)
        self.assertFalse(t.show_in_attendance)
        self.assertTrue(t.show_in_menu)


class PersonTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_get_name_display_name(self):
        p = Person.objects.create(
            organization=self.org,
            first_name="John",
            last_name="Doe",
            display_name="Johnny",
        )
        self.assertEqual(p.get_name(), "Johnny")

    def test_get_name_fallback(self):
        p = Person.objects.create(
            organization=self.org,
            first_name="Jane",
            last_name="Doe",
        )
        self.assertEqual(p.get_name(), "Jane")

    def test_str(self):
        p = Person.objects.create(
            organization=self.org,
            first_name="Alice",
            last_name="Smith",
            display_name="Ali",
        )
        self.assertIn("Alice Smith", str(p))
        self.assertIn(str(self.org.id), str(p))

    def test_org_scoping(self):
        other = create_test_org("Other School")
        p1 = Person.objects.create(organization=self.org, first_name="A")
        p2 = Person.objects.create(organization=other, first_name="B")
        self.assertIn(p1, Person.objects.filter(organization=self.org))
        self.assertNotIn(p2, Person.objects.filter(organization=self.org))

    def test_custodia_fields_default(self):
        p = Person.objects.create(organization=self.org, first_name="Test")
        self.assertIsNone(p.custodia_show_as_absent)
        self.assertIsNone(p.custodia_start_date)


class UserTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_create_user(self):
        user = UserModel.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="testpass123",
            organization=self.org,
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))

    def test_has_role_all_access(self):
        user = create_test_user(self.org)
        self.assertTrue(user.hasRole(UserRole.VIEW_JC))
        self.assertTrue(user.hasRole(UserRole.ALL_ACCESS))
        self.assertTrue(user.hasRole(UserRole.ATTENDANCE))
        self.assertTrue(user.hasRole(UserRole.EDIT_MANUAL))

    def test_has_role_attendance_only(self):
        user = create_test_user(self.org, role=UserRole.ATTENDANCE)
        self.assertTrue(user.hasRole(UserRole.ATTENDANCE))
        self.assertFalse(user.hasRole(UserRole.ALL_ACCESS))
        self.assertFalse(user.hasRole(UserRole.VIEW_JC))

    def test_has_role_checkin_app(self):
        user = create_test_user(self.org, role=UserRole.CHECKIN_APP)
        self.assertTrue(user.hasRole(UserRole.CHECKIN_APP))
        self.assertFalse(user.hasRole(UserRole.ATTENDANCE))
        self.assertFalse(user.hasRole(UserRole.ALL_ACCESS))

    def test_user_str(self):
        user = create_test_user(self.org)
        self.assertEqual(str(user), user.name)

    def test_users_unique_email(self):
        create_test_user(self.org, username="same@email.com")
        with self.assertRaises(Exception):
            create_test_user(self.org, username="same@email.com")


class RoleInclusionTests(TestCase):
    def test_all_access_includes_all(self):
        self.assertTrue(role_includes(UserRole.ALL_ACCESS, UserRole.VIEW_JC))
        self.assertTrue(role_includes(UserRole.ALL_ACCESS, UserRole.EDIT_7_DAY_JC))
        self.assertTrue(role_includes(UserRole.ALL_ACCESS, UserRole.EDIT_MANUAL))
        self.assertTrue(role_includes(UserRole.ALL_ACCESS, UserRole.ATTENDANCE))
        self.assertTrue(role_includes(UserRole.ALL_ACCESS, UserRole.CHECKIN_APP))

    def test_edit_all_jc_hierarchy(self):
        self.assertTrue(role_includes(UserRole.EDIT_ALL_JC, UserRole.VIEW_JC))
        self.assertTrue(role_includes(UserRole.EDIT_ALL_JC, UserRole.EDIT_7_DAY_JC))
        self.assertTrue(
            role_includes(UserRole.EDIT_ALL_JC, UserRole.EDIT_RESOLUTION_PLANS)
        )
        self.assertFalse(role_includes(UserRole.EDIT_ALL_JC, UserRole.ATTENDANCE))
        self.assertFalse(role_includes(UserRole.EDIT_ALL_JC, UserRole.EDIT_MANUAL))

    def test_edit_31_day_jc_hierarchy(self):
        self.assertTrue(role_includes(UserRole.EDIT_31_DAY_JC, UserRole.VIEW_JC))
        self.assertTrue(role_includes(UserRole.EDIT_31_DAY_JC, UserRole.EDIT_7_DAY_JC))
        self.assertFalse(role_includes(UserRole.EDIT_31_DAY_JC, UserRole.EDIT_ALL_JC))

    def test_edit_7_day_jc_hierarchy(self):
        self.assertTrue(role_includes(UserRole.EDIT_7_DAY_JC, UserRole.VIEW_JC))
        self.assertTrue(
            role_includes(UserRole.EDIT_7_DAY_JC, UserRole.EDIT_RESOLUTION_PLANS)
        )
        self.assertFalse(role_includes(UserRole.EDIT_7_DAY_JC, UserRole.EDIT_31_DAY_JC))

    def test_view_jc_no_inclusion(self):
        self.assertFalse(role_includes(UserRole.VIEW_JC, UserRole.EDIT_7_DAY_JC))
        self.assertFalse(role_includes(UserRole.VIEW_JC, UserRole.ALL_ACCESS))

    def test_unknown_role_includes_nothing(self):
        self.assertFalse(role_includes("nonexistent-role", UserRole.VIEW_JC))


class ChapterTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_create_chapter(self):
        c = Chapter.objects.create(
            title="Test Chapter", num="1", organization=self.org
        )
        self.assertEqual(str(c), "1 Test Chapter")

    def test_default_manager_excludes_deleted(self):
        Chapter.objects.create(
            title="Deleted", num="2", organization=self.org, deleted=True
        )
        self.assertEqual(list(Chapter.objects.all()), [])

    def test_all_objects_includes_deleted(self):
        c = Chapter.objects.create(
            title="Deleted", num="2", organization=self.org, deleted=True
        )
        self.assertIn(c, Chapter.all_objects.all())

    def test_default_manager_orders_by_num(self):
        Chapter.objects.create(title="B", num="2", organization=self.org)
        Chapter.objects.create(title="A", num="1", organization=self.org)
        chapters = list(Chapter.objects.all())
        self.assertEqual(chapters[0].title, "A")
        self.assertEqual(chapters[1].title, "B")

    def test_org_scoping(self):
        other = create_test_org("Other")
        c1 = Chapter.objects.create(title="C1", num="1", organization=self.org)
        Chapter.objects.create(title="C2", num="1", organization=other)
        self.assertIn(c1, Chapter.objects.filter(organization=self.org))


class SectionTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.chapter = Chapter.objects.create(
            title="Ch", num="1", organization=self.org
        )

    def test_number_format(self):
        s = Section.objects.create(title="Sec", num="1", chapter=self.chapter)
        self.assertEqual(s.number(), "11")

    def test_section_str(self):
        s = Section.objects.create(title="Sec", num="1", chapter=self.chapter)
        self.assertEqual(str(s), "11 Sec")

    def test_cascade_on_chapter_delete(self):
        Section.objects.create(title="Sec", num="1", chapter=self.chapter)
        self.chapter.delete()
        self.assertEqual(list(self.chapter.sections.all()), [])


class EntryTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.chapter = Chapter.objects.create(
            title="Ch", num="1", organization=self.org
        )
        self.section = Section.objects.create(
            title="Sec", num="1", chapter=self.chapter
        )

    def test_number_format(self):
        e = Entry.objects.create(title="Ent", num="1", section=self.section)
        self.assertEqual(e.number(), "11.1")

    def test_changes_for_render(self):
        e = Entry.objects.create(title="Ent", num="1", section=self.section)
        self.assertEqual(e.changes_for_render(), [])

    def test_changes_for_render_with_changes(self):
        e = Entry.objects.create(title="Ent", num="1", section=self.section)
        ManualChange.objects.create(
            entry=e, new_content="updated", was_created=True
        )
        self.assertEqual(len(e.changes_for_render()), 1)


class ManualChangeTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.chapter = Chapter.objects.create(
            title="Ch", num="1", organization=self.org
        )

    def test_effective_date_fallback(self):
        mc = ManualChange.objects.create(chapter=self.chapter, new_content="x")
        self.assertEqual(mc.effective_date_with_fallback(), mc.date_entered.date())

    def test_effective_date_explicit(self):
        mc = ManualChange.objects.create(
            chapter=self.chapter, new_content="x", effective_date=date(2025, 1, 1)
        )
        self.assertEqual(mc.effective_date_with_fallback(), date(2025, 1, 1))


class AttendanceCodeTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_create_code(self):
        code = AttendanceCode.objects.create(
            organization=self.org,
            code="P",
            description="Present",
            color="#00ff00",
            counts_toward_attendance=True,
        )
        self.assertEqual(str(code.code), "P")
        self.assertTrue(code.counts_toward_attendance)

    def test_not_counted_default(self):
        code = AttendanceCode.objects.create(
            organization=self.org,
            code="X",
            description="Excused",
            color="#ff0000",
        )
        self.assertFalse(code.counts_toward_attendance)
        self.assertFalse(code.not_counted)


class AttendanceDayTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.person = Person.objects.create(organization=self.org, first_name="Test")

    def test_unique_person_day(self):
        AttendanceDay.objects.create(person=self.person, day=date(2025, 1, 1))
        with self.assertRaises(Exception):
            AttendanceDay.objects.create(person=self.person, day=date(2025, 1, 1))

    def test_create_attendance_day(self):
        ad = AttendanceDay.objects.create(
            person=self.person, day=date(2025, 1, 1), code="P"
        )
        self.assertEqual(ad.code, "P")
        self.assertIsNone(ad.start_time)
        self.assertIsNone(ad.end_time)


class AttendanceWeekTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.person = Person.objects.create(organization=self.org, first_name="Test")

    def test_unique_person_monday(self):
        AttendanceWeek.objects.create(person=self.person, monday=date(2025, 1, 6))
        with self.assertRaises(Exception):
            AttendanceWeek.objects.create(person=self.person, monday=date(2025, 1, 6))

    def test_extra_hours_default(self):
        aw = AttendanceWeek.objects.create(
            person=self.person, monday=date(2025, 1, 6)
        )
        self.assertEqual(aw.extra_hours, 0)


class AttendanceRuleTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_create_rule(self):
        rule = AttendanceRule.objects.create(
            organization=self.org,
            monday=True,
            tuesday=True,
            wednesday=True,
            thursday=True,
            friday=True,
            exempt_from_fees=False,
            absence_code="U",
        )
        self.assertTrue(rule.monday)
        self.assertFalse(rule.exempt_from_fees)
        self.assertEqual(rule.absence_code, "U")
