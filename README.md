## Dekel Cosmetics - מערכת ניהול סטודיו

מערכת ניהול תורים, לקוחות וכספים עבור Dekel Cosmetics, מבוססת Django, עם תמיכה מלאה בעברית ו‑RTL.

### דרישות

- Python 3.11+ (מומלץ)
- וירטואל־סביבה (venv) פעילה

### התקנת חבילות

מהתיקייה `Dekel_Cosmetics`:

```bash
pip install -r requirements.txt
```

### מיגרציות והפעלת השרת

```bash
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py createsuperuser  # יצירת משתמש אדמין
venv\Scripts\python.exe manage.py runserver
```

לאחר ההפעלה:

- ממשק הניהול: `http://localhost:8000/admin/` (ממשק בעברית, כולל לקוחות, תורים ורישומים כספיים)
- לוח הניהול הראשי: `http://localhost:8000/`

### מבנה לוגי עיקרי

- `appointments/models.py` – מודלים:
  - `Client` – לקוחות והעדפות.
  - `Appointment` – תורים (עם סוג טיפול קבוע ומחיר ידני לכל תור).
  - `FinanceRecord` – הכנסות/הוצאות, מקושרות לתורים (אופציונלי).
- `management/` – אפליקציית הניהול:
  - `views.py` – דשבורד, תורים, לקוחות, דוח כספי, ודף "דקל‑בוט".
  - `templates/management/*.html` – תבניות Django בעברית עם Tailwind ו‑RTL.
- `templates/base.html` – לייאאוט ראשי עם ניווט, RTL, ו"חלק צור קשר" קבוע בתחתית.

### תצוגות מרכזיות

- לוח ראשי – תורים קרובים + סיכום הכנסות.
- תורים – רשימת תורים לפי תאריך ויצירת תור חדש (עם מחיר ידני).
- לקוחות – רשימת לקוחות + היסטוריית טיפולים לכל לקוחה.
- כספים – דוח הכנסות/הוצאות יומי, שבועי, חודשי ורבעוני.
- דקל‑בוט – שדה צ'אט צדדי לשאלות כמו:
  - "מתי דנה הייתה פה פעם אחרונה?"
  - "כמה הרווחתי בינואר?"

