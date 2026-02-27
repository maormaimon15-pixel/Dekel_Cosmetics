import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


class Client(models.Model):
    name = models.CharField(max_length=100, verbose_name="שם מלא")
    age = models.PositiveIntegerField(blank=True, null=True, verbose_name="גיל")
    birth_date = models.DateField(blank=True, null=True, verbose_name="תאריך לידה")
    phone = models.CharField(max_length=15, verbose_name="טלפון")
    email = models.EmailField(blank=True, null=True, verbose_name="אימייל")
    notes = models.TextField(blank=True, verbose_name="העדפות / הערות")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="נוצרה בתאריך")

    class Meta:
        verbose_name = "לקוחה"
        verbose_name_plural = "לקוחות"

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = "".join(filter(str.isdigit, self.phone))
        super().save(*args, **kwargs)
        try:
            self.health_declaration
        except HealthDeclaration.DoesNotExist:
            HealthDeclaration.objects.create(client=self, is_submitted=False)

    def get_wa_phone(self):
        """Return phone formatted for WhatsApp (972XXXXXXXXX)."""
        digits = "".join(filter(str.isdigit, self.phone or ""))
        if not digits:
            return ""
        if digits.startswith("972"):
            return digits
        if digits.startswith("0"):
            return "972" + digits[1:]
        return "972" + digits

    def __str__(self):
        return self.name


class Appointment(models.Model):
    SERVICE_FACE = "face"
    SERVICE_BROWS = "brows"
    SERVICE_GEL = "gel"

    SERVICE_CHOICES = [
        (SERVICE_FACE, "טיפול פנים"),
        (SERVICE_BROWS, "עיצוב גבות"),
        (SERVICE_GEL, "לק ג'ל"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="לקוחה",
    )
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_CHOICES,
        verbose_name="סוג טיפול",
    )
    custom_price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        verbose_name="מחיר לטיפול",
    )
    start_time = models.DateTimeField(verbose_name="זמן התחלה")
    duration_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name="משך (בדקות)",
    )
    notes = models.TextField(blank=True, verbose_name="הערות")
    is_completed = models.BooleanField(default=False, verbose_name="בוצע?")

    class Meta:
        verbose_name = "תור"
        verbose_name_plural = "תורים"
        ordering = ["-start_time"]

    @property
    def current_status(self):
        """Returns 'הושלם', 'בטיפול', or 'מתוכנן' based on current time."""
        if self.is_completed:
            return "הושלם"
        now = timezone.now()
        end_time = self.start_time + timedelta(minutes=self.duration_minutes)
        if self.start_time <= now <= end_time:
            return "בטיפול"
        return "מתוכנן"

    def __str__(self):
        return f"{self.client.name} - {self.get_service_type_display()} ({self.start_time.strftime('%d/%m %H:%M')})"


class FinanceRecord(models.Model):
    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"

    TYPE_CHOICES = [
        (TYPE_INCOME, "הכנסה"),
        (TYPE_EXPENSE, "הוצאה"),
    ]

    record_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="סוג תנועה",
    )
    date = models.DateField(verbose_name="תאריך")
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="סכום")
    category = models.CharField(max_length=100, verbose_name="קטגוריה")
    description = models.TextField(blank=True, verbose_name="תיאור")
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="finance_records",
        verbose_name="תור קשור",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="נוצר בתאריך")

    class Meta:
        verbose_name = "רישום כספי"
        verbose_name_plural = "רישומים כספיים"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_record_type_display()} - {self.amount} ₪ ({self.date})"


class PersonalEvent(models.Model):
    title = models.CharField(max_length=120, verbose_name="כותרת אירוע")
    start_time = models.DateTimeField(verbose_name="זמן התחלה")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="זמן סיום")
    notes = models.TextField(blank=True, verbose_name="הערות")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="נוצר בתאריך")

    class Meta:
        verbose_name = "אירוע אישי"
        verbose_name_plural = "אירועים אישיים"
        ordering = ["-start_time"]

    def __str__(self):
        return self.title


class HealthDeclaration(models.Model):
    """הצהרת בריאות ופרטים אישיים – דקל קוסמטיקס"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(
        "Client",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="health_declaration",
        verbose_name="לקוחה",
    )
    is_submitted = models.BooleanField(default=False, verbose_name="הוגשה")

    # Identity – פרטים אישיים
    full_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="שם מלא")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="טלפון")
    age = models.PositiveIntegerField(blank=True, null=True, verbose_name="גיל")
    email = models.EmailField(blank=True, null=True, verbose_name="אימייל - אופציונלי")

    # Critical Medical – שאלון רפואי קריטי
    roaccutane = models.BooleanField(default=False, verbose_name="שימוש בראוקוטן בשנה האחרונה")
    active_peeling = models.BooleanField(default=False, verbose_name="שימוש בתכשירים מקלפים פעילים")
    prescription_creams = models.BooleanField(default=False, verbose_name="תכשירים במרשם רופא")

    # Health History – היסטוריה רפואית
    past_acne = models.BooleanField(default=False, verbose_name="אקנה בעבר")
    skin_diseases = models.BooleanField(default=False, verbose_name="מחלות עור")
    regular_meds = models.BooleanField(default=False, verbose_name="תרופות קבועות")
    hormonal_contraceptives = models.BooleanField(default=False, verbose_name="גלולות/התקן הורמונלי")
    is_pregnant = models.BooleanField(default=False, verbose_name="הריון/הנקה")

    # Sensitivities – רגישויות
    cosmetic_allergies = models.BooleanField(default=False, verbose_name="אלרגיה לתכשירים")
    numbing_sensitivity = models.BooleanField(default=False, verbose_name="רגישות לאלחוש/עזרקאין")
    metal_sensitivity = models.BooleanField(default=False, verbose_name="רגישות למתכות - תכשיטים")
    general_allergies = models.BooleanField(default=False, verbose_name="אלרגיות למזון/חומרים אחרים")

    # Detailed Info – פירוט נוסף
    medical_notes = models.TextField(blank=True, verbose_name="פירוט נוסף")
    treatment_reactions = models.TextField(blank=True, verbose_name="תגובות חריפות לטיפולים בעבר")

    # Metadata – תיעוד
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="תאריך מילוי")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="כתובת IP לצרכי תיעוד")

    class Meta:
        verbose_name = "הצהרת בריאות"
        verbose_name_plural = "הצהרות בריאות"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} – {self.created_at.strftime('%d/%m/%Y')}"