const toastRoot = document.getElementById("toast-root");

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.message || "Request failed");
  }
  return data;
}

function showToast(message, type = "info") {
  if (!toastRoot) return;
  const item = document.createElement("div");
  item.className = `toast toast-${type}`;
  item.textContent = message;
  toastRoot.appendChild(item);
  window.setTimeout(() => item.remove(), 2800);
}

function percent(value) {
  return `${Math.max(0, Math.min(100, value))}%`;
}

function lessonButtonClass(lesson) {
  if (lesson.status === "completed") return "lesson-link completed";
  if (lesson.nextReviewAt) return "lesson-link review";
  return "lesson-link";
}

function renderHero(data) {
  const node = document.getElementById("dashboard-hero");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Daily mission</p>
        <h1>${data.user.username}, keep the streak moving.</h1>
        <p class="lede">Adaptive recommendations, voice practice, and your weekly league are ready.</p>
        <div class="inline-actions">
          ${data.nextLesson ? `<a class="button-primary" href="/lesson/${data.nextLesson}">Continue lesson</a>` : ""}
          <a class="button-secondary" href="/social">Open social hub</a>
        </div>
      </div>
      <div class="hero-strip">
        ${[
          ["XP", data.user.xp],
          ["Level", data.user.level],
          ["Coins", data.user.coins],
          ["Streak", `${data.user.dailyStreak} days`],
        ]
          .map(
            ([label, value]) => `
              <div class="stat-pill">
                <span>${label}</span>
                <strong>${value}</strong>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderCourses(data) {
  const node = document.getElementById("dashboard-courses");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Course map</p>
        <h2>Courses, units, lessons</h2>
      </div>
    </div>
    <div class="section-list">
      ${data.courses
        .map((course) => {
          const placementLesson = course.units.flatMap((unit) => unit.lessons).find((lesson) => lesson.title.toLowerCase().includes("placement"));
          return `
            <article class="course-card" style="border-top-color:${course.accentColor}">
              <div class="panel-header">
                <div>
                  <h3>${course.title}</h3>
                  <p class="muted">${course.translationDirection} • ${course.description}</p>
                  <div class="inline-actions">
                    <span class="badge">${course.enrolled ? "Enrolled" : "Available"}</span>
                    <span class="badge">Placement score ${Math.round(course.proficiencyScore * 100)}%</span>
                  </div>
                </div>
                <div class="course-actions">
                  <button class="action-button enroll-course" data-course-id="${course.id}">${course.enrolled ? "Set active" : "Enroll"}</button>
                  ${placementLesson ? `<a class="button-secondary" href="/lesson/${placementLesson.id}">Placement test</a>` : ""}
                </div>
              </div>
              ${course.units
                .map(
                  (unit) => `
                    <div class="unit-card">
                      <strong>${unit.position}. ${unit.title}</strong>
                      <p class="muted">${unit.description}</p>
                      <div class="lesson-grid">
                        ${unit.lessons
                          .map(
                            (lesson) => `
                              <a class="${lessonButtonClass(lesson)}" href="/lesson/${lesson.id}">
                                <div>
                                  <strong>${lesson.title}</strong>
                                  <p class="muted">${lesson.topic} • ${lesson.questionCount} questions</p>
                                </div>
                                <span class="badge">${lesson.status.replace("_", " ")}</span>
                              </a>
                            `
                          )
                          .join("")}
                      </div>
                    </div>
                  `
                )
                .join("")}
            </article>
          `;
        })
        .join("")}
    </div>
  `;

  node.querySelectorAll(".enroll-course").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const result = await fetchJSON(`/api/courses/${button.dataset.courseId}/enroll`, { method: "POST" });
        showToast(result.message, "success");
        initDashboard();
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  });
}

function renderRecommendations(data) {
  const node = document.getElementById("dashboard-recommendations");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Personalized next steps</p>
        <h2>Recommendations</h2>
      </div>
    </div>
    <div class="recommendation-grid">
      ${data.recommendations.length
        ? data.recommendations
            .map(
              (item) => `
                <article class="recommendation-card">
                  <strong>${item.lessonTitle}</strong>
                  <p class="muted">${item.courseTitle}</p>
                  <p>${item.reason}</p>
                  <a class="button-secondary" href="/lesson/${item.lessonId}">Open lesson</a>
                </article>
              `
            )
            .join("")
        : '<p class="muted">Complete more lessons to generate targeted recommendations.</p>'}
    </div>
  `;
}

function renderAnalytics(data) {
  const node = document.getElementById("dashboard-analytics");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Performance</p>
        <h2>Analytics dashboard</h2>
      </div>
    </div>
    <div class="analytics-grid">
      <article class="analytics-card"><span class="muted">Accuracy</span><strong>${data.analytics.accuracy}%</strong></article>
      <article class="analytics-card"><span class="muted">Completed lessons</span><strong>${data.analytics.completedLessons}</strong></article>
      <article class="analytics-card"><span class="muted">Review queue</span><strong>${data.analytics.reviewQueue}</strong></article>
      <article class="analytics-card"><span class="muted">Avg response</span><strong>${Math.round(data.analytics.avgResponseMs || 0)}ms</strong></article>
    </div>
    <div class="panel-header">
      <div>
        <h3>Weak topics</h3>
      </div>
    </div>
    <div class="bar-list">
      ${data.analytics.weakTopics.length
        ? data.analytics.weakTopics
            .map(
              (item) => `
                <div class="bar-row">
                  <strong>${item.topic}</strong>
                  <div class="mini-bar"><span style="width:${percent(item.accuracy)}"></span></div>
                  <span class="muted">${item.accuracy}%</span>
                </div>
              `
            )
            .join("")
        : '<p class="muted">Weak topics will appear after a few question attempts.</p>'}
    </div>
    <div class="panel-header">
      <div>
        <h3>Recent activity</h3>
      </div>
    </div>
    <div class="activity-grid">
      ${data.analytics.activity
        .map(
          (cell) => `
            <div class="activity-cell">
              <strong>${cell.correct}/${cell.total}</strong>
              <span>${cell.date.slice(5)}</span>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderLeaderboards(data) {
  const node = document.getElementById("dashboard-leaderboards");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Competition</p>
        <h2>${data.league.currentLeague} league</h2>
        <p class="muted">Weekly rank ${data.league.currentRank || "Unranked"} • ${data.league.weeklyXp} XP this week</p>
      </div>
    </div>
    <div class="leaderboard-grid">
      <article class="leaderboard-card">
        <strong>Weekly leaderboard</strong>
        <div class="section-list">
          ${data.leaderboards.weekly
            .map(
              (entry) => `
                <div class="leaderboard-row">
                  <span>#${entry.rank} ${entry.username}</span>
                  <span class="muted">${entry.xp} XP • ${entry.league}</span>
                </div>
              `
            )
            .join("")}
        </div>
      </article>
      <article class="leaderboard-card">
        <strong>Global leaderboard</strong>
        <div class="section-list">
          ${data.leaderboards.global
            .map(
              (entry) => `
                <div class="leaderboard-row">
                  <span>#${entry.rank} ${entry.username}</span>
                  <span class="muted">${entry.xp} XP • level ${entry.level}</span>
                </div>
              `
            )
            .join("")}
        </div>
      </article>
    </div>
  `;
}

function renderSocial(data) {
  const node = document.getElementById("dashboard-social");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Friends</p>
        <h2>Social snapshot</h2>
      </div>
    </div>
    <div class="friend-grid">
      ${data.social.friends.length
        ? data.social.friends
            .map(
              (friend) => `
                <article class="friend-card">
                  <strong>${friend.username}</strong>
                  <p class="muted">${friend.xp} XP • level ${friend.level}</p>
                  <p>${friend.dailyStreak} day streak • ${friend.league}</p>
                </article>
              `
            )
            .join("")
        : '<p class="muted">Add friends to compare streaks and weekly score.</p>'}
      <a class="button-secondary" href="/social">Manage friends</a>
    </div>
  `;
}

async function markNotificationRead(notificationId) {
  await fetchJSON(`/api/notifications/${notificationId}/read`, { method: "POST" });
}

function maybeTriggerBrowserNotifications(notifications) {
  if (!("Notification" in window)) return;
  const unread = notifications.filter((item) => !item.readAt);
  if (!unread.length) return;
  if (Notification.permission === "default") {
    Notification.requestPermission();
    return;
  }
  if (Notification.permission === "granted") {
    unread.slice(0, 2).forEach((item) => {
      new Notification(item.title, { body: item.message });
    });
  }
}

function renderNotifications(data) {
  const node = document.getElementById("dashboard-notifications");
  if (!node) return;
  maybeTriggerBrowserNotifications(data.notifications);
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Reminders</p>
        <h2>Notifications</h2>
      </div>
    </div>
    <div class="section-list">
      ${data.notifications.length
        ? data.notifications
            .map(
              (item) => `
                <article class="notification-card ${item.readAt ? "" : "unread"}">
                  <div class="notification-row">
                    <div>
                      <strong>${item.title}</strong>
                      <p class="muted">${item.message}</p>
                    </div>
                    <div class="inline-actions">
                      <span class="badge">${item.type.replace("_", " ")}</span>
                      ${item.readAt ? "" : `<button class="action-button read-notification" data-id="${item.id}">Mark read</button>`}
                    </div>
                  </div>
                </article>
              `
            )
            .join("")
        : '<p class="muted">No reminders queued right now.</p>'}
    </div>
  `;
  node.querySelectorAll(".read-notification").forEach((button) => {
    button.addEventListener("click", async () => {
      await markNotificationRead(button.dataset.id);
      initDashboard();
    });
  });
}

function renderAchievements(data) {
  const node = document.getElementById("dashboard-achievements");
  if (!node) return;
  node.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">Badges</p>
        <h2>Achievements</h2>
      </div>
    </div>
    <div class="achievement-grid">
      ${data.achievements.length
        ? data.achievements
            .map(
              (item) => `
                <article class="achievement-card">
                  <strong>${item.name}</strong>
                  <p>${item.description}</p>
                  <span class="badge">${new Date(item.earnedAt).toLocaleDateString()}</span>
                </article>
              `
            )
            .join("")
        : '<p class="muted">Achievements unlock as you progress through lessons, streaks, and social milestones.</p>'}
    </div>
  `;
}

async function initDashboard() {
  try {
    const data = await fetchJSON("/api/dashboard");
    renderHero(data);
    renderCourses(data);
    renderRecommendations(data);
    renderAnalytics(data);
    renderLeaderboards(data);
    renderSocial(data);
    renderNotifications(data);
    renderAchievements(data);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderSocialHub(social, leaderboards) {
  const friendsNode = document.getElementById("social-friends");
  const pendingNode = document.getElementById("social-pending");
  const weeklyNode = document.getElementById("social-weekly");

  if (friendsNode) {
    friendsNode.innerHTML = `
      <div class="panel-header">
        <div>
          <p class="eyebrow">Friends</p>
          <h2>Compare scores</h2>
        </div>
      </div>
      <div class="friend-grid">
        ${social.friends.length
          ? social.friends
              .map(
                (friend) => `
                  <article class="friend-card">
                    <strong>${friend.username}</strong>
                    <p class="muted">${friend.xp} XP • level ${friend.level}</p>
                    <p>${friend.dailyStreak} day streak • ${friend.league}</p>
                  </article>
                `
              )
              .join("")
          : '<p class="muted">No friends yet. Send a request above.</p>'}
      </div>
    `;
  }

  if (pendingNode) {
    pendingNode.innerHTML = `
      <div class="panel-header">
        <div>
          <p class="eyebrow">Requests</p>
          <h2>Pending invitations</h2>
        </div>
      </div>
      <div class="section-list">
        ${social.pending.length
          ? social.pending
              .map(
                (request) => `
                  <article class="pending-card">
                    <strong>${request.username}</strong>
                    <p class="muted">Sent ${new Date(request.createdAt).toLocaleDateString()}</p>
                    <div class="inline-actions">
                      <button class="button-primary respond-request" data-id="${request.id}" data-accept="true">Accept</button>
                      <button class="button-secondary respond-request" data-id="${request.id}" data-accept="false">Decline</button>
                    </div>
                  </article>
                `
              )
              .join("")
          : '<p class="muted">Nothing waiting for approval.</p>'}
      </div>
    `;

    pendingNode.querySelectorAll(".respond-request").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          const result = await fetchJSON("/api/friends/respond", {
            method: "POST",
            body: JSON.stringify({
              friendshipId: Number(button.dataset.id),
              accept: button.dataset.accept === "true",
            }),
          });
          showToast(result.message, "success");
          initSocialPage();
        } catch (error) {
          showToast(error.message, "error");
        }
      });
    });
  }

  if (weeklyNode) {
    weeklyNode.innerHTML = `
      <div class="panel-header">
        <div>
          <p class="eyebrow">Weekly ranking</p>
          <h2>Global standings</h2>
        </div>
      </div>
      <div class="section-list">
        ${leaderboards.weekly
          .map(
            (entry) => `
              <article class="leaderboard-card">
                <div class="leaderboard-row">
                  <strong>#${entry.rank} ${entry.username}</strong>
                  <span class="muted">${entry.xp} XP • ${entry.league}</span>
                </div>
              </article>
            `
          )
          .join("")}
      </div>
    `;
  }
}

async function initSocialPage() {
  try {
    const [social, leaderboards] = await Promise.all([fetchJSON("/api/social"), fetchJSON("/api/leaderboards")]);
    renderSocialHub(social, leaderboards);
  } catch (error) {
    showToast(error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "dashboard") {
    initDashboard();
  }
  if (page === "social") {
    initSocialPage();
    document.getElementById("friend-request-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = document.getElementById("friend-username");
      try {
        const result = await fetchJSON("/api/friends/request", {
          method: "POST",
          body: JSON.stringify({ username: input.value.trim() }),
        });
        input.value = "";
        showToast(result.message, "success");
        initSocialPage();
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  }
});
