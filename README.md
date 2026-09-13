# Smart Student Attendance Manager

A modern, browser-based attendance management web application built entirely in Python for university students. Track daily attendance by subject, monitor your percentage, and know exactly how many classes you need to attend — or can afford to miss.

---

## Features

| Feature | Description |
|---|---|
| 🔐 **Multi-user Auth** | Register/login with bcrypt-hashed passwords |
| 🏠 **Dashboard** | KPI cards, status badges, subject table, Plotly charts |
| 📚 **Subject Management** | Create semesters, add/edit/archive/delete subjects |
| 📝 **Mark Attendance** | Daily entry with Present / Absent / Medical Leave |
| 📅 **History** | Filterable, editable history table with CSV export |
| 📄 **PDF Report** | Download a full attendance report as a branded PDF |
| 📊 **Analytics** | Trend charts, monthly reports, subject breakdowns |
| 🧮 **What-If Calculator** | Project attendance for future scenarios |
| ⚙️ **Settings** | Profile, password change, demo data loader |
| 🎭 **Demo Data** | One-click demo semester with 6 subjects and 60 days of records |

---

## Screenshots

> _Add screenshots here after first run_

---

## Technology Stack

| Layer | Technology |
|---|---|
| UI Framework | Streamlit 1.32+ |
| Language | Python 3.10+ |
| Database (local) | SQLite (zero-config) |
| Database (cloud) | PostgreSQL via Supabase |
| Charts | Plotly |
| Data manipulation | Pandas |
| PDF generation | ReportLab |
| Auth | bcrypt |
| Testing | pytest |

---

## System Architecture

```
app.py (entry point / login gate)
    │
    ├── pages/ (Streamlit multi-page navigation)
    │       1_Dashboard.py
    │       2_Subjects.py
    │       3_Mark_Attendance.py
    │       4_Attendance_History.py
    │       5_Analytics.py
    │       6_What_If_Calculator.py
    │       7_Settings.py
    │
    ├── src/
    │       auth.py          ← bcrypt login/register/session
    │       calculations.py  ← pure attendance math
    │       validation.py    ← input validators
    │       services.py      ← combines DB + calculations
    │       analytics.py     ← Plotly chart builders
    │       export.py        ← CSV helpers
    │       models.py        ← all SQL CRUD
    │       database.py      ← connection factory + schema init
    │       sample_data.py   ← demo data seeder
    │       ui.py            ← shared UI helpers
    │
    └── tests/
            test_calculations.py  (49 tests)
            test_validation.py    (42 tests)
            test_database.py      (34 tests)
```

---

## Database Architecture

```sql
students     ─┐
              ├── semesters ─┐
              │              └── subjects ──── attendance
              └── (profile, threshold, auth)
```

Four tables. All foreign keys cascade on delete. Medical Leave is stored but excluded from percentage calculations.

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/<username>/smart-attendance-manager.git
cd smart-attendance-manager

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
streamlit run app.py
```

The SQLite database is created automatically at `database/attendance.db` on first launch.

---

## How to Use

1. **Register** a new account on the login page.
2. Go to **📚 Subjects** → create a semester → add your subjects.
3. Go to **📝 Mark Attendance** → select today → mark each class.
4. Return to **🏠 Dashboard** to see your statistics.
5. Use **📅 History** to review past records.
6. Use **🧮 What-If Calculator** to plan ahead.
7. Go to **⚙️ Settings → Demo Data** to load sample data instantly.

---

## Attendance Calculation

### Percentage
```
percentage = (present / (present + absent)) × 100
```
Medical Leave is excluded from both numerator and denominator.

### Classes Needed to Recover (when below threshold)
```
Find smallest x ≥ 0 such that:
    (present + x) / (present + absent + x) ≥ required / 100

x = ceil((required% × total − present) / (1 − required%))
```

### Classes You Can Still Miss (when above threshold)
```
Find largest y ≥ 0 such that:
    present / (present + absent + y) ≥ required / 100

y = floor(present / (required%) − total)
```

### Status Labels
| Percentage | Status |
|---|---|
| ≥ 85% | Excellent |
| ≥ 75% (threshold) | Safe |
| ≥ 65% | Warning |
| < 65% | Critical |

---

## Testing

```bash
pytest
```

**125 tests** across calculations, validation, and database CRUD. All tests use an isolated temporary database — no production data is affected.

---

## Deployment

### Option A: Streamlit Community Cloud (Recommended — Free)

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app.
3. Connect your GitHub repo. Set **Main file path** to `app.py`.
4. Configure secrets (see below).
5. Click **Deploy**. Every `git push` to `main` triggers auto-redeploy.

### Option B: Any Python Host

```bash
streamlit run app.py --server.port 8080
```

---

## Environment Variables / Secrets

### Local (`.streamlit/secrets.toml` — never commit this file)

```toml
# Leave empty to use local SQLite
DATABASE_URL = ""

# OR fill in Supabase PostgreSQL URL for local testing with persistent DB:
# DATABASE_URL = "postgresql://user:password@host:5432/dbname"
```

### Streamlit Community Cloud (App Settings → Secrets)

```toml
DATABASE_URL = "postgresql://user:password@host:5432/dbname"
```

### How to get the Supabase URL

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **Project Settings → Database → Connection String**
3. Copy the URI and replace `[YOUR-PASSWORD]` with your actual password

> If `DATABASE_URL` is not set, the app uses local SQLite automatically.

---

## Project Structure

```
smart-attendance-manager/
├── app.py                        # Entry point — login/register gate
├── requirements.txt
├── README.md
├── pyproject.toml                # pytest configuration
├── LICENSE
│
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Subjects.py
│   ├── 3_Mark_Attendance.py
│   ├── 4_Attendance_History.py
│   ├── 5_Analytics.py
│   ├── 6_What_If_Calculator.py
│   └── 7_Settings.py
│
├── src/
│   ├── __init__.py
│   ├── auth.py
│   ├── calculations.py
│   ├── validation.py
│   ├── services.py
│   ├── analytics.py
│   ├── export.py
│   ├── models.py
│   ├── database.py
│   ├── sample_data.py
│   └── ui.py
│
├── tests/
│   ├── __init__.py
│   ├── test_calculations.py
│   ├── test_validation.py
│   └── test_database.py
│
├── database/
│   └── .gitkeep                 # directory tracked; .db files ignored
│
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example     # template — copy to secrets.toml locally
```

---

## Future Improvements

- PDF report export
- Timetable import (upload a weekly schedule)
- Email/push reminders when attendance drops below threshold
- Admin/lecturer portal
- Dark mode toggle
- Bulk attendance import from CSV

---

## Author

Built as a Python university project.  
**Technology:** Python · Streamlit · SQLite/PostgreSQL · Plotly · pandas · bcrypt · pytest
