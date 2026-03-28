from __future__ import annotations

from random import choice, randint

from sqlalchemy import inspect, text

from app.extensions import db
from app.models.core import (
    Achievement,
    Course,
    CourseEnrollment,
    Friendship,
    Language,
    Lesson,
    Question,
    Translation,
    TranslationGroup,
    Unit,
    User,
)


LANGUAGE_SEED = [
    {"code": "en", "name": "English"},
    {"code": "te", "name": "Telugu"},
    {"code": "hi", "name": "Hindi"},
]

ACHIEVEMENT_SEED = [
    {
        "key": "first_steps",
        "name": "First Steps",
        "description": "Complete your first lesson.",
        "icon": "shoe",
        "criteria_type": "lessons",
        "criteria_value": 1,
        "xp_reward": 30,
        "coins_reward": 10,
    },
    {
        "key": "streak_three",
        "name": "On Fire",
        "description": "Reach a 3 day streak.",
        "icon": "flame",
        "criteria_type": "streak",
        "criteria_value": 3,
        "xp_reward": 50,
        "coins_reward": 20,
    },
    {
        "key": "xp_500",
        "name": "Serious Learner",
        "description": "Earn 500 XP.",
        "icon": "bolt",
        "criteria_type": "xp",
        "criteria_value": 500,
        "xp_reward": 60,
        "coins_reward": 30,
    },
    {
        "key": "perfect_two",
        "name": "Precision",
        "description": "Ace 2 perfect lessons.",
        "icon": "target",
        "criteria_type": "perfect_lessons",
        "criteria_value": 2,
        "xp_reward": 75,
        "coins_reward": 25,
    },
    {
        "key": "social_one",
        "name": "Squad Up",
        "description": "Add your first friend.",
        "icon": "users",
        "criteria_type": "friends",
        "criteria_value": 1,
        "xp_reward": 40,
        "coins_reward": 15,
    },
]

TRANSLATION_SEED = [
    {
        "key": "greetings",
        "topic": "greetings",
        "entries": {
            "en": {"text": "hello", "example_sentence": "Hello, Maya"},
            "te": {"text": "నమస్కారం", "example_sentence": "నమస్కారం, మాయా"},
            "hi": {"text": "नमस्ते", "example_sentence": "नमस्ते, माया"},
        },
    },
    {
        "key": "basics",
        "topic": "basics",
        "entries": {
            "en": {"text": "water", "example_sentence": "I want water"},
            "te": {"text": "నీరు", "example_sentence": "నాకు నీరు కావాలి"},
            "hi": {"text": "पानी", "example_sentence": "मुझे पानी चाहिए"},
        },
    },
    {
        "key": "food",
        "topic": "food",
        "entries": {
            "en": {"text": "apple", "example_sentence": "The apple is red"},
            "te": {"text": "ఆపిల్", "example_sentence": "ఆపిల్ ఎర్రగా ఉంది"},
            "hi": {"text": "सेब", "example_sentence": "सेब लाल है"},
        },
    },
    {
        "key": "travel",
        "topic": "travel",
        "entries": {
            "en": {"text": "station", "example_sentence": "The station is here"},
            "te": {"text": "స్టేషన్", "example_sentence": "స్టేషన్ ఇక్కడ ఉంది"},
            "hi": {"text": "स्टेशन", "example_sentence": "स्टेशन यहाँ है"},
        },
    },
    {
        "key": "cafe",
        "topic": "cafe",
        "entries": {
            "en": {"text": "coffee", "example_sentence": "One coffee, please"},
            "te": {"text": "కాఫీ", "example_sentence": "ఒక కాఫీ, దయచేసి"},
            "hi": {"text": "कॉफी", "example_sentence": "एक कॉफी, कृपया"},
        },
    },
    {
        "key": "hotel",
        "topic": "hotel",
        "entries": {
            "en": {"text": "room", "example_sentence": "I need a room"},
            "te": {"text": "గది", "example_sentence": "నాకు ఒక గది కావాలి"},
            "hi": {"text": "कमरा", "example_sentence": "मुझे एक कमरा चाहिए"},
        },
    },
    {
        "key": "routine",
        "topic": "routine",
        "entries": {
            "en": {"text": "work", "example_sentence": "I work today"},
            "te": {"text": "పని", "example_sentence": "నేను ఈ రోజు పని చేస్తున్నాను"},
            "hi": {"text": "काम", "example_sentence": "मैं आज काम करता हूँ"},
        },
    },
    {
        "key": "past",
        "topic": "past",
        "entries": {
            "en": {"text": "market", "example_sentence": "I went to the market"},
            "te": {"text": "మార్కెట్", "example_sentence": "నేను మార్కెట్‌కు వెళ్లాను"},
            "hi": {"text": "बाज़ार", "example_sentence": "मैं बाज़ार गया"},
        },
    },
    {
        "key": "review",
        "topic": "review",
        "entries": {
            "en": {"text": "friend", "example_sentence": "My friend is here"},
            "te": {"text": "స్నేహితుడు", "example_sentence": "నా స్నేహితుడు ఇక్కడ ఉన్నాడు"},
            "hi": {"text": "दोस्त", "example_sentence": "मेरा दोस्त यहाँ है"},
        },
    },
]

UNIT_BLUEPRINTS = [
    {
        "title": "Foundations",
        "description": "Set up your base vocabulary and high-frequency phrases.",
        "lessons": [
            {
                "title": "Placement Check",
                "description": "Adaptive entrance test",
                "topic": "placement",
                "translation_key": "travel",
                "difficulty": 2,
                "xp_reward": 55,
                "is_placement": True,
            },
            {
                "title": "Greetings",
                "description": "Say hi and introduce yourself",
                "topic": "greetings",
                "translation_key": "greetings",
                "difficulty": 1,
                "xp_reward": 40,
                "is_placement": False,
            },
            {
                "title": "Basics",
                "description": "Core nouns and requests",
                "topic": "basics",
                "translation_key": "basics",
                "difficulty": 1,
                "xp_reward": 40,
                "is_placement": False,
            },
            {
                "title": "Food",
                "description": "Talk about simple meals",
                "topic": "food",
                "translation_key": "food",
                "difficulty": 2,
                "xp_reward": 45,
                "is_placement": False,
            },
        ],
    },
    {
        "title": "Everyday Survival",
        "description": "Get through stations, cafes, and hotels with confidence.",
        "lessons": [
            {
                "title": "Travel",
                "description": "Handle directions and transit",
                "topic": "travel",
                "translation_key": "travel",
                "difficulty": 2,
                "xp_reward": 45,
                "is_placement": False,
            },
            {
                "title": "Cafe",
                "description": "Order drinks politely",
                "topic": "cafe",
                "translation_key": "cafe",
                "difficulty": 3,
                "xp_reward": 50,
                "is_placement": False,
            },
            {
                "title": "Hotel",
                "description": "Check in and ask for help",
                "topic": "hotel",
                "translation_key": "hotel",
                "difficulty": 3,
                "xp_reward": 50,
                "is_placement": False,
            },
        ],
    },
    {
        "title": "Fluency Builder",
        "description": "Mix recall, listening, and spoken production.",
        "lessons": [
            {
                "title": "Routine",
                "description": "Talk about your day",
                "topic": "routine",
                "translation_key": "routine",
                "difficulty": 3,
                "xp_reward": 55,
                "is_placement": False,
            },
            {
                "title": "Past Tense",
                "description": "Describe recent events",
                "topic": "past",
                "translation_key": "past",
                "difficulty": 4,
                "xp_reward": 60,
                "is_placement": False,
            },
            {
                "title": "Review Arena",
                "description": "Mixed practice and recall",
                "topic": "review",
                "translation_key": "review",
                "difficulty": 4,
                "xp_reward": 65,
                "is_placement": False,
            },
        ],
    },
]

QUESTION_TEMPLATE_TYPES = [
    "multiple_choice",
    "fill_blank",
    "typing",
    "listening",
    "speaking",
]


def seed_database() -> None:
    db.create_all()
    ensure_schema_support()

    languages = seed_languages()
    seed_achievements()
    translation_groups = seed_translation_catalog(languages)
    course_lookup = seed_courses(languages, translation_groups)
    demo_users = seed_demo_users(languages, course_lookup)
    seed_friendships(demo_users)
    db.session.commit()


def ensure_schema_support() -> None:
    inspector = inspect(db.engine)
    question_columns = {column["name"] for column in inspector.get_columns("questions")}
    if "translation_group_id" not in question_columns:
        db.session.execute(text("ALTER TABLE questions ADD COLUMN translation_group_id INTEGER"))
        db.session.commit()


def seed_languages() -> dict[str, Language]:
    languages: dict[str, Language] = {}
    for spec in LANGUAGE_SEED:
        language = Language.query.filter_by(code=spec["code"]).first()
        if not language:
            language = Language(code=spec["code"], name=spec["name"])
            db.session.add(language)
        else:
            language.name = spec["name"]
        languages[spec["code"]] = language
    db.session.flush()
    return languages


def seed_achievements() -> None:
    for spec in ACHIEVEMENT_SEED:
        achievement = Achievement.query.filter_by(key=spec["key"]).first()
        if not achievement:
            achievement = Achievement(key=spec["key"], **{k: v for k, v in spec.items() if k != "key"})
            db.session.add(achievement)
            continue
        for key, value in spec.items():
            setattr(achievement, key, value)
    db.session.flush()


def seed_translation_catalog(
    languages: dict[str, Language],
) -> dict[str, TranslationGroup]:
    groups: dict[str, TranslationGroup] = {}
    for spec in TRANSLATION_SEED:
        group = TranslationGroup.query.filter_by(key=spec["key"]).first()
        if not group:
            group = TranslationGroup(key=spec["key"], topic=spec["topic"])
            db.session.add(group)
            db.session.flush()
        else:
            group.topic = spec["topic"]
        groups[spec["key"]] = group

        for language_code, entry in spec["entries"].items():
            translation = Translation.query.filter_by(
                translation_group_id=group.id,
                language_id=languages[language_code].id,
            ).first()
            if not translation:
                translation = Translation(
                    translation_group_id=group.id,
                    language_id=languages[language_code].id,
                )
                db.session.add(translation)
            translation.text = entry["text"]
            translation.example_sentence = entry.get("example_sentence")
            translation.alternate_texts = entry.get("alternate_texts", [])

    db.session.flush()
    return groups


def seed_courses(
    languages: dict[str, Language],
    translation_groups: dict[str, TranslationGroup],
) -> dict[str, Course]:
    required_keys = [lesson["translation_key"] for unit in UNIT_BLUEPRINTS for lesson in unit["lessons"]]
    supported_languages = [
        language
        for language in languages.values()
        if language_supports_all_translation_keys(language, required_keys)
    ]
    accent_palette = ["#58cc02", "#1cb0f6", "#ff9600", "#ff4b4b", "#ce82ff", "#00b894"]
    course_lookup: dict[str, Course] = {}

    pair_index = 0
    for source in sorted(supported_languages, key=lambda item: item.name):
        for target in sorted(supported_languages, key=lambda item: item.name):
            if source.id == target.id:
                continue
            course = Course.query.filter_by(
                source_language_id=source.id,
                target_language_id=target.id,
            ).first()
            if not course:
                course = Course(
                    title=f"{source.name} to {target.name}",
                    description=(
                        f"Practice everyday vocabulary by translating from {source.name} to {target.name}."
                    ),
                    source_language_id=source.id,
                    target_language_id=target.id,
                    accent_color=accent_palette[pair_index % len(accent_palette)],
                )
                db.session.add(course)

            course.title = f"{source.name} to {target.name}"
            course.description = (
                f"Practice everyday vocabulary by translating from {source.name} to {target.name}."
            )
            course.accent_color = accent_palette[pair_index % len(accent_palette)]
            course_lookup[course.title] = course
            pair_index += 1

            db.session.flush()
            seed_units_and_lessons(course, translation_groups)

    db.session.flush()
    return course_lookup


def language_supports_all_translation_keys(language: Language, required_keys: list[str]) -> bool:
    available_keys = {
        row.key
        for row in (
            db.session.query(TranslationGroup.key)
            .join(Translation, Translation.translation_group_id == TranslationGroup.id)
            .filter(Translation.language_id == language.id)
            .all()
        )
    }
    return set(required_keys).issubset(available_keys)


def seed_units_and_lessons(
    course: Course,
    translation_groups: dict[str, TranslationGroup],
) -> None:
    for unit_index, unit_spec in enumerate(UNIT_BLUEPRINTS, start=1):
        unit = Unit.query.filter_by(course_id=course.id, position=unit_index).first()
        if not unit:
            unit = Unit(
                course_id=course.id,
                title=unit_spec["title"],
                description=unit_spec["description"],
                position=unit_index,
            )
            db.session.add(unit)
        unit.title = unit_spec["title"]
        unit.description = unit_spec["description"]
        db.session.flush()

        for lesson_index, lesson_spec in enumerate(unit_spec["lessons"], start=1):
            lesson = Lesson.query.filter_by(unit_id=unit.id, position=lesson_index).first()
            if not lesson:
                lesson = Lesson(
                    unit_id=unit.id,
                    title=lesson_spec["title"],
                    description=lesson_spec["description"],
                    topic=lesson_spec["topic"],
                    position=lesson_index,
                    difficulty=lesson_spec["difficulty"],
                    xp_reward=lesson_spec["xp_reward"],
                    is_placement=lesson_spec["is_placement"],
                )
                db.session.add(lesson)

            lesson.title = lesson_spec["title"]
            lesson.description = lesson_spec["description"]
            lesson.topic = lesson_spec["topic"]
            lesson.difficulty = lesson_spec["difficulty"]
            lesson.xp_reward = lesson_spec["xp_reward"]
            lesson.is_placement = lesson_spec["is_placement"]
            db.session.flush()

            translation_group = translation_groups[lesson_spec["translation_key"]]
            seed_question_templates(lesson, translation_group)


def seed_question_templates(lesson: Lesson, translation_group: TranslationGroup) -> None:
    for question_type in QUESTION_TEMPLATE_TYPES:
        question = Question.query.filter_by(lesson_id=lesson.id, question_type=question_type).first()
        if not question:
            question = Question(
                lesson_id=lesson.id,
                question_type=question_type,
                prompt=question_type,
                correct_answer=translation_group.key,
                difficulty=lesson.difficulty,
                topic=lesson.topic,
            )
            db.session.add(question)

        question.translation_group_id = translation_group.id
        question.prompt = question_type
        question.choices = []
        question.correct_answer = translation_group.key
        question.acceptable_answers = []
        question.hint = None
        question.explanation = None
        question.difficulty = lesson.difficulty + (1 if question_type in {"typing", "listening", "speaking"} else 0)
        question.topic = lesson.topic
        question.audio_text = None
        question.speaking_text = None

    db.session.flush()


def seed_demo_users(
    languages: dict[str, Language],
    course_lookup: dict[str, Course],
) -> list[User]:
    user_specs = [
        ("demo", "demo@example.com", "password123", "en", "English to Telugu"),
        ("coach", "coach@example.com", "password123", "en", "English to Hindi"),
        ("polyglot", "polyglot@example.com", "password123", "te", "Telugu to English"),
    ]
    users: list[User] = []

    for username, email, password, native_code, course_title in user_specs:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=username,
                email=email,
                native_language_id=languages[native_code].id,
                xp=randint(120, 980),
                coins=randint(70, 260),
                daily_streak=randint(1, 12),
                longest_streak=randint(4, 20),
                streak_freezes=randint(1, 3),
                avatar_color=choice(["#58cc02", "#1cb0f6", "#ff9600", "#ff4b4b"]),
            )
            user.set_password(password)
            user.recompute_level()
            db.session.add(user)
            db.session.flush()
        else:
            user.native_language_id = user.native_language_id or languages[native_code].id

        course = course_lookup.get(course_title)
        if course:
            user.active_course_id = course.id
            ensure_enrollment(user, course)
        users.append(user)

    db.session.flush()
    return users


def ensure_enrollment(user: User, course: Course) -> None:
    enrollment = CourseEnrollment.query.filter_by(user_id=user.id, course_id=course.id).first()
    first_unit = course.units[0] if course.units else None
    first_lesson = next((lesson for lesson in first_unit.lessons if not lesson.is_placement), None) if first_unit else None
    if not enrollment:
        enrollment = CourseEnrollment(
            user_id=user.id,
            course_id=course.id,
            current_unit_id=first_unit.id if first_unit else None,
            current_lesson_id=first_lesson.id if first_lesson else None,
            proficiency_score=0.35,
            placement_level=1,
        )
        db.session.add(enrollment)
        return

    enrollment.current_unit_id = enrollment.current_unit_id or (first_unit.id if first_unit else None)
    enrollment.current_lesson_id = enrollment.current_lesson_id or (first_lesson.id if first_lesson else None)


def seed_friendships(users: list[User]) -> None:
    if len(users) < 2:
        return
    friendship = Friendship.query.filter_by(
        requester_id=users[0].id,
        addressee_id=users[1].id,
    ).first()
    if not friendship:
        db.session.add(
            Friendship(
                requester_id=users[0].id,
                addressee_id=users[1].id,
                status="accepted",
            )
        )
