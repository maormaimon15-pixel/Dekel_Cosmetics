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
        on_delete=models.SET_NULL,
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