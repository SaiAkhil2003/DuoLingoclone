console.log("Lesson JS loaded");

const ANSWER_OPTION_SELECTOR = ".answer-option";

let lessonState = {
  lesson: null,
  questions: [],
  currentIndex: 0,
  answers: [],
  checking: false,
  questionStartedAt: Date.now(),
  selectedChoice: null,
};

function $(id) {
  return document.getElementById(id);
}

function currentQuestion() {
  return lessonState.questions[lessonState.currentIndex];
}

function currentAnswerEntry() {
  return lessonState.answers.find((item) => item.questionId === currentQuestion().id);
}

function renderLessonHeader() {
  const header = $("lesson-header");
  const progress = ((lessonState.currentIndex + 1) / lessonState.questions.length) * 100;
  header.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">${lessonState.lesson.courseTitle} • ${lessonState.lesson.unitTitle}</p>
        <h1>${lessonState.lesson.title}</h1>
        <p class="lede">${lessonState.lesson.description}</p>
        <p class="muted">${lessonState.lesson.translationDirection}</p>
      </div>
      <div class="lesson-meta">
        <span class="badge">${lessonState.lesson.topic}</span>
        <span class="badge">Difficulty ${lessonState.lesson.difficulty}</span>
        <span class="badge">${lessonState.lesson.xpReward} XP</span>
      </div>
    </div>
    <div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div>
  `;
}

function speechRecognitionSupported() {
  return "webkitSpeechRecognition" in window || "SpeechRecognition" in window;
}

function speakText(text) {
  if (!("speechSynthesis" in window)) {
    showToast("Speech synthesis is not available in this browser.", "error");
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.lang = lessonState.lesson?.targetLanguageCode || "en";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function startSpeechCapture(input) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    showToast("Speech recognition is not available. Type your answer instead.", "error");
    return;
  }
  const recognition = new Recognition();
  recognition.lang = lessonState.lesson?.targetLanguageCode || "en";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onresult = (event) => {
    input.value = event.results[0][0].transcript;
  };
  recognition.onerror = () => {
    showToast("Speech capture failed. Try again or type manually.", "error");
  };
  recognition.start();
}

function answerInputMarkup(question) {
  switch (question.questionType) {
    case "multiple_choice":
      return `
        <div class="choice-grid">
          ${question.choices
            .map(
              (choice) => `
                <button class="choice-button answer-option ${lessonState.selectedChoice === choice ? "selected" : ""}" data-choice="${choice}" type="button">${choice}</button>
              `
            )
            .join("")}
        </div>
      `;
    case "fill_blank":
    case "typing":
    case "listening":
    case "speaking":
      return `
        ${question.questionType === "listening" ? '<button id="play-audio" class="button-secondary" type="button">Play audio</button>' : ""}
        ${question.questionType === "speaking" ? `<button id="capture-speech" class="button-secondary" type="button">${speechRecognitionSupported() ? "Record speech" : "Speech unsupported"}</button>` : ""}
        <textarea id="answer-input" rows="3" placeholder="Type your answer here"></textarea>
      `;
    default:
      return `<textarea id="answer-input" rows="3"></textarea>`;
  }
}

function selectedAnswerValue() {
  const question = currentQuestion();
  if (question.questionType === "multiple_choice") {
    return lessonState.selectedChoice || $("lesson-runner")?.querySelector(`${ANSWER_OPTION_SELECTOR}.selected`)?.dataset.choice || "";
  }
  return document.getElementById("answer-input")?.value?.trim() || "";
}

function setSelectedChoice(choice, node = $("lesson-runner")) {
  lessonState.selectedChoice = choice;
  node?.querySelectorAll(ANSWER_OPTION_SELECTOR).forEach((button) => {
    button.classList.toggle("selected", button.dataset.choice === choice);
  });
}

function renderQuestion() {
  renderLessonHeader();
  const question = currentQuestion();
  const saved = currentAnswerEntry();
  const node = $("lesson-runner");
  lessonState.selectedChoice = question.questionType === "multiple_choice" ? saved?.answer ?? null : null;
  node.innerHTML = `
    <div class="lesson-question">
      <p class="eyebrow">Question ${lessonState.currentIndex + 1} of ${lessonState.questions.length}</p>
      <p class="muted">${lessonState.lesson.translationDirection}</p>
      <h2>${question.prompt}</h2>
      ${question.hint ? `<p class="muted">Hint: ${question.hint}</p>` : ""}
      ${question.questionType === "speaking" && question.speakingText ? `<p><strong>Say:</strong> ${question.speakingText}</p>` : ""}
      ${answerInputMarkup(question)}
      <div id="feedback-slot"></div>
      <div class="inline-actions">
        <button id="check-answer" class="button-primary" type="button">${saved?.checked ? (lessonState.currentIndex === lessonState.questions.length - 1 ? "Finish lesson" : "Next question") : "Check"}</button>
      </div>
    </div>
  `;

  if (saved?.checked) {
    renderFeedback(saved.correct, saved.feedback);
    const input = document.getElementById("answer-input");
    if (input) input.value = saved.answer;
  }

  node.querySelectorAll(ANSWER_OPTION_SELECTOR).forEach((button) => {
    button.addEventListener("click", () => {
      setSelectedChoice(button.dataset.choice, node);
    });
  });

  document.getElementById("play-audio")?.addEventListener("click", () => speakText(question.audioText || question.prompt));
  document.getElementById("capture-speech")?.addEventListener("click", () => {
    const input = document.getElementById("answer-input");
    if (input) startSpeechCapture(input);
  });
  document.getElementById("check-answer")?.addEventListener("click", handleCheckOrAdvance);

  if (saved?.answer && document.getElementById("answer-input")) {
    document.getElementById("answer-input").value = saved.answer;
  }
}

function renderFeedback(correct, feedback) {
  const slot = document.getElementById("feedback-slot");
  slot.innerHTML = `
    <div class="feedback-panel ${correct ? "correct" : "incorrect"}">
      <strong>${correct ? "Correct" : "Not quite"}</strong>
      <p>${feedback.explanation || ""}</p>
      ${!correct ? `<p class="muted">Accepted answers: ${feedback.acceptedAnswers.join(", ")}</p>` : ""}
    </div>
  `;
}

async function handleCheckOrAdvance() {
  const question = currentQuestion();
  const existing = currentAnswerEntry();
  if (existing?.checked) {
    if (lessonState.currentIndex === lessonState.questions.length - 1) {
      await submitLesson();
      return;
    }
    lessonState.currentIndex += 1;
    lessonState.questionStartedAt = Date.now();
    renderQuestion();
    return;
  }

  const answer = selectedAnswerValue();
  if (!answer) {
    showToast("Enter or select an answer first.", "error");
    return;
  }

  try {
    const feedback = await fetchJSON(`/api/questions/${question.id}/check`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    });
    lessonState.answers.push({
      questionId: question.id,
      answer,
      responseTimeMs: Date.now() - lessonState.questionStartedAt,
      correct: feedback.correct,
      checked: true,
      feedback,
    });
    renderQuestion();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderSummary(result) {
  $("lesson-header").innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">${lessonState.lesson.isPlacement ? "Placement complete" : "Lesson complete"}</p>
        <h1>${lessonState.lesson.title}</h1>
      </div>
      <div class="lesson-meta">
        <span class="badge">${result.correctCount || 0}/${result.totalCount || lessonState.questions.length} correct</span>
      </div>
    </div>
  `;

  $("lesson-runner").innerHTML = lessonState.lesson.isPlacement
    ? `
      <div class="summary-screen">
        <article class="summary-card">
          <strong>Placement score ${Math.round(result.proficiencyScore * 100)}%</strong>
          <p class="muted">Recommended lesson: ${result.recommendedLessonTitle || "Start from the beginning"}</p>
          <div class="inline-actions">
            ${result.recommendedLessonId ? `<a class="button-primary" href="/lesson/${result.recommendedLessonId}">Start recommended lesson</a>` : '<a class="button-primary" href="/dashboard">Back to dashboard</a>'}
          </div>
        </article>
      </div>
    `
    : `
      <div class="summary-screen">
        <div class="summary-stats">
          <article class="summary-card"><span class="muted">Score</span><strong>${Math.round(result.score * 100)}%</strong></article>
          <article class="summary-card"><span class="muted">XP earned</span><strong>${result.xpEarned}</strong></article>
          <article class="summary-card"><span class="muted">Coins earned</span><strong>${result.coinsEarned}</strong></article>
          <article class="summary-card"><span class="muted">Boost</span><strong>${result.boostTriggered ? "Activated" : "Idle"}</strong></article>
        </div>
        <article class="summary-card">
          <h3>Achievements unlocked</h3>
          ${result.achievements.length
            ? result.achievements.map((item) => `<p>${item.name}: ${item.description}</p>`).join("")
            : '<p class="muted">No new achievements this round.</p>'}
        </article>
        <article class="summary-card">
          <h3>Question review</h3>
          <div class="section-list">
            ${result.results
              .map(
                (item) => `
                  <div class="leaderboard-row">
                    <span>Question ${item.questionId}</span>
                    <span class="${item.correct ? "" : "muted"}">${item.correct ? "Correct" : "Review needed"}</span>
                  </div>
                `
              )
              .join("")}
          </div>
        </article>
        <div class="inline-actions">
          <a class="button-primary" href="/dashboard">Back to dashboard</a>
          <a class="button-secondary" href="/lesson/${lessonState.lesson.id}">Retry lesson</a>
        </div>
      </div>
    `;
}

async function submitLesson() {
  const endpoint = lessonState.lesson.isPlacement
    ? `/api/courses/${lessonState.lesson.courseId}/placement-test`
    : `/api/lessons/${lessonState.lesson.id}/submit`;
  try {
    const result = await fetchJSON(endpoint, {
      method: "POST",
      body: JSON.stringify({
        answers: lessonState.answers.map((item) => ({
          questionId: item.questionId,
          answer: item.answer,
          responseTimeMs: item.responseTimeMs,
        })),
      }),
    });
    renderSummary(result);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function initLesson() {
  const lessonId = document.body.dataset.lessonId;
  try {
    const data = await fetchJSON(`/api/lessons/${lessonId}`);
    lessonState.lesson = data.lesson;
    lessonState.questions = data.questions;
    lessonState.currentIndex = 0;
    lessonState.answers = [];
    lessonState.questionStartedAt = Date.now();
    renderQuestion();
  } catch (error) {
    showToast(error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", initLesson);
