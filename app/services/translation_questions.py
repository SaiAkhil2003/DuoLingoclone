from __future__ import annotations

from app.models.core import Course, Question, Translation, TranslationGroup


def _translation_for_language(
    translation_group: TranslationGroup | None, language_id: int
) -> Translation | None:
    if not translation_group:
        return None
    return next(
        (item for item in translation_group.translations if item.language_id == language_id),
        None,
    )


def _distinct_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join(value.strip().lower().split())
        if not value or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def _blanked_sentence(sentence: str, answer: str) -> str:
    if not sentence or not answer:
        return sentence
    if answer in sentence:
        return sentence.replace(answer, "____", 1)
    return f"____ {sentence}"


def _build_choice_list(question: Question, course: Course, answer: str) -> list[str]:
    if not question.translation_group_id or not answer:
        return question.choices or []

    distractor_rows = (
        Translation.query.filter(
            Translation.language_id == course.target_language_id,
            Translation.translation_group_id != question.translation_group_id,
        )
        .order_by(Translation.text.asc())
        .all()
    )
    distractors = _distinct_texts([row.text for row in distractor_rows if row.text])
    start = question.id % len(distractors) if distractors else 0
    selected = [answer]
    for index in range(len(distractors)):
        candidate = distractors[(start + index) % len(distractors)]
        if candidate == answer:
            continue
        selected.append(candidate)
        if len(selected) == 4:
            break

    shift = question.id % len(selected) if selected else 0
    return selected[shift:] + selected[:shift]


def _legacy_payload(question: Question) -> dict:
    return {
        "prompt": question.prompt,
        "choices": question.choices or [],
        "hint": question.hint,
        "explanation": question.explanation,
        "audioText": question.audio_text,
        "speakingText": question.speaking_text,
        "acceptedAnswers": question.acceptable_answers or [question.correct_answer],
        "correctAnswer": question.correct_answer,
    }


def build_question_payload(question: Question) -> dict:
    course = question.lesson.unit.course
    source_language = course.source_language
    target_language = course.target_language
    source = _translation_for_language(question.translation_group, course.source_language_id)
    target = _translation_for_language(question.translation_group, course.target_language_id)

    if not source or not target:
        return _legacy_payload(question)

    target_answers = _distinct_texts([target.text, *(target.alternate_texts or [])])
    target_sentence = target.example_sentence or target.text
    source_sentence = source.example_sentence or source.text

    base = {
        "hint": question.hint,
        "explanation": (
            f"{source.text} in {source_language.name} becomes {target.text} in {target_language.name}."
        ),
        "audioText": None,
        "speakingText": None,
        "acceptedAnswers": target_answers,
        "correctAnswer": target.text,
        "choices": [],
    }

    if question.question_type == "multiple_choice":
        base["prompt"] = (
            f'Translate from {source_language.name} to {target_language.name}: "{source.text}".'
        )
        base["hint"] = question.hint or f"Choose the answer written in {target_language.name}."
        base["choices"] = _build_choice_list(question, course, target.text)
        return base

    if question.question_type == "fill_blank":
        base["prompt"] = (
            f'Translate from {source_language.name} to {target_language.name} and complete: '
            f'"{_blanked_sentence(target_sentence, target.text)}"'
        )
        base["hint"] = question.hint or f'Source clue: "{source_sentence}"'
        base["acceptedAnswers"] = target_answers
        base["correctAnswer"] = target.text
        return base

    if question.question_type == "typing":
        base["prompt"] = (
            f'Translate from {source_language.name} to {target_language.name}: "{source_sentence}"'
        )
        base["hint"] = question.hint or f"Type the full answer in {target_language.name}."
        base["acceptedAnswers"] = _distinct_texts([target_sentence])
        base["correctAnswer"] = target_sentence
        base["explanation"] = f'A natural translation is "{target_sentence}".'
        return base

    if question.question_type == "listening":
        base["prompt"] = (
            f"Translate from {source_language.name} to {target_language.name}. Listen and type the phrase."
        )
        base["hint"] = question.hint or f'Source clue: "{source_sentence}"'
        base["audioText"] = target_sentence
        base["acceptedAnswers"] = _distinct_texts([target_sentence])
        base["correctAnswer"] = target_sentence
        base["explanation"] = f'The spoken phrase is "{target_sentence}".'
        return base

    if question.question_type == "speaking":
        base["prompt"] = (
            f"Translate from {source_language.name} to {target_language.name} and say it aloud."
        )
        base["hint"] = question.hint or f'Source clue: "{source_sentence}"'
        base["speakingText"] = target_sentence
        base["acceptedAnswers"] = _distinct_texts([target_sentence])
        base["correctAnswer"] = target_sentence
        base["explanation"] = f'A correct spoken answer is "{target_sentence}".'
        return base

    base["prompt"] = question.prompt
    return base


def accepted_answers_for_question(question: Question) -> list[str]:
    payload = build_question_payload(question)
    return payload["acceptedAnswers"]


def explanation_for_question(question: Question) -> str | None:
    payload = build_question_payload(question)
    return payload["explanation"]
