PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(8) NOT NULL UNIQUE,
    name VARCHAR(80) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS translation_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(80) NOT NULL UNIQUE,
    topic VARCHAR(80) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_group_id INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    text VARCHAR(255) NOT NULL,
    alternate_texts TEXT,
    example_sentence TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (translation_group_id, language_id),
    FOREIGN KEY (translation_group_id) REFERENCES translation_groups (id),
    FOREIGN KEY (language_id) REFERENCES languages (id)
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    source_language_id INTEGER NOT NULL,
    target_language_id INTEGER NOT NULL,
    cefr_level VARCHAR(10) NOT NULL DEFAULT 'A1',
    accent_color VARCHAR(20) NOT NULL DEFAULT '#58cc02',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (source_language_id) REFERENCES languages (id),
    FOREIGN KEY (target_language_id) REFERENCES languages (id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(40) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    native_language_id INTEGER,
    active_course_id INTEGER,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    coins INTEGER NOT NULL DEFAULT 50,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    streak_freezes INTEGER NOT NULL DEFAULT 2,
    last_active_date DATE,
    xp_boost_multiplier FLOAT NOT NULL DEFAULT 1.0,
    xp_boost_until DATETIME,
    avatar_color VARCHAR(20) NOT NULL DEFAULT '#78c800',
    preferred_reminder_time VARCHAR(5) NOT NULL DEFAULT '19:00',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (native_language_id) REFERENCES languages (id),
    FOREIGN KEY (active_course_id) REFERENCES courses (id)
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    title VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL,
    title VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    topic VARCHAR(80) NOT NULL,
    position INTEGER NOT NULL,
    difficulty INTEGER NOT NULL DEFAULT 1,
    xp_reward INTEGER NOT NULL DEFAULT 40,
    is_placement BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (unit_id) REFERENCES units (id)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    translation_group_id INTEGER,
    prompt TEXT NOT NULL,
    question_type VARCHAR(40) NOT NULL,
    choices TEXT,
    correct_answer VARCHAR(255) NOT NULL,
    acceptable_answers TEXT,
    hint VARCHAR(255),
    explanation TEXT,
    difficulty INTEGER NOT NULL DEFAULT 1,
    topic VARCHAR(80) NOT NULL,
    audio_text TEXT,
    speaking_text TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (lesson_id) REFERENCES lessons (id),
    FOREIGN KEY (translation_group_id) REFERENCES translation_groups (id)
);

CREATE TABLE IF NOT EXISTS course_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    current_unit_id INTEGER,
    current_lesson_id INTEGER,
    proficiency_score FLOAT NOT NULL DEFAULT 0.0,
    placement_level INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (user_id, course_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (course_id) REFERENCES courses (id),
    FOREIGN KEY (current_unit_id) REFERENCES units (id),
    FOREIGN KEY (current_lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'not_started',
    attempts_count INTEGER NOT NULL DEFAULT 0,
    accuracy FLOAT NOT NULL DEFAULT 0.0,
    best_score FLOAT NOT NULL DEFAULT 0.0,
    last_score FLOAT NOT NULL DEFAULT 0.0,
    completed_at DATETIME,
    mastery_level FLOAT NOT NULL DEFAULT 0.0,
    next_review_at DATETIME,
    easiness_factor FLOAT NOT NULL DEFAULT 2.5,
    review_interval_days INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (user_id, lesson_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS question_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    user_answer TEXT,
    is_correct BOOLEAN NOT NULL,
    response_time_ms INTEGER,
    difficulty_snapshot INTEGER NOT NULL,
    xp_awarded INTEGER NOT NULL DEFAULT 0,
    answered_on DATE NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (lesson_id) REFERENCES lessons (id),
    FOREIGN KEY (question_id) REFERENCES questions (id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(40) NOT NULL DEFAULT 'star',
    criteria_type VARCHAR(40) NOT NULL,
    criteria_value INTEGER NOT NULL,
    xp_reward INTEGER NOT NULL DEFAULT 0,
    coins_reward INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    earned_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (achievement_id) REFERENCES achievements (id)
);

CREATE TABLE IF NOT EXISTS friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL,
    addressee_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    accepted_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (requester_id, addressee_id),
    FOREIGN KEY (requester_id) REFERENCES users (id),
    FOREIGN KEY (addressee_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_type VARCHAR(40) NOT NULL,
    title VARCHAR(120) NOT NULL,
    message TEXT NOT NULL,
    scheduled_for DATETIME NOT NULL,
    sent_at DATETIME,
    read_at DATETIME,
    payload TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lesson_id INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    score FLOAT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start DATE NOT NULL,
    xp_earned INTEGER NOT NULL DEFAULT 0,
    rank INTEGER NOT NULL DEFAULT 0,
    league_name VARCHAR(40) NOT NULL DEFAULT 'Bronze',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (user_id, week_start),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_leaderboard_week_start ON leaderboard_entries (week_start);

CREATE TABLE IF NOT EXISTS user_league_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    league_name VARCHAR(40) NOT NULL,
    finish_rank INTEGER NOT NULL,
    xp_earned INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
