document.addEventListener("DOMContentLoaded", () => {
    // Base URLs — relative when served from FastAPI, absolute as fallback
    const API_BASE = window.location.origin.includes("localhost:8000") ? "" : "http://localhost:8000";
    const WS_BASE = `ws://${window.location.host || "localhost:8000"}`;

    const form = document.getElementById("sprintForm");
    const timetableInput = document.getElementById("timetable_text");
    const fileInput = document.getElementById("fileUpload");
    const resultsPanel = document.getElementById("resultsPanel");
    const sprintsList = document.getElementById("sprintsList");
    const loader = document.getElementById("loader");
    const emptyState = document.getElementById("emptyState");
    const generateBtn = document.getElementById("generateBtn");

    // New elements for safety/quiz
    const activeMissionBanner = document.getElementById("activeMissionBanner");
    const activeSprintTopic = document.getElementById("activeSprintTopic");
    const btnEmergencyExit = document.getElementById("btnEmergencyExit");

    const quizOverlay = document.getElementById("quizOverlay");
    const quizLoader = document.getElementById("quizLoader");
    const quizContainer = document.getElementById("quizContainer");

    const safetyOverlay = document.getElementById("safetyOverlay");
    const safetyChallengeText = document.getElementById("safetyChallengeText");
    const safetyInput = document.getElementById("safetyInput");
    const btnCancelSafety = document.getElementById("btnCancelSafety");
    const btnUnlockSystem = document.getElementById("btnUnlockSystem");
    const safetyError = document.getElementById("safetyError");

    // Notification elements
    const btnNotifications = document.getElementById("btnNotifications");
    const notifBadge = document.getElementById("notifBadge");
    const notifToast = document.getElementById("notifToast");
    const notifToastText = document.getElementById("notifToastText");
    const notifRecapOverlay = document.getElementById("notifRecapOverlay");
    const notifRecapList = document.getElementById("notifRecapList");
    const notifRecapSubtitle = document.getElementById("notifRecapSubtitle");
    const btnClearNotifs = document.getElementById("btnClearNotifs");
    const btnCloseRecap = document.getElementById("btnCloseRecap");
    const btnEndSession = document.getElementById("btnEndSession");

    let currentActiveSprint = null;
    let ws = null;

    let quizActive = false; // Prevent multiple quiz popups
    let heldNotifCount = 0;
    let toastTimeout = null;

    // Initialize WebSocket for Block Events
    function initWebSocket() {
        ws = new WebSocket(`${WS_BASE}/ws`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event === "BLOCK" && currentActiveSprint && !quizActive) {
                console.log("OS Blocker Activated!", data.app);
                triggerQuizPopup();
            }

            // Notification held event (live push from backend)
            if (data.event === "NOTIFICATION_HELD" && data.notification) {
                heldNotifCount = data.held_count || (heldNotifCount + 1);
                updateNotifBadge();
                showNotifToast(data.notification);
            }

            // Sync held count from periodic STATUS heartbeat
            if (data.held_notifications_count !== undefined) {
                heldNotifCount = data.held_notifications_count;
                updateNotifBadge();
            }
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed. Reconnecting...");
            setTimeout(initWebSocket, 3000);
        };
    }

    // --- QUIZ POPUP LOGIC (Non-Closable) ---
    async function triggerQuizPopup() {
        quizActive = true;
        quizOverlay.style.display = "flex";
        quizContainer.innerHTML = "";
        quizLoader.style.display = "flex";

        // Prevent Escape key from closing
        document.addEventListener("keydown", blockEscape);

        const topic = currentActiveSprint ? currentActiveSprint.suggested_topic : "General Study";

        try {
            const res = await fetch(`${API_BASE}/api/brain/quiz`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ topic: topic, num_questions: 3 })
            });
            const data = await res.json();
            quizLoader.style.display = "none";

            if (data.quiz && data.quiz.length > 0) {
                showQuizQuestions(data.quiz);
            } else {
                // Fallback: if API returns empty, still block until retry
                quizContainer.innerHTML = `<p style="color: #ff3b3b;">Failed to load questions. Retrying...</p>`;
                setTimeout(() => {
                    quizLoader.style.display = "flex";
                    quizContainer.innerHTML = "";
                    triggerQuizPopup();
                }, 3000);
            }
        } catch (err) {
            console.error("Quiz fetch error:", err);
            quizLoader.style.display = "none";
            quizContainer.innerHTML = `<p style="color: #ff3b3b;">Server error. Retrying in 3s...</p>`;
            setTimeout(() => {
                quizContainer.innerHTML = "";
                triggerQuizPopup();
            }, 3000);
        }
    }

    function blockEscape(e) {
        if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
        }
    }

    function showQuizQuestions(questions) {
        let currentIndex = 0;

        function renderQuestion() {
            quizContainer.innerHTML = "";

            if (currentIndex >= questions.length) {
                // All answered correctly — dismiss!
                quizOverlay.style.display = "none";
                quizActive = false;
                document.removeEventListener("keydown", blockEscape);
                return;
            }

            const q = questions[currentIndex];

            // Progress indicator
            const progress = document.createElement("p");
            progress.style.color = "#FF9800";
            progress.style.fontWeight = "bold";
            progress.style.marginBottom = "10px";
            progress.textContent = `Question ${currentIndex + 1} of ${questions.length}`;
            quizContainer.appendChild(progress);

            // Question text
            const qText = document.createElement("p");
            qText.textContent = q.question;
            qText.style.fontSize = "1.1rem";
            qText.style.marginBottom = "15px";
            qText.style.color = "#fff";
            quizContainer.appendChild(qText);

            // Feedback area
            const feedback = document.createElement("p");
            feedback.style.marginTop = "10px";
            feedback.style.fontWeight = "bold";
            feedback.style.minHeight = "24px";

            // Option buttons
            q.options.forEach(option => {
                const btn = document.createElement("button");
                btn.className = "quiz-btn";
                btn.textContent = option;
                btn.addEventListener("click", () => {
                    // Disable all buttons after click
                    const allBtns = quizContainer.querySelectorAll(".quiz-btn");
                    allBtns.forEach(b => b.disabled = true);

                    if (option === q.correct_answer) {
                        btn.classList.add("correct");
                        feedback.textContent = "✅ Correct!";
                        feedback.style.color = "#00E676";
                        currentIndex++;
                        setTimeout(renderQuestion, 1000);
                    } else {
                        btn.classList.add("wrong");
                        // Highlight the correct one
                        allBtns.forEach(b => {
                            if (b.textContent === q.correct_answer) b.classList.add("correct");
                        });
                        feedback.textContent = q.explanation ? `❌ Wrong! ${q.explanation}` : "❌ Wrong answer. Try the next one.";
                        feedback.style.color = "#ff3b3b";
                        // Re-enable after a delay so they must try again
                        setTimeout(() => {
                            allBtns.forEach(b => {
                                b.disabled = false;
                                b.classList.remove("wrong", "correct");
                            });
                            feedback.textContent = "";
                        }, 2000);
                    }
                });
                quizContainer.appendChild(btn);
            });

            quizContainer.appendChild(feedback);
        }

        renderQuestion();
    }

    initWebSocket();
    let timerInterval = null;
    let secondsElapsed = 0;

    // --- NOTIFICATION HELPERS ---
    function updateNotifBadge() {
        if (heldNotifCount > 0) {
            btnNotifications.style.display = "flex";
            notifBadge.textContent = heldNotifCount;
            notifBadge.style.display = "inline-block";
        } else {
            notifBadge.style.display = "none";
        }
    }

    function showNotifToast(notif) {
        const appName = notif.app_name || "App";
        const title = notif.title || "";
        notifToastText.textContent = `🔕 ${appName}: ${title || "Notification held for later"}`;
        notifToast.style.display = "flex";
        notifToast.classList.remove("toast-out");
        notifToast.classList.add("toast-in");

        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            notifToast.classList.remove("toast-in");
            notifToast.classList.add("toast-out");
            setTimeout(() => { notifToast.style.display = "none"; }, 300);
        }, 2500);
    }

    function getAppEmoji(appName) {
        const name = (appName || "").toLowerCase();
        if (name.includes("mail") || name.includes("outlook") || name.includes("gmail")) return "📧";
        if (name.includes("whatsapp")) return "💬";
        if (name.includes("instagram")) return "📷";
        if (name.includes("messenger") || name.includes("facebook")) return "💭";
        if (name.includes("telegram")) return "✈️";
        if (name.includes("discord")) return "🎮";
        if (name.includes("slack") || name.includes("teams")) return "💼";
        if (name.includes("twitter") || name.includes("x")) return "🐦";
        if (name.includes("snapchat")) return "👻";
        if (name.includes("youtube")) return "▶️";
        return "🔔";
    }

    function timeAgo(isoStr) {
        if (!isoStr) return "";
        const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
        if (diff < 60) return "just now";
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    async function fetchHeldNotifications() {
        try {
            const res = await fetch(`${API_BASE}/api/notifications/held`);
            const data = await res.json();
            heldNotifCount = data.count || 0;
            updateNotifBadge();
            return data.notifications || [];
        } catch (err) {
            console.error("Failed to fetch held notifications:", err);
            return [];
        }
    }

    async function clearHeldNotifications() {
        try {
            await fetch(`${API_BASE}/api/notifications/clear`, { method: "POST" });
            heldNotifCount = 0;
            updateNotifBadge();
        } catch (err) {
            console.error("Failed to clear notifications:", err);
        }
    }

    function renderRecap(notifications, isSessionOver) {
        notifRecapList.innerHTML = "";

        if (!notifications || notifications.length === 0) {
            notifRecapSubtitle.textContent = isSessionOver
                ? "No notifications were held — great focus! 🎯"
                : "No held notifications right now.";
            return;
        }

        notifRecapSubtitle.textContent = isSessionOver
            ? `${notifications.length} notification${notifications.length !== 1 ? "s" : ""} were filtered out during your focus session:`
            : `${notifications.length} notification${notifications.length !== 1 ? "s" : ""} held so far:`;

        notifications.forEach(notif => {
            const card = document.createElement("div");
            card.className = "notif-card";
            card.innerHTML = `
                <div class="notif-card-icon">${getAppEmoji(notif.app_name)}</div>
                <div class="notif-card-content">
                    <div class="notif-card-top">
                        <span class="notif-card-app">${notif.app_name || "Unknown"}</span>
                        <span class="notif-card-time">${timeAgo(notif.timestamp)}</span>
                    </div>
                    ${notif.title ? `<div class="notif-card-title">${notif.title}</div>` : ""}
                    ${notif.body ? `<div class="notif-card-body">${notif.body}</div>` : ""}
                </div>
            `;
            notifRecapList.appendChild(card);
        });
    }

    async function openRecap(isSessionOver = false) {
        const notifs = await fetchHeldNotifications();
        renderRecap(notifs, isSessionOver);
        notifRecapOverlay.style.display = "flex";
    }

    async function endFocusSession() {
        clearInterval(timerInterval);
        await openRecap(true);
        // Unlock on the backend
        try {
            await fetch(`${API_BASE}/api/safety/unlock`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ typed_sentence: "" }) // won't unlock but we handle it
            });
        } catch (e) { /* ignore */ }
        currentActiveSprint = null;
        activeMissionBanner.style.display = "none";
    }

    // --- NOTIFICATION BUTTON LISTENERS ---
    btnNotifications.addEventListener("click", () => openRecap(false));

    btnCloseRecap.addEventListener("click", () => {
        notifRecapOverlay.style.display = "none";
    });

    btnClearNotifs.addEventListener("click", async () => {
        await clearHeldNotifications();
        notifRecapList.innerHTML = "";
        notifRecapSubtitle.textContent = "All cleared!";
        setTimeout(() => { notifRecapOverlay.style.display = "none"; }, 600);
    });

    btnEndSession.addEventListener("click", () => endFocusSession());

    // Show selected file visually
    fileInput.addEventListener("change", (e) => {
        const btnLabel = e.target.previousElementSibling.querySelector("span");
        if (e.target.files.length > 0) {
            btnLabel.textContent = e.target.files[0].name;
            btnLabel.style.color = "#00D4FF";
        } else {
            btnLabel.textContent = "Select Calendar File";
            btnLabel.style.color = "";
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const textVal = timetableInput.value.trim();
        const fileVal = fileInput.files[0];

        if (!textVal && !fileVal) {
            alert("Please provide a text schedule or upload an ICS file to generate missions.");
            return;
        }

        // UI state updates before fetching
        resultsPanel.style.display = "block";
        loader.style.display = "flex";
        sprintsList.innerHTML = "";
        sprintsList.style.display = "none";
        emptyState.style.display = "none";
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Calculating...';

        const formData = new FormData();
        if (textVal) formData.append("timetable_text", textVal);
        if (fileVal) formData.append("file", fileVal);

        try {
            const response = await fetch(`${API_BASE}/api/brain/sprints`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || "Failed to fetch from the server.");
            }

            const data = await response.json();

            // If backend returned an error object (e.g. Groq not initialized), use fallback
            if (data.error || !data.sprints || data.sprints.length === 0) {
                throw new Error(data.error || "No sprints returned");
            }

            renderSprints(data.sprints);

        } catch (error) {
            console.warn("Sprint API failed, using fallback sprints:", error.message);
            // Generate fallback sprints from the user's text input so we can still test
            const topics = textVal
                ? textVal.split(/,|and|\n/).map(t => t.trim()).filter(t => t.length > 0)
                : ["General Study"];
            const now = new Date();
            const fallbackSprints = topics.map((topic, i) => ({
                suggested_topic: topic.charAt(0).toUpperCase() + topic.slice(1),
                duration_minutes: 45,
                start_time: new Date(now.getTime() + i * 50 * 60000).toISOString(),
                end_time: new Date(now.getTime() + (i * 50 + 45) * 60000).toISOString(),
            }));
            renderSprints(fallbackSprints);
        } finally {
            // Restore UI state
            loader.style.display = "none";
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fa-solid fa-rocket"></i> Generate Sprints';
        }
    });

    function renderSprints(sprints) {
        if (!sprints || sprints.length === 0) {
            emptyState.style.display = "block";
            return;
        }

        sprintsList.style.display = "flex";

        // Delay animation styling manually per card
        sprints.forEach((sprint, index) => {

            const sprintElement = document.createElement("div");
            sprintElement.className = "sprint-card";
            sprintElement.style.animationDelay = `${index * 0.15}s`;

            sprintElement.innerHTML = `
              <div class="sprint-info">
                  <h3><i class="fa-solid fa-star"></i> ${sprint.suggested_topic}</h3>
                  <div class="sprint-time">
                      <i class="fa-solid fa-play"></i> Click to start
                  </div>
              </div>
              <div class="sprint-duration">
                  <i class="fa-solid fa-stopwatch"></i> ${sprint.duration_minutes}m
              </div>
          `;

            sprintElement.addEventListener("click", () => activateSprint(sprint));

            sprintsList.appendChild(sprintElement);
        });
    }

    function activateSprint(sprint) {
        currentActiveSprint = sprint;
        activeSprintTopic.textContent = sprint.suggested_topic;
        activeMissionBanner.style.display = "flex";
        btnEndSession.style.display = "inline-flex";
        btnNotifications.style.display = "flex";
        heldNotifCount = 0;
        updateNotifBadge();

        // Create Timer UI if it doesn't exist
        let timerDisplay = document.getElementById("sprintTimer");
        if (!timerDisplay) {
            timerDisplay = document.createElement("span");
            timerDisplay.id = "sprintTimer";
            timerDisplay.style.marginLeft = "15px";
            timerDisplay.style.color = "#00D4FF";
            timerDisplay.style.fontWeight = "bold";
            activeMissionBanner.querySelector(".active-info").appendChild(timerDisplay);
        }

        clearInterval(timerInterval);
        secondsElapsed = 0;
        updateTimerDisplay();
        timerInterval = setInterval(() => {
            secondsElapsed++;
            updateTimerDisplay();
        }, 1000);

        function updateTimerDisplay() {
            const minutes = Math.floor(secondsElapsed / 60);
            const seconds = secondsElapsed % 60;
            timerDisplay.textContent = `⏱️ ${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }

        fetch(`${API_BASE}/api/safety/lock`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: sprint.suggested_topic })
        }).catch(console.error);

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- SAFETY EXIT LOGIC ---
    btnEmergencyExit.addEventListener("click", async () => {
        safetyOverlay.style.display = "flex";
        safetyChallengeText.textContent = "Loading challenge...";
        safetyInput.value = "";
        safetyError.style.display = "none";

        try {
            const res = await fetch(`${API_BASE}/api/safety/challenge`);
            const data = await res.json();
            safetyChallengeText.textContent = data.challenge;
        } catch (err) {
            safetyChallengeText.textContent = "Error loading challenge. Is server running?";
        }
    });

    btnCancelSafety.addEventListener("click", () => {
        safetyOverlay.style.display = "none";
    });

    btnUnlockSystem.addEventListener("click", async () => {
        const typed = safetyInput.value.trim();
        try {
            const res = await fetch(`${API_BASE}/api/safety/unlock`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ typed_sentence: typed })
            });
            const data = await res.json();

            if (data.success) {
                safetyOverlay.style.display = "none";
                clearInterval(timerInterval);
                currentActiveSprint = null;
                alert("System Unlocked! You have exited your focus session.");
            } else {
                safetyError.style.display = "block";
                safetyError.textContent = data.message;
            }
        } catch (err) {
            console.error(err);
        }
    });
});
