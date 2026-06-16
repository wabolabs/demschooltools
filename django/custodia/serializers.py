from rest_framework import serializers


class SchoolInfoSerializer(serializers.Serializer):
    _id = serializers.IntegerField(source="id")
    name = serializers.CharField()
    timezone = serializers.CharField()


class IsAdminResponseSerializer(serializers.Serializer):
    admin = serializers.CharField(allow_null=True)
    school = SchoolInfoSerializer()


class StudentSummarySerializer(serializers.Serializer):
    _id = serializers.IntegerField()
    name = serializers.CharField()
    last_swipe_type = serializers.CharField()
    swiped_today_late = serializers.BooleanField(default=False)
    is_teacher = serializers.BooleanField(default=False)
    in_today = serializers.BooleanField(default=False)
    absent_today = serializers.BooleanField(default=False)
    last_swipe_date = serializers.DateField(allow_null=True)


class StudentsTodayResponseSerializer(serializers.Serializer):
    students = StudentSummarySerializer(many=True)


class SwipeDataSerializer(serializers.Serializer):
    _id = serializers.IntegerField()
    day = serializers.DateField()
    nice_in_time = serializers.CharField()
    nice_out_time = serializers.CharField()
    student_id = serializers.IntegerField()
    out_time = serializers.DateTimeField(allow_null=True)
    in_time = serializers.DateTimeField(allow_null=True)


class DayDataSerializer(serializers.Serializer):
    absent = serializers.BooleanField()
    override = serializers.BooleanField()
    excused = serializers.BooleanField()
    day = serializers.DateField()
    total_mins = serializers.IntegerField()
    swipes = SwipeDataSerializer(many=True)
    short = serializers.BooleanField()
    valid = serializers.BooleanField()


class StudentDetailSerializer(serializers.Serializer):
    _id = serializers.IntegerField()
    absent_today = serializers.BooleanField()
    days = DayDataSerializer(many=True)
    name = serializers.CharField()
    required_minutes = serializers.IntegerField()
    total_hours = serializers.FloatField()
    last_swipe_date = serializers.DateField(allow_null=True)
    total_abs = serializers.IntegerField()
    total_days = serializers.IntegerField()
    total_excused = serializers.IntegerField()
    total_overrides = serializers.IntegerField()
    total_short = serializers.IntegerField()
    start_date = serializers.DateField(allow_null=True)
    last_swipe_type = serializers.CharField()
    in_today = serializers.BooleanField()


class StudentDetailResponseSerializer(serializers.Serializer):
    student = StudentDetailSerializer()


class ReportStudentSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    _id = serializers.IntegerField()
    name = serializers.CharField()
    total_hours = serializers.FloatField()
    good = serializers.IntegerField()
    short = serializers.IntegerField()
    overrides = serializers.IntegerField()
    excuses = serializers.IntegerField()
    unexcused = serializers.IntegerField()


class ReportYearsResponseSerializer(serializers.Serializer):
    years = serializers.ListField(child=serializers.CharField())
    current_year = serializers.CharField(allow_null=True)


class YearCreateSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()


class YearCreateResponseSerializer(serializers.Serializer):
    made = serializers.DictField(child=serializers.CharField())


class YearDeleteSerializer(serializers.Serializer):
    year_name = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
