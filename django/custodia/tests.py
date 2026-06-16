from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from custodia.models import Excuse, Override, StudentRequiredMinutes, Swipe, Year
from dst.models import Organization, Person, User

UserModel = User


def create_test_org(name="Test School"):
    return Organization.objects.create(name=name, short_name="TS")


def create_test_person(org, first_name="Student"):
    return Person.objects.create(
        organization=org,
        first_name=first_name,
        last_name="Test",
    )


class SwipeModelTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.person = create_test_person(self.org)

    def test_create_swipe(self):
        now = timezone.now()
        swipe = Swipe.objects.create(
            person=self.person,
            swipe_day=now.date(),
            in_time=now,
        )
        self.assertIsNotNone(swipe.id)
        self.assertIsNone(swipe.out_time)

    def test_swipe_with_out_time(self):
        now = timezone.now()
        swipe = Swipe.objects.create(
            person=self.person,
            swipe_day=now.date(),
            in_time=now - timedelta(hours=3),
            out_time=now,
        )
        self.assertIsNotNone(swipe.out_time)

    def test_unique_constraint_no_out_time(self):
        today = date.today()
        Swipe.objects.create(
            person=self.person, swipe_day=today, in_time=timezone.now()
        )
        with self.assertRaises(Exception):
            Swipe.objects.create(
                person=self.person, swipe_day=today, in_time=timezone.now()
            )

    def test_allows_multiple_swipes_with_out_time(self):
        today = date.today()
        Swipe.objects.create(
            person=self.person,
            swipe_day=today,
            in_time=timezone.now() - timedelta(hours=4),
            out_time=timezone.now() - timedelta(hours=3),
        )
        Swipe.objects.create(
            person=self.person,
            swipe_day=today,
            in_time=timezone.now() - timedelta(hours=2),
            out_time=timezone.now() - timedelta(hours=1),
        )

    def test_str(self):
        now = timezone.now()
        swipe = Swipe.objects.create(
            person=self.person,
            swipe_day=now.date(),
            in_time=now,
        )
        self.assertIn(f"ID-{swipe.id}", str(swipe))
        self.assertIn(str(swipe.id), str(swipe))

    def test_swipe_day_index(self):
        now = timezone.now()
        swipe = Swipe.objects.create(
            person=self.person,
            swipe_day=date(2025, 6, 1),
            in_time=now,
        )
        found = Swipe.objects.filter(swipe_day=date(2025, 6, 1))
        self.assertIn(swipe, found)


class OverrideModelTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.person = create_test_person(self.org)

    def test_create_override(self):
        ov = Override.objects.create(person=self.person, date=date(2025, 5, 1))
        self.assertIsNotNone(ov.id)
        self.assertIsNotNone(ov.inserted_date)

    def test_unique_person_date(self):
        Override.objects.create(person=self.person, date=date(2025, 5, 1))
        with self.assertRaises(Exception):
            Override.objects.create(person=self.person, date=date(2025, 5, 1))

    def test_different_person_same_date(self):
        other = create_test_person(self.org, "Other")
        Override.objects.create(person=self.person, date=date(2025, 5, 1))
        Override.objects.create(person=other, date=date(2025, 5, 1))


class ExcuseModelTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.person = create_test_person(self.org)

    def test_create_excuse(self):
        exc = Excuse.objects.create(person=self.person, date=date(2025, 5, 1))
        self.assertIsNotNone(exc.id)
        self.assertIsNotNone(exc.inserted_date)

    def test_unique_person_date(self):
        Excuse.objects.create(person=self.person, date=date(2025, 5, 1))
        with self.assertRaises(Exception):
            Excuse.objects.create(person=self.person, date=date(2025, 5, 1))


class StudentRequiredMinutesTests(TestCase):
    def setUp(self):
        self.org = create_test_org()
        self.person = create_test_person(self.org)

    def test_create_required_minutes(self):
        srm = StudentRequiredMinutes.objects.create(
            person=self.person,
            fromdate=date(2025, 1, 1),
            required_minutes=345,
        )
        self.assertEqual(srm.required_minutes, 345)

    def test_multiple_entries_different_dates(self):
        StudentRequiredMinutes.objects.create(
            person=self.person, fromdate=date(2025, 1, 1), required_minutes=345
        )
        StudentRequiredMinutes.objects.create(
            person=self.person, fromdate=date(2025, 6, 1), required_minutes=300
        )
        entries = StudentRequiredMinutes.objects.filter(person=self.person).order_by(
            "fromdate"
        )
        self.assertEqual(entries.count(), 2)


class YearModelTests(TestCase):
    def setUp(self):
        self.org = create_test_org()

    def test_create_year(self):
        year = Year.objects.create(
            organization=self.org,
            name="2024-2025",
            from_time=timezone.make_aware(datetime(2024, 8, 1)),
            to_time=timezone.make_aware(datetime(2025, 7, 31, 23, 59, 59)),
        )
        self.assertEqual(year.name, "2024-2025")
        self.assertIsNotNone(year.inserted_date)
