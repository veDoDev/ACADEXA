# ACADEXA — Intelligent Academic Management Platform

> AI-powered assignment management, plagiarism detection, and academic communication platform built with Django + Gemini AI.

---

## ⚡ Quick Setup (Run Tonight)

```bash
# 1. Clone / place project folder
cd acadexa

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run migrations
python manage.py makemigrations accounts
python manage.py makemigrations assignments
python manage.py makemigrations communications
python manage.py migrate

# 6. Seed demo data (for demo!)
python manage.py seed_demo

# 7. Run server
python manage.py runserver
```

Open http://127.0.0.1:8000

---

## 🔑 Demo Login Credentials

| Role    | Username     | Password   |
|---------|-------------|------------|
| Teacher | prof_sharma | demo1234   |
| Student | arjun_k     | demo1234   |
| Student | priya_m     | demo1234   |
| Student | rohan_s     | demo1234   |

---

## 🏗️ Project Structure

```
acadexa/
├── acadexa_project/        # Django project config
│   ├── settings.py
│   └── urls.py
├── apps/
│   ├── accounts/           # User auth, roles, dashboards
│   ├── assignments/        # Assignment CRUD + AI analysis
│   └── communications/     # Messaging system
├── templates/              # All HTML templates
│   ├── base/               # Base layout with sidebar
│   ├── accounts/           # Login, register, dashboards
│   ├── assignments/        # All assignment views
│   └── communications/     # Inbox, messages
├── static/
│   └── css/acadexa.css     # Full design system
├── requirements.txt
├── .env.example
└── manage.py
```

---

## ✅ Features Implemented (40% Demo)

### Authentication & Roles
- Custom User model with Student / Teacher roles
- Role-based dashboards (different views per role)
- Secure login, register, logout

### Assignment Management
- Teachers create assignments with deadline & marks
- Students browse available and submitted assignments
- File upload support: PDF, DOCX, TXT

### AI-Powered Analysis Pipeline
- **PDF/DOCX Text Extraction** via PyMuPDF
- **Gemini AI Reference Solution Generation** — auto-generates ideal answer
- **TF-IDF Cosine Similarity** plagiarism scoring vs AI reference
- **NLP Quality Score** based on word count, vocabulary richness, sentence structure
- **Gemini AI Feedback** — personalized, constructive comments
- Auto-flagging of submissions with >70% plagiarism

### Teacher Review
- Annotated submission list with color-coded plagiarism bars
- Full submission detail with all AI scores
- Manual review form: remarks, marks, status update
- Access to AI-generated reference solution

### Communication
- Inbox with read/unread tracking
- Keyword-based message flagging for inappropriate language
- Role-restricted messaging (students → teachers, teachers → students)

### 📅 Roadmap (Remaining 60%)
- [ ] OCR for handwritten PDF submissions (Tesseract)
- [ ] Highlighted plagiarism sections with source mapping
- [ ] Sentiment analysis on messages (Gemini)
- [ ] Learning analytics dashboard with charts
- [ ] Personalized feedback history per student
- [ ] Bulk submission export (CSV)
- [ ] Email notifications

---

## 🤖 AI Stack
- **Gemini 2.5 Flash** — solution generation, feedback
- **scikit-learn TF-IDF** — plagiarism detection
- **NLTK** — quality scoring and text analysis
- **PyMuPDF** — PDF text extraction

---

## 💡 Demo Script for Evaluators

1. Log in as **teacher** (`prof_sharma / demo1234`)
2. See dashboard with stats: 2 assignments, 4 submissions, 1 flagged
3. Click **All Submissions** → notice color-coded plagiarism bars
4. Open `priya_m`'s submission → 78% plagiarism, flagged status, AI feedback visible
5. Open `rohan_s`'s submission → 15.8% plagiarism, 81/100 quality, approved
6. Log in as **student** (`arjun_k / demo1234`)
7. Submit a new assignment → see live AI analysis results
8. Check inbox → view message from student to teacher
