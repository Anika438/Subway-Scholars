const SERVER_URL = "http://127.0.0.1:8000";

document.addEventListener('DOMContentLoaded', async () => {
    // Parse URL params
    const urlParams = new URLSearchParams(window.location.search);
    const originalUrl = urlParams.get('url');
    const topic = urlParams.get('topic') || "General Study";

    const loadingEl = document.getElementById('loading');
    const quizUi = document.getElementById('quiz-ui');
    const progressText = document.getElementById('progress-text');
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    const feedbackEl = document.getElementById('feedback');

    let mcqs = [];
    let currentIndex = 0;
    const TOTAL_NEEDED = 3;

    try {
        // Fetch questions from Python Backend securely
        const response = await fetch(`${SERVER_URL}/api/brain/quiz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, num_questions: TOTAL_NEEDED })
        });

        if (response.ok) {
            const data = await response.json();
            mcqs = data.quiz || [];
            if (mcqs.length > 0) {
                loadingEl.style.display = 'none';
                quizUi.style.display = 'block';
                renderQuestion();
            } else {
                throw new Error("No questions returned.");
            }
        } else {
            throw new Error("Server error.");
        }
    } catch (err) {
        console.error("Quiz gen error:", err);
        // Fallback: If AI fails, let them pass
        unlockOriginalUrl();
    }

    function renderQuestion() {
        if (currentIndex >= TOTAL_NEEDED || currentIndex >= mcqs.length) {
            feedbackEl.className = 'success';
            feedbackEl.textContent = "Challenge Passed. Unlocking...";
            setTimeout(unlockOriginalUrl, 1000);
            return;
        }

        const q = mcqs[currentIndex];
        progressText.textContent = `Question ${currentIndex + 1} of ${TOTAL_NEEDED}`;
        questionText.textContent = q.question;
        feedbackEl.textContent = "";
        optionsContainer.innerHTML = "";

        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'btn-option';
            btn.textContent = opt;
            btn.onclick = () => checkAnswer(opt, q);
            optionsContainer.appendChild(btn);
        });
    }

    function checkAnswer(selectedOpt, currentQ) {
        if (selectedOpt === currentQ.correct_answer) {
            currentIndex++;
            renderQuestion();
        } else {
            feedbackEl.className = 'error';
            feedbackEl.textContent = `WRONG! ${currentQ.explanation}`;
        }
    }

    function unlockOriginalUrl() {
        // Just redirect back to the page. 
        // Note: If the sprint is still active, background.js WILL block it again.
        // The user must end the sprint to view distracting sites. But this unlocks the "penalty".

        // Actually, to make it forgiving, let's just send them to a safe page or new tab.
        // It's a focus blocker, so they shouldn't go back to the distracting site.
        window.location.href = "chrome://newtab/";
    }
});
