import uuid
from datetime import date, datetime, timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
import json

from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, Client, FinanceRecord, HealthDeclaration, PersonalEvent


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _get_base_context():
    return {"today": timezone.localdate()}


# ── Zodiac helper ──────────────────────────────────────────────────────────────

def _get_zodiac(birth_date):
    """Return (sign_hebrew, symbol, beauty_tip) or None if no birth_date."""
    if not birth_date:
        return None
    m, d = birth_date.month, birth_date.day
    if   (m == 3 and d >= 21) or (m == 4 and d <= 19): return ("טלה",     "♈", "האנרגיה שלך גבוהה היום – זמן מושלם לטיפול פנים מחדש!")
    if   (m == 4 and d >= 20) or (m == 5 and d <= 20): return ("שור",     "♉", "פינוק הגוף ממש בא לך היום – כיפה מושלמת!")
    if   (m == 5 and d >= 21) or (m == 6 and d <= 20): return ("תאומים",  "♊", "נסי סגנון חדש ומרענן – היום הוא יום של שינויים טובים!")
    if   (m == 6 and d >= 21) or (m == 7 and d <= 22): return ("סרטן",    "♋", "הזמן הטוב ביותר לטפל בעצמך ולגלות יופי פנימי!")
    if   (m == 7 and d >= 23) or (m == 8 and d <= 22): return ("אריה",    "♌", "הבליטי את הקרינה הטבעית שלך – היום הוא יום הזוהר שלך!")
    if   (m == 8 and d >= 23) or (m == 9 and d <= 22): return ("בתולה",   "♍", "יום מצוין לטיפולי עור מדוקדקים – הפרטים חשובים לך ובצדק!")
    if   (m == 9 and d >= 23) or (m == 10 and d <= 22): return ("מאזניים", "♎", "האסתטיקה היא השפה שלך – היום תהיי מדהימה!")
    if   (m == 10 and d >= 23) or (m == 11 and d <= 21): return ("עקרב",   "♏", "הכוח הפנימי שלך בא לידי ביטוי – טיפוח עצמי מעצים!")
    if   (m == 11 and d >= 22) or (m == 12 and d <= 21): return ("קשת",    "♐", "פגישה עם דקל תמלא אותך אנרגיה חדשה לדרך!")
    if   (m == 12 and d >= 22) or (m == 1 and d <= 19): return ("גדי",     "♑", "השקעה בעצמך היא תמיד נכונה – ומשתלמת!")
    if   (m == 1 and d >= 20) or (m == 2 and d <= 18): return ("דלי",     "♒", "ייחודיות היא החוזק שלך – היום היא מיוחדת בצורה שלה!")
    return ("דגים", "♓", "הרגישות שלך היא יתרון – פינוק עצמי הוא חובה היום!")


# ── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = timezone.localdate()
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)

    today_appointments = (
        Appointment.objects.filter(start_time__date=today)
        .select_related("client")
        .prefetch_related("client__health_declaration")
        .order_by("start_time")
    )

    HEALTH_MSG = "היי {name}, כאן דקל קוסמטיקס. מחכה לראות אותך בטיפול שלנו! לתיאום סופי ומקצועי, אשמח אם תמלאי את הצהרת הבריאות הקצרה בקישור המאובטח הבא: {url}"
    appointment_rows = []
    for appt in today_appointments:
        client = appt.client
        try:
            hd = client.health_declaration
        except HealthDeclaration.DoesNotExist:
            hd = HealthDeclaration.objects.create(client=client, is_submitted=False)
        health_url = ""
        health_submitted = False
        wa_health_url = ""
        health_url = request.build_absolute_uri(
            reverse("management:health_form", kwargs={"id": hd.id})
        )
        health_submitted = hd.is_submitted
        if not health_submitted:
            msg = HEALTH_MSG.format(name=client.name, url=health_url)
            wa_health_url = f"https://wa.me/{client.get_wa_phone()}?text={quote(msg)}"
        appointment_rows.append({
            "appt": appt,
            "health_url": health_url,
            "health_submitted": health_submitted,
            "wa_health_url": wa_health_url,
            "wa_confirm_url": f"https://wa.me/{client.get_wa_phone()}?text={quote('היי ' + client.name + ', רציתי לאשר את התור שלך היום בשעה ' + appt.start_time.strftime('%H:%M') + ' 💅✨')}",
        })

    income_today = (
        FinanceRecord.objects.filter(
            record_type=FinanceRecord.TYPE_INCOME,
            date=today,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    income_week = (
        FinanceRecord.objects.filter(
            record_type=FinanceRecord.TYPE_INCOME,
            date__range=(start_week, end_week),
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # Zodiac cards: one card per unique client with a known birth_date
    zodiac_cards = []
    seen = set()
    for appt in today_appointments:
        c = appt.client
        if c.pk not in seen:
            seen.add(c.pk)
            z = _get_zodiac(c.birth_date)
            if z:
                sign, symbol, tip = z
                zodiac_cards.append({
                    "name": c.name,
                    "sign": sign,
                    "symbol": symbol,
                    "tip": tip,
                    "time": appt.start_time,
                })

    context = _get_base_context() | {
        "today_appointments": today_appointments,
        "appointment_rows": appointment_rows,
        "zodiac_cards": zodiac_cards,
        "income_today": income_today,
        "income_week": income_week,
        "start_week": start_week,
        "end_week": end_week,
    }
    return render(request, "management/dashboard.html", context)


# ── Clients ────────────────────────────────────────────────────────────────────

@login_required
def client_list(request):
    clients = Client.objects.all().order_by("name")
    return render(request, "management/client_list.html", _get_base_context() | {"clients": clients})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    appointments = client.appointments.order_by("-start_time")
    return render(
        request,
        "management/client_detail.html",
        _get_base_context() | {"client": client, "appointments": appointments},
    )


@login_required
def client_create_ajax(request):
    """AJAX: create a client inline from the booking modal without page navigation."""
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    name = (request.POST.get("name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    email = (request.POST.get("email") or "").strip() or None
    age_raw = (request.POST.get("age") or "").strip()
    birth_date = request.POST.get("birth_date") or None
    notes = request.POST.get("notes") or ""
    age = int(age_raw) if age_raw.isdigit() else None

    if not name or not phone:
        return JsonResponse({"ok": False, "error": "שם וטלפון הם שדות חובה"}, status=400)

    client = Client.objects.create(
        name=name, phone=phone, email=email,
        age=age, birth_date=birth_date or None, notes=notes,
    )
    return JsonResponse({"ok": True, "id": client.pk, "name": client.name, "phone": client.phone})


@login_required
def client_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        email = (request.POST.get("email") or "").strip() or None
        age_raw = (request.POST.get("age") or "").strip()
        birth_date = request.POST.get("birth_date") or None
        notes = request.POST.get("notes") or ""

        age = int(age_raw) if age_raw.isdigit() else None

        if name and phone:
            client = Client.objects.create(
                name=name,
                phone=phone,
                email=email,
                age=age,
                birth_date=birth_date or None,
                notes=notes,
            )
            try:
                hd = client.health_declaration
            except HealthDeclaration.DoesNotExist:
                hd = HealthDeclaration.objects.create(client=client, is_submitted=False)
            health_url = request.build_absolute_uri(reverse("management:health_form", kwargs={"id": hd.id}))
            msg = f"היי {client.name}, כאן דקל קוסמטיקס. מחכה לראות אותך בטיפול שלנו! לתיאום סופי ומקצועי, אשמח אם תמלאי את הצהרת הבריאות הקצרה בקישור המאובטח הבא: {health_url}"
            wa_url = f"https://wa.me/{client.get_wa_phone()}?text={quote(msg)}"
            return redirect(f"{reverse('management:dashboard')}?new_wa_url={quote(wa_url)}")

    return render(request, "management/client_form.html", _get_base_context())


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        email = (request.POST.get("email") or "").strip() or None
        age_raw = (request.POST.get("age") or "").strip()
        birth_date = request.POST.get("birth_date") or None
        notes = request.POST.get("notes") or ""

        age = int(age_raw) if age_raw.isdigit() else None

        if name and phone:
            client.name = name
            client.phone = phone
            client.email = email
            client.age = age
            client.birth_date = birth_date or None
            client.notes = notes
            client.save()
            return redirect("management:client_list")

    return render(request, "management/client_form.html", _get_base_context() | {"client": client})


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        client.delete()
        return redirect("management:client_list")
    return redirect("management:client_list")


# ── Appointments ───────────────────────────────────────────────────────────────

@login_required
def appointment_list(request):
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    appointments = (
        Appointment.objects.filter(start_time__date=selected_date)
        .select_related("client")
        .order_by("start_time")
    )

    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    week_appointments = Appointment.objects.filter(
        start_time__date__range=(start_of_week, end_of_week)
    ).select_related("client")

    personal_events = PersonalEvent.objects.filter(
        start_time__date__range=(start_of_week, end_of_week)
    )
    clients = Client.objects.all().order_by("name")

    reschedule_id = request.GET.get("reschedule_id")
    return render(
        request,
        "management/appointment_list.html",
        _get_base_context() | {
            "selected_date": selected_date,
            "appointments": appointments,
            "week_appointments": week_appointments,
            "personal_events": personal_events,
            "clients": clients,
            "reschedule_id": reschedule_id,
        },
    )


@login_required
def appointment_create(request):
    clients = Client.objects.all().order_by("name")
    if request.method == "POST":
        client_id = request.POST.get("client")
        service_type = request.POST.get("service_type")
        price = request.POST.get("price")
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")
        duration = request.POST.get("duration_minutes") or "60"
        notes = request.POST.get("notes", "")

        if client_id and service_type and price and date_str and time_str:
            client = get_object_or_404(Client, pk=client_id)
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())

            appointment = Appointment.objects.create(
                client=client,
                service_type=service_type,
                custom_price=price,
                start_time=start_dt,
                duration_minutes=int(duration),
                notes=notes,
            )
            FinanceRecord.objects.create(
                record_type=FinanceRecord.TYPE_INCOME,
                date=start_dt.date(),
                amount=price,
                category="טיפול לקוחה",
                description=(
                    f"תשלום עבור {appointment.get_service_type_display()} - {client.name}"
                ),
                appointment=appointment,
            )
            date_str = start_dt.strftime("%d/%m/%Y")
            time_str = start_dt.strftime("%H:%M")
            msg = f"היי {client.name}, קבענו! מחכה לך בתאריך {date_str} בשעה {time_str} בדקל קוסמטיקס."
            wa_url = f"https://wa.me/{client.get_wa_phone()}?text={quote(msg)}"
            return redirect(f"{reverse('management:dashboard')}?new_wa_url={quote(wa_url)}")

    return render(request, "management/appointment_form.html", _get_base_context() | {"clients": clients})


@login_required
def reschedule_appointment(request, appointment_id):
    """POST: Update appointment start_time. Returns wa_url for a WhatsApp rescheduling prompt."""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    raw = request.POST.get("new_start_datetime")
    if not raw and request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body)
            raw = data.get("new_start_datetime")
        except (json.JSONDecodeError, TypeError):
            pass
    if not raw:
        return JsonResponse({"success": False}, status=400)
    try:
        raw = raw.strip()[:16]
        start_dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
        start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
    except (ValueError, TypeError):
        return JsonResponse({"success": False}, status=400)

    appointment.start_time = start_dt
    appointment.save()

    # Keep the linked FinanceRecord date in sync with the new appointment date
    fr = appointment.finance_records.filter(record_type=FinanceRecord.TYPE_INCOME).first()
    if fr:
        fr.date = start_dt.date()
        fr.save(update_fields=["date"])

    # Build a WhatsApp rescheduling message for the client
    client = appointment.client
    date_str = start_dt.strftime("%d/%m/%Y")
    time_str = start_dt.strftime("%H:%M")
    msg = f"היי {client.name}, התור שלך הוזז! מחכה לך בתאריך {date_str} בשעה {time_str} בדקל קוסמטיקס 💅"
    wa_url = f"https://wa.me/{client.get_wa_phone()}?text={quote(msg)}"
    return JsonResponse({"success": True, "wa_url": wa_url})


# ── Finance ────────────────────────────────────────────────────────────────────

@login_required
def finance_dashboard(request):
    today = timezone.localdate()
    period = request.GET.get("period", "month")

    if period == "day":
        start = end = today
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "quarter":
        current_quarter = (today.month - 1) // 3 + 1
        start_month = 3 * (current_quarter - 1) + 1
        start = date(today.year, start_month, 1)
        end_month = start_month + 2
        end = (
            date(today.year, 12, 31)
            if end_month == 12
            else date(today.year, end_month + 1, 1) - timedelta(days=1)
        )
    else:  # month
        start = date(today.year, today.month, 1)
        end = (
            date(today.year, 12, 31)
            if today.month == 12
            else date(today.year, today.month + 1, 1) - timedelta(days=1)
        )

    records = FinanceRecord.objects.filter(date__range=(start, end))
    income = (
        records.filter(record_type=FinanceRecord.TYPE_INCOME).aggregate(total=Sum("amount"))["total"] or 0
    )
    expenses = (
        records.filter(record_type=FinanceRecord.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"] or 0
    )

    # ── Chart data ─────────────────────────────────────────────────────────────
    SERVICE_LABEL = {"face": "טיפול פנים", "brows": "עיצוב גבות", "gel": "לק ג'ל"}
    service_qs = (
        Appointment.objects.values("service_type").annotate(count=Count("id"))
    )
    service_chart = json.dumps({
        "labels": [SERVICE_LABEL.get(r["service_type"], r["service_type"]) for r in service_qs],
        "values": [r["count"] for r in service_qs],
    })

    age_brackets = [("18–25", 18, 25), ("26–35", 26, 35), ("36–45", 36, 45), ("46–55", 46, 55), ("56+", 56, 120)]
    age_labels, age_values = [], []
    for label, lo, hi in age_brackets:
        age_labels.append(label)
        age_values.append(Client.objects.filter(age__gte=lo, age__lte=hi).count())
    age_labels.append("לא ידוע")
    age_values.append(Client.objects.filter(age__isnull=True).count())
    age_chart = json.dumps({"labels": age_labels, "values": age_values})

    monthly_qs = (
        FinanceRecord.objects.filter(record_type=FinanceRecord.TYPE_INCOME)
        .annotate(m=TruncMonth("date")).values("m").annotate(total=Sum("amount")).order_by("m")
    )
    MONTH_HE = ["", "ינו", "פבר", "מרץ", "אפר", "מאי", "יוני", "יולי", "אוג", "ספט", "אוק", "נוב", "דצמ"]
    monthly_chart = json.dumps({
        "labels": [f"{MONTH_HE[r['m'].month]} {r['m'].year}" for r in monthly_qs],
        "values": [float(r["total"]) for r in monthly_qs],
    })

    return render(
        request,
        "management/finance_dashboard.html",
        _get_base_context() | {
            "records": records.order_by("-date"),
            "income": income,
            "expenses": expenses,
            "profit": income - expenses,
            "start": start,
            "end": end,
            "period": period,
            "period_choices": [("day", "יומי"), ("week", "שבועי"), ("month", "חודשי"), ("quarter", "רבעוני")],
            "service_chart": service_chart,
            "age_chart": age_chart,
            "monthly_chart": monthly_chart,
        },
    )


# ── Smart AI Chat ──────────────────────────────────────────────────────────────

MONTH_MAP = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5,
    "יוני": 6, "יולי": 7, "אוגוסט": 8, "ספטמבר": 9,
    "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
}
MONTH_NAME = {v: k for k, v in MONTH_MAP.items()}

SERVICE_MAP = {
    "לק ג'ל": "gel",
    "ג'ל":    "gel",
    "לק":     "gel",
    "גבות":   "brows",
    "פנים":   "face",
}


def _process_ai_question(q: str) -> str:
    """
    Pattern-match a Hebrew business question and return a Hebrew answer string.
    All queries go directly to the Django ORM – no external LLM needed.
    """
    today = timezone.localdate()

    # ── 1. Last visit for a named client ──────────────────────────────────────
    if ("מתי" in q or "פעם אחרונה" in q) and (
        "הייתה" in q or "היית" in q or "ביקר" in q or "פה" in q
    ):
        parts = q.split()
        name = None
        for i, w in enumerate(parts):
            if w == "מתי" and i + 1 < len(parts):
                name = parts[i + 1]
                break
        if not name:
            for i, w in enumerate(parts):
                if "הייתה" in w and i > 0:
                    name = parts[i - 1]
                    break
        if name:
            appt = (
                Appointment.objects.filter(client__name__icontains=name)
                .order_by("-start_time")
                .first()
            )
            if appt:
                return (
                    f"{appt.client.name} הייתה לאחרונה ב-"
                    f"{appt.start_time.strftime('%d/%m/%Y')} בשעה {appt.start_time.strftime('%H:%M')}, "
                    f"לטיפול {appt.get_service_type_display()}."
                )
            return f"לא מצאתי תורים עבור לקוחה בשם '{name}'."
        return "לא הצלחתי לזהות שם לקוחה. נסי: 'מתי דנה הייתה פה פעם אחרונה?'"

    # ── 2. How many times did a client visit ──────────────────────────────────
    if "כמה פעמים" in q:
        clients = Client.objects.all()
        for client in clients:
            first_name = client.name.split()[0]
            if client.name in q or first_name in q:
                n = client.appointments.count()
                return f"{client.name} ביקרה {n} פעמים."
        return "לא מצאתי שם לקוחה בשאלה."

    # ── 3. Monthly earnings ────────────────────────────────────────────────────
    if "כמה הרווחתי" in q or ("הכנסה" in q and "חודש" in q):
        for month_name, num in MONTH_MAP.items():
            if month_name in q:
                year = today.year
                start = date(year, num, 1)
                end = (
                    date(year, 12, 31)
                    if num == 12
                    else date(year, num + 1, 1) - timedelta(days=1)
                )
                total = (
                    FinanceRecord.objects.filter(
                        record_type=FinanceRecord.TYPE_INCOME, date__range=(start, end)
                    ).aggregate(t=Sum("amount"))["t"]
                    or 0
                )
                return f"הכנסות חודש {month_name} {year}: {total:,.0f} ₪"
        # No specific month – return current month
        start = date(today.year, today.month, 1)
        end = (
            date(today.year, 12, 31)
            if today.month == 12
            else date(today.year, today.month + 1, 1) - timedelta(days=1)
        )
        total = (
            FinanceRecord.objects.filter(
                record_type=FinanceRecord.TYPE_INCOME, date__range=(start, end)
            ).aggregate(t=Sum("amount"))["t"]
            or 0
        )
        return f"הכנסות החודש הנוכחי ({MONTH_NAME.get(today.month, str(today.month))} {today.year}): {total:,.0f} ₪"

    # ── 4. Most frequent (loyal) client ───────────────────────────────────────
    if (
        "הכי תכופה" in q
        or "הכי הרבה פעמים" in q
        or "הכי הרבה תורים" in q
        or "מגיעה הכי הרבה" in q
        or ("תכוף" in q and "לקוח" in q)
        or ("נאמנה" in q and "לקוח" in q)
    ):
        result = (
            Client.objects.annotate(num=Count("appointments"))
            .order_by("-num")
            .first()
        )
        if result and result.num > 0:
            return f"הלקוחה הכי תכופה היא {result.name} עם {result.num} ביקורים."
        return "אין מספיק נתונים עדיין."

    # ── 5. Most profitable (revenue-generating) client ────────────────────────
    if (
        "הכי רווחית" in q
        or "הכי הרבה כסף" in q
        or ("הכי" in q and "מביאה" in q)
        or ("רווח" in q and "לקוח" in q)
    ):
        result = (
            Client.objects.annotate(revenue=Sum("appointments__custom_price"))
            .order_by("-revenue")
            .first()
        )
        if result and result.revenue:
            return (
                f"הלקוחה הכי רווחית היא {result.name} "
                f"עם הכנסה כוללת של {result.revenue:,.0f} ₪."
            )
        return "אין מספיק נתונים עדיין."

    # ── 6. Most profitable month ──────────────────────────────────────────────
    if "הכי רווחי" in q or "החודש הטוב ביותר" in q or ("הרבה הכנסה" in q and "חודש" in q):
        result = (
            FinanceRecord.objects.filter(record_type=FinanceRecord.TYPE_INCOME)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("-total")
            .first()
        )
        if result and result["total"]:
            m = result["month"]
            return (
                f"החודש הכי רווחי היה {MONTH_NAME.get(m.month, str(m.month))} {m.year} "
                f"עם הכנסה של {result['total']:,.0f} ₪."
            )
        return "אין מספיק נתונים עדיין."

    # ── 7. Treatment-type count in a given period ─────────────────────────────
    for service_label, service_code in SERVICE_MAP.items():
        if service_label in q:
            qs = Appointment.objects.filter(service_type=service_code)
            if "השבוע" in q or "שבוע" in q:
                start_week = today - timedelta(days=today.weekday())
                end_week = start_week + timedelta(days=6)
                n = qs.filter(start_time__date__range=(start_week, end_week)).count()
                return f"ביצעת {n} טיפולי {service_label} השבוע."
            elif "החודש" in q or "חודש" in q:
                sm = date(today.year, today.month, 1)
                em = (
                    date(today.year, 12, 31)
                    if today.month == 12
                    else date(today.year, today.month + 1, 1) - timedelta(days=1)
                )
                n = qs.filter(start_time__date__range=(sm, em)).count()
                return f"ביצעת {n} טיפולי {service_label} החודש."
            else:
                n = qs.count()
                return f"ביצעת {n} טיפולי {service_label} בסך הכל."

    # ── 8. Total client count ──────────────────────────────────────────────────
    if "כמה לקוחות" in q or "מספר לקוחות" in q:
        n = Client.objects.count()
        return f"יש לך {n} לקוחות רשומות במערכת."

    # ── 9. Appointment count (period) ─────────────────────────────────────────
    if "כמה תורים" in q or "מספר תורים" in q:
        if "השבוע" in q or "שבוע" in q:
            sw = today - timedelta(days=today.weekday())
            ew = sw + timedelta(days=6)
            n = Appointment.objects.filter(start_time__date__range=(sw, ew)).count()
            return f"יש {n} תורים השבוע."
        if "החודש" in q or "חודש" in q:
            sm = date(today.year, today.month, 1)
            em = (
                date(today.year, 12, 31)
                if today.month == 12
                else date(today.year, today.month + 1, 1) - timedelta(days=1)
            )
            n = Appointment.objects.filter(start_time__date__range=(sm, em)).count()
            return f"יש {n} תורים החודש."
        n = Appointment.objects.count()
        return f"יש {n} תורים בסך הכל במערכת."

    # ── 10. Total income / expenses ───────────────────────────────────────────
    if "הכנסה כוללת" in q or "סך ההכנסות" in q or "כמה הרווחת סך הכל" in q or "סך הכנסות" in q:
        total = (
            FinanceRecord.objects.filter(record_type=FinanceRecord.TYPE_INCOME)
            .aggregate(t=Sum("amount"))["t"]
            or 0
        )
        return f"סך כל ההכנסות: {total:,.0f} ₪"

    if "הוצאות כוללות" in q or "סך ההוצאות" in q or "כמה הוצאות" in q:
        total = (
            FinanceRecord.objects.filter(record_type=FinanceRecord.TYPE_EXPENSE)
            .aggregate(t=Sum("amount"))["t"]
            or 0
        )
        return f"סך כל ההוצאות: {total:,.0f} ₪"

    # ── 11. Revenue by service type ───────────────────────────────────────────
    if "כמה הרווחתי מ" in q or ("הכנסה" in q and ("לק" in q or "פנים" in q or "גבות" in q)):
        for service_label, service_code in SERVICE_MAP.items():
            if service_label in q:
                total = (
                    Appointment.objects.filter(service_type=service_code)
                    .aggregate(t=Sum("custom_price"))["t"]
                    or 0
                )
                return f"הרווחת {total:,.0f} ₪ מטיפולי {service_label} בסך הכל."

    # ── Default / help message ────────────────────────────────────────────────
    return (
        "אני יכולה לענות על שאלות כמו:\n"
        "• 'מתי דנה הייתה פה פעם אחרונה?'\n"
        "• 'כמה פעמים שרה הגיעה?'\n"
        "• 'כמה הרווחתי בינואר?'\n"
        "• 'מי הלקוחה הכי תכופה?'\n"
        "• 'מי הלקוחה הכי רווחית?'\n"
        "• 'איזה חודש הכי רווחי?'\n"
        "• 'כמה טיפולי לק ג\\'ל החודש?'\n"
        "• 'כמה לקוחות יש לי?'\n"
        "• 'כמה תורים השבוע?'\n"
        "• 'מה ההכנסה הכוללת?'"
    )


@login_required
def ai_chat(request):
    answer = ""
    question = ""
    if request.method == "POST":
        question = (request.POST.get("question") or "").strip()
        if question:
            answer = _process_ai_question(question)

    example_questions = [
        "מתי דנה הייתה פה פעם אחרונה?",
        "כמה פעמים שרה הגיעה?",
        "כמה הרווחתי בינואר?",
        "מי הלקוחה הכי תכופה?",
        "מי הלקוחה הכי רווחית?",
        "איזה חודש הכי רווחי?",
        "כמה טיפולי לק ג'ל החודש?",
        "כמה תורים השבוע?",
        "מה ההכנסה הכוללת?",
        "כמה לקוחות יש לי?",
    ]
    return render(
        request,
        "management/ai_chat.html",
        _get_base_context() | {
            "question": question,
            "answer": answer,
            "example_questions": example_questions,
        },
    )


# ── Health Declaration (public, no @login_required) ─────────────────────────────

def _get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@login_required
def health_declaration_new(request):
    """Generate a new UUID and redirect to the health form. Staff can share the resulting URL."""
    new_uuid = uuid.uuid4()
    return redirect("management:health_form", id=new_uuid)


def health_form_view(request, id):
    """Public health declaration form. Redirect to success if already submitted."""
    form_uuid = id
    existing = HealthDeclaration.objects.filter(pk=form_uuid).first()
    if existing and existing.is_submitted:
        return redirect("management:health_declaration_success")

    if request.method == "POST":
        sig = request.POST.get("signature_confirm") == "on"
        if not sig:
            medical_fields = [
                ("roaccutane", "שימוש בראוקוטן בשנה האחרונה"),
                ("active_peeling", "שימוש בתכשירים מקלפים פעילים"),
                ("prescription_creams", "תכשירים במרשם רופא"),
                ("past_acne", "אקנה בעבר"),
                ("skin_diseases", "מחלות עור"),
                ("regular_meds", "תרופות קבועות"),
                ("hormonal_contraceptives", "גלולות/התקן הורמונלי"),
                ("is_pregnant", "הריון/הנקה"),
                ("cosmetic_allergies", "אלרגיה לתכשירים"),
                ("numbing_sensitivity", "רגישות לאלחוש/עזרקאין"),
                ("metal_sensitivity", "רגישות למתכות - תכשיטים"),
                ("general_allergies", "אלרגיות למזון/חומרים אחרים"),
            ]
            return render(
                request,
                "management/health_form.html",
                {"form_uuid": form_uuid, "error": "יש לאשר את ההצהרה לפני השליחה.", "medical_fields": medical_fields},
            )

        def _bool(name):
            return request.POST.get(name) == "on"

        def _int(name, default=0):
            try:
                return int(request.POST.get(name) or default)
            except ValueError:
                return default

        data = {
            "full_name": (request.POST.get("full_name") or "").strip() or None,
            "phone_number": (request.POST.get("phone_number") or "").strip() or None,
            "age": _int("age") or None,
            "email": (request.POST.get("email") or "").strip() or None,
            "roaccutane": _bool("roaccutane"),
            "active_peeling": _bool("active_peeling"),
            "prescription_creams": _bool("prescription_creams"),
            "past_acne": _bool("past_acne"),
            "skin_diseases": _bool("skin_diseases"),
            "regular_meds": _bool("regular_meds"),
            "hormonal_contraceptives": _bool("hormonal_contraceptives"),
            "is_pregnant": _bool("is_pregnant"),
            "cosmetic_allergies": _bool("cosmetic_allergies"),
            "numbing_sensitivity": _bool("numbing_sensitivity"),
            "metal_sensitivity": _bool("metal_sensitivity"),
            "general_allergies": _bool("general_allergies"),
            "medical_notes": (request.POST.get("medical_notes") or "").strip(),
            "treatment_reactions": (request.POST.get("treatment_reactions") or "").strip(),
            "ip_address": _get_client_ip(request) or None,
            "is_submitted": True,
        }
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.save()
        else:
            HealthDeclaration.objects.create(id=form_uuid, **data)
        return redirect("management:health_declaration_success")

    medical_fields = [
        ("roaccutane", "שימוש בראוקוטן בשנה האחרונה"),
        ("active_peeling", "שימוש בתכשירים מקלפים פעילים"),
        ("prescription_creams", "תכשירים במרשם רופא"),
        ("past_acne", "אקנה בעבר"),
        ("skin_diseases", "מחלות עור"),
        ("regular_meds", "תרופות קבועות"),
        ("hormonal_contraceptives", "גלולות/התקן הורמונלי"),
        ("is_pregnant", "הריון/הנקה"),
        ("cosmetic_allergies", "אלרגיה לתכשירים"),
        ("numbing_sensitivity", "רגישות לאלחוש/עזרקאין"),
        ("metal_sensitivity", "רגישות למתכות - תכשיטים"),
        ("general_allergies", "אלרגיות למזון/חומרים אחרים"),
    ]
    return render(request, "management/health_form.html", {"form_uuid": form_uuid, "medical_fields": medical_fields})


def health_declaration_success(request):
    """Thank you page after successful submission."""
    return render(request, "management/health_success.html")
