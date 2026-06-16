from django.db import connection
from django.http import JsonResponse


def health(request):
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    return JsonResponse({"status": "ok" if db_ok else "db_error", "database": "connected" if db_ok else "error"})
