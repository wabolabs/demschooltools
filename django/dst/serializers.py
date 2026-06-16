from rest_framework import serializers

from dst.models import (
    AttendanceCode,
    AttendanceDay,
    AttendanceRule,
    Chapter,
    Entry,
    ManualChange,
    Organization,
    Person,
    Section,
    Tag,
    User,
    UserRole,
)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "short_name",
            "timezone",
            "late_time",
            "show_custodia",
            "show_attendance",
            "show_electronic_signin",
            "show_accounting",
            "show_roles",
            "enable_case_references",
        ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "id",
            "organization_id",
            "title",
            "use_student_display",
            "show_in_jc",
            "show_in_attendance",
            "show_in_menu",
            "show_in_account_balances",
            "show_in_roles",
        ]


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "id",
            "organization_id",
            "first_name",
            "last_name",
            "display_name",
            "email",
            "gender",
            "dob",
            "grade",
            "notes",
            "tags",
            "pin",
            "custodia_start_date",
            "custodia_show_as_absent",
        ]


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "organization_id",
            "is_active",
            "roles",
        ]


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ["id", "user_id", "role"]


class AttendanceCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceCode
        fields = [
            "id",
            "organization_id",
            "code",
            "description",
            "color",
            "counts_toward_attendance",
            "not_counted",
        ]


class AttendanceDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceDay
        fields = [
            "id",
            "person_id",
            "day",
            "code",
            "start_time",
            "end_time",
            "off_campus_departure_time",
            "off_campus_return_time",
            "off_campus_minutes_exempted",
        ]


class AttendanceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRule
        fields = [
            "id",
            "organization_id",
            "category",
            "person_id",
            "start_date",
            "end_date",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "absence_code",
            "min_hours",
            "latest_start_time",
            "earliest_departure_time",
            "exempt_from_fees",
        ]


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "title", "num", "organization_id", "deleted"]


class SectionSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)

    class Meta:
        model = Section
        fields = ["id", "title", "num", "chapter_id", "deleted", "number"]


class ManualChangeSerializer(serializers.ModelSerializer):
    effective_date_with_fallback = serializers.DateField(read_only=True)

    class Meta:
        model = ManualChange
        fields = [
            "id",
            "chapter_id",
            "section_id",
            "entry_id",
            "date_entered",
            "effective_date",
            "effective_date_with_fallback",
            "show_date_in_history",
            "user_id",
            "was_deleted",
            "was_created",
            "old_content",
            "new_content",
            "old_title",
            "new_title",
            "old_num",
            "new_num",
        ]


class EntrySerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)

    class Meta:
        model = Entry
        fields = [
            "id",
            "title",
            "num",
            "section_id",
            "deleted",
            "content",
            "is_breaking_res_plan",
            "number",
        ]
