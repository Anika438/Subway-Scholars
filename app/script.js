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

    // Initialize WebSocket for Block Events
    function initWebSocket() {
        ws = new WebSocket("ws://localhost:8000/ws");

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event === "BLOCK" && currentActiveSprint) {
                console.log("OS Blocker Activated!", data.app);
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
