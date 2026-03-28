# LingoSprint

Production-style Duolingo-like web application built with Flask, SQLite, server-rendered HTML templates, and browser-side JavaScript. It includes authentication, hierarchical course content, placement tests, adaptive difficulty, spaced repetition, XP/levels/streaks/leagues, achievements, coins, boosts, analytics, social friends and score comparisons, leaderboards, and simulated push/reminder notifications.

## Stack

- Backend: Flask with modular blueprints
- Frontend: HTML, CSS, vanilla JavaScript
- Database: SQLite with SQLAlchemy ORM and exported SQL schema
- Voice: Web Speech API for listening and speaking flows

## Project Structure

```text
.
├── app
│   ├── models
│   │   ├── __init__.py
│   │   └── core.py
│   ├── routes
│   │   ├── api.py
│   │   ├── auth.py
│   │   └── main.py
│   ├── services
│   │   ├── adaptive.py
│   │   ├── gamification.py
│   │   ├── notifications.py
│   │   ├── recommendations.py
│   │   ├── seed.py
│   │   └── social.py
│   ├── static
│   │   ├── css/style.css
│   │   └── js/{app.js,lesson.js}
│   ├── templates
│   │   ├── auth.html
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── index.html
│   │   ├── lesson.html
│   │   └── social.html
│   ├── utils/serializers.py
│   ├── __init__.py
│   └── extensions.py
├── config.py
├── requirements.txt
├── run.py
└── sql/schema.sql
```

## Implemented Features

- Authentication with signup, login, logout, password hashing, and session-based auth via `Flask-Login`
- Learning hierarchy: languages, courses, units, lessons, questions
- Placement-test flow with proficiency-based lesson placement
- Question types: multiple choice, fill blank, typing, listening, speaking
- Adaptive learning:
  - question reordering based on user accuracy
  - dynamic next-lesson selection
  - spaced repetition using review intervals and easiness factor
  - weak-topic detection and personalized lesson recommendations
- Gamification:
  - XP and level progression
  - daily streaks and streak freeze consumption
  - coins and auto-activated XP boosts
  - achievements/badges
  - weekly leaderboard
  - Bronze-to-Diamond-style league assignment
- Progress tracking and analytics dashboard
- Social system with friend requests, accepted friends, streak comparison, and leaderboard comparison
- Notifications system for daily reminders, streak alerts, and boost reminders, plus browser notification simulation
- Responsive dashboard and lesson UI with progress bars and correct/incorrect feedback animations

## Seeded Data

The app auto-creates and auto-seeds the database on first boot with:

- Languages: English, Spanish, French, German
- Courses: Spanish Sprint, French Voyage
- Multi-unit lesson trees with mixed question types
- Demo users and friend relationship

Demo login:

- Email: `demo@example.com`
- Password: `password123`

## Run Locally

1. Create a virtual environment:

```bash
python3 -m venv .venv
```

2. Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Start the app:

```bash
.venv/bin/python run.py
```

4. Open `http://127.0.0.1:5000`

The app calls `db.create_all()` and seeds initial content automatically when the database is empty.

## Optional Flask CLI

```bash
FLASK_APP=run.py .venv/bin/flask init-db
FLASK_APP=run.py .venv/bin/flask seed-db
```

## Notes

- Speaking and listening exercises use browser Web Speech APIs. Browser support varies; typed fallback remains available for speaking prompts.
- Notification delivery is simulated in-app and can also use browser notifications when permission is granted.
- The local environment used during implementation did not have network access for package download, so dependency installation must be run in an environment that can reach PyPI or already has those wheels available.
