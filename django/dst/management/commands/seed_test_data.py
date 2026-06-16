"""
Seed the database with random test data for local development.

Usage:
    uv run manage.py seed_test_data

Seeds an org named "Test School" (or uses existing), creates tag, year,
random students, and a few days of swipe/attendance data.
"""

import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from zoneinfo import ZoneInfo

from custodia.models import Swipe, Year
from dst.models import AttendanceDay, AttendanceWeek, Organization, OrganizationHost, Person, Tag

FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank",
    "Ivy", "Jack", "Kate", "Leo", "Mia", "Noah", "Olivia", "Paul",
    "Quinn", "Ria", "Sam", "Tina", "Uma", "Victor", "Wren", "Xander",
    "Yuki", "Zara", "Aiden", "Bella", "Caleb", "Daisy",
]

LAST_NAMES = [
    "Smith", "Jones", "Brown", "Taylor", "Wilson", "Davis", "Miller",
    "Garcia", "Martinez", "Lee", "Walker", "Harris", "Clark", "Lewis",
    "Young", "Allen", "King", "Wright", "Hill", "Scott",
]


class Command(BaseCommand):
    help = "Seed test data for local development"

    def _create_org(self):
        org, created = Organization.objects.get_or_create(
            name="Test School",
            defaults={
                "short_name": "TS",
                "show_custodia": True,
                "show_electronic_signin": True,
                "show_roles": True,
                "late_time": time(9, 0),
            },
        )
        if org.late_time is None:
            org.late_time = time(9, 0)
            org.save()
        for host in ("localhost", "localhost:8001", "localhost:8000"):
            OrganizationHost.objects.get_or_create(host=host, organization=org)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created org '{org.name}'"))
        else:
            self.stdout.write(f"Using existing org '{org.name}'")
        return org

    def _create_tag(self, org: Organization, title: str, **kwargs):
        tag, created = Tag.objects.get_or_create(
            title=title,
            organization=org,
            defaults={"show_in_attendance": True, **kwargs},
        )
        if created:
            self.stdout.write(f"  Created tag '{title}'")
        return tag

    def _create_year(self, org: Organization):
        today = date.today()
        year_start = today.replace(month=7, day=1)
        if today < year_start:
            year_start = year_start.replace(year=year_start.year - 1)
        year_end = year_start.replace(year=year_start.year + 1)
        name = f"{year_start.year}-{year_end.year}"

        year, created = Year.objects.get_or_create(
            organization=org,
            name=name,
            defaults={"from_time": datetime.combine(year_start, time.min, tzinfo=ZoneInfo("UTC")),
                      "to_time": datetime.combine(year_end, time.min, tzinfo=ZoneInfo("UTC"))},
        )
        if created:
            self.stdout.write(f"  Created year '{name}'")
        return year

    def _create_students(self, org: Organization, tag: Tag, count: int):
        existing = Person.objects.filter(organization=org).count()
        if existing >= count:
            self.stdout.write(f"  {existing} people already exist, skipping student creation")
            return

        created = 0
        for i in range(count - existing):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}@test.school"
            person = Person.objects.create(
                first_name=first,
                last_name=last,
                display_name=f"{first} {last}",
                email=email,
                organization=org,
                grade=random.choice(["9", "10", "11", "12"]),
            )
            person.tags.add(tag)
            created += 1
        if created:
            self.stdout.write(f"  Created {created} students")

    def _create_attendance_data(self, students, days_back: int):
        today = date.today()
        weekdays = []
        for i in range(days_back, 0, -1):
            d = today - timedelta(days=i)
            if d.weekday() < 5:
                weekdays.append(d)

        created_days = 0
        for person in students:
            for day in weekdays:
                _, was_created = AttendanceDay.objects.get_or_create(
                    person=person,
                    day=day,
                    defaults={
                        "start_time": time(8, random.randint(0, 30)),
                        "end_time": time(14 + random.choice([0, 0, 1]),
                                         random.randint(0, 59)),
                    },
                )
                if was_created:
                    created_days += 1

            monday = weekdays[0] - timedelta(days=weekdays[0].weekday())
            AttendanceWeek.objects.get_or_create(
                person=person,
                monday=monday,
                defaults={"extra_hours": round(random.uniform(0, 3), 1)},
            )

        if created_days:
            self.stdout.write(f"  Created {created_days} attendance day records")

    def _create_swipe_data(self, students, days_back: int):
        today = date.today()
        created_swipes = 0
        for person in students:
            for offset in range(days_back, 0, -1):
                day = today - timedelta(days=offset)
                if day.weekday() >= 5:
                    continue
                in_hour = 7 + random.randint(0, 2)
                in_min = random.randint(0, 59)
                out_hour = in_hour + 5 + random.randint(0, 2)
                out_min = random.randint(0, 59)
                in_dt = datetime.combine(day, time(in_hour, in_min), tzinfo=ZoneInfo("UTC"))
                out_dt = datetime.combine(day, time(out_hour, out_min), tzinfo=ZoneInfo("UTC"))

                _, was_created = Swipe.objects.get_or_create(
                    person=person,
                    swipe_day=day,
                    defaults={"in_time": in_dt, "out_time": out_dt},
                )
                if was_created:
                    created_swipes += 1
        if created_swipes:
            self.stdout.write(f"  Created {created_swipes} swipe records")

    @atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")
        org = self._create_org()

        current_tag = self._create_tag(org, "Current Student",
                                       use_student_display=True,
                                       show_in_attendance=True)
        self._create_tag(org, "Staff", use_student_display=False,
                         show_in_attendance=True)
        self._create_tag(org, "Absent Today", use_student_display=False,
                         show_in_attendance=True)

        self._create_year(org)

        student_count = 24
        self._create_students(org, current_tag, student_count)

        students = list(Person.objects.filter(
            organization=org, tags=current_tag
        ).order_by("?"))

        self._create_swipe_data(students, days_back=5)
        self._create_attendance_data(students, days_back=5)

        self.stdout.write(self.style.SUCCESS("Done seeding test data"))
