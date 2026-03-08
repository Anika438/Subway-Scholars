const SERVER_URL = "http://127.0.0.1:8000";

document.addEventListener('DOMContentLoaded', async () => {
    // UI Elements
    const setupView = document.getElementById('setup-view');
    const timetableInput = document.getElementById('timetable-input');
    const generateBtn = document.getElementById('btn-generate');
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error-msg');

    const activeView = document.getElementById('active-view');
    const topicEl = document.getElementById('sprint-topic');
    const timeValEl = document.getElementById('time-val');
    const btnEnd = document.getElementById('btn-end');

    // Check if a sprint is already running
    chrome.storage.local.get(['activeSprint', 'endTime'], (data) => {
        if (data.activeSprint && data.endTime) {
            showActiveView(data.activeSprint, data.endTime);
        } else {
            showSetupView();
        }
    });

    generateBtn.addEventListener('click', async () => {
        const text = timetableInput.value.trim();
        if (!text) return;

        loadingEl.style.display = 'block';
        errorEl.style.display = 'none';
        generateBtn.disabled = true;

        try {
            // Need to send as Form Data since the python backend expects `timetable_text = Form(...)`
            const formData = new FormData();
            formData.append("timetable_text", text);

            const response = await fetch(`${SERVER_URL}/api/brain/sprints`, {
                method: "POST",
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                if (data.sprints && data.sprints.length > 0) {
                    // Start the first sprint as a test
                    const sprint = data.sprints[0];
                    const durationMs = sprint.duration_minutes * 60 * 1000;
                    const endTime = Date.now() + durationMs;

                    // Save to local storage
                    chrome.storage.local.set({
                        activeSprint: sprint,
                        endTime: endTime
                    }, () => {
                        // Tell background script to set an alarm
                        chrome.runtime.sendMessage({ action: "sprint_started", endTime: endTime });
                        showActiveView(sprint, endTime);
                    });
                } else {
                    showError("No study gaps found.");
                }
            } else {
                showError("Server Error.");
            }
        } catch (err) {
            showError("Cannot connect to desktop app.");
        } finally {
            loadingEl.style.display = 'none';
            generateBtn.disabled = false;
        }
    });

    btnEnd.addEventListener('click', () => {
        chrome.storage.local.remove(['activeSprint', 'endTime'], () => {
            chrome.runtime.sendMessage({ action: "sprint_ended" });
            showSetupView();
        });
    });

    function showSetupView() {
        activeView.style.display = 'none';
        setupView.style.display = 'flex';
        timetableInput.value = "";
    }

    let timerInterval = null;
    function showActiveView(sprint, endTime) {
        setupView.style.display = 'none';
        activeView.style.display = 'block';
        topicEl.textContent = sprint.suggested_topic;

        if (timerInterval) clearInterval(timerInterval);

        updateTimer(endTime);
        timerInterval = setInterval(() => updateTimer(endTime), 1000);
    }

    function updateTimer(endTime) {
        const remaining = endTime - Date.now();
        if (remaining <= 0) {
            clearInterval(timerInterval);
            timeValEl.textContent = "00:00";
            return;
        }

        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        timeValEl.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function showError(msg) {
        errorEl.textContent = msg;
        errorEl.style.display = 'block';
    }
});
