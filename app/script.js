document.addEventListener("DOMContentLoaded", () => {
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

    let currentActiveSprint = null;
    let ws = null;

    let quizActive = false; // Prevent multiple quiz popups

    // Initialize WebSocket for Block Events
    function initWebSocket() {
        ws = new WebSocket("ws://localhost:8000/ws");

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event === "BLOCK" && currentActiveSprint && !quizActive) {
                console.log("OS Blocker Activated!", data.app);
                triggerQuizPopup();
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
            const res = await fetch("http://localhost:8000/api/brain/quiz", {
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
            const response = await fetch("http://localhost:8000/api/brain/sprints", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || "Failed to fetch from the server.");
            }

            const data = await response.json();
            renderSprints(data.sprints);

        } catch (error) {
            console.error("API Error:", error);
            alert("Error connecting to Gemini backend! Ensure the FastAPI server is running.\n\n" + error.message);
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

        fetch("http://localhost:8000/api/safety/lock", {
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
            const res = await fetch("http://localhost:8000/api/safety/challenge");
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
            const res = await fetch("http://localhost:8000/api/safety/unlock", {
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
