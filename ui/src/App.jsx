import React, { useState, useEffect, useCallback, useRef } from 'react';
import Track from './components/Track';
import Character from './components/Character';
import HUD from './components/HUD';
import Scenery from './components/Scenery';
import QuizPopup from './components/QuizPopup';
import NotificationRecap from './components/NotificationRecap';
import './App.css';

const BOUNCER_API = 'http://localhost:8000';
const BOUNCER_WS = 'ws://localhost:8000/ws';

function App() {
  // ── Focus session state ──
  const [focusStartTime, setFocusStartTime] = useState(null);
  const [focusSeconds, setFocusSeconds] = useState(0);
  const [distractionSeconds, setDistractionSeconds] = useState(0);
  const [multiplier, setMultiplier] = useState(1);
  const [highScore, setHighScore] = useState(
    () => parseInt(localStorage.getItem('ss_highscore') || '0', 10)
  );
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [activeTopic, setActiveTopic] = useState('General Study');

  // ── Quiz state (triggered by bouncer) ──
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [distractionsCount, setDistractionsCount] = useState(0);
  const quizStartTimeRef = useRef(null);

  // ── Notification filter state ──
  const [heldNotifications, setHeldNotifications] = useState([]);
  const [heldCount, setHeldCount] = useState(0);
  const [showRecap, setShowRecap] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [heldToast, setHeldToast] = useState(null);
  const heldToastTimer = useRef(null);

  // ── Animation refs ──
  const frameRef = useRef(null);
  const multiplierRef = useRef(multiplier);
  multiplierRef.current = multiplier;

  // ── WebSocket connection to bouncer ──
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    function connect() {
      ws = new WebSocket(BOUNCER_WS);

      ws.onopen = () => {
        console.log('[Bouncer WS] Connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Distraction detected
          if (data.event === 'BLOCK' || data.is_blocking === true) {
            if (!showQuiz && isRunning) {
              triggerQuizFromBouncer(data.active_topic || activeTopic);
            }
          }

          // Notification held event (live)
          if (data.event === 'NOTIFICATION_HELD') {
            setHeldCount(data.held_count || 0);
            // Show brief toast
            if (data.notification) {
              showHeldToast(data.notification);
            }
          }

          // Sync held count from STATUS heartbeat
          if (data.held_notifications_count !== undefined) {
            setHeldCount(data.held_notifications_count);
          }

          // Sync active topic
          if (data.active_topic) {
            setActiveTopic(data.active_topic);
          }

          // Session started from bouncer
          if (data.monitoring_active && !isRunning) {
            startFocusSession();
          }
        } catch (e) {
          console.error('[Bouncer WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        console.log('[Bouncer WS] Disconnected, retrying in 3s...');
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();
    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [isRunning, showQuiz, activeTopic]);

  // ── Focus session timer ──
  useEffect(() => {
    if (!isRunning || isPaused || showQuiz) return;
    const ticker = setInterval(() => {
      setFocusSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(ticker);
  }, [isRunning, isPaused, showQuiz]);

  // ── Game loop (score + speed progression) ──
  useEffect(() => {
    if (!isRunning || isPaused || showQuiz) return;

    const loop = () => {
      setScore(prev => prev + multiplierRef.current);
      setSpeed(prev => Math.min(prev + 0.00015, 3.5));
      frameRef.current = requestAnimationFrame(loop);
    };

    frameRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frameRef.current);
  }, [isRunning, isPaused, showQuiz]);

  // ── Persist high score ──
  useEffect(() => {
    if (score > highScore) {
      setHighScore(score);
      localStorage.setItem('ss_highscore', String(score));
    }
  }, [score, highScore]);

  // ── Show brief toast when a notification is held ──
  const showHeldToast = useCallback((notif) => {
    if (heldToastTimer.current) clearTimeout(heldToastTimer.current);
    setHeldToast(notif);
    heldToastTimer.current = setTimeout(() => setHeldToast(null), 2500);
  }, []);

  // ── Fetch held notifications from API ──
  const fetchHeldNotifications = useCallback(async () => {
    try {
      const res = await fetch(`${BOUNCER_API}/api/notifications/held`);
      const data = await res.json();
      setHeldNotifications(data.notifications || []);
      setHeldCount(data.count || 0);
    } catch (err) {
      console.error('Failed to fetch held notifications:', err);
    }
  }, []);

  // ── Clear held notifications ──
  const clearHeldNotifications = useCallback(async () => {
    try {
      await fetch(`${BOUNCER_API}/api/notifications/clear`, { method: 'POST' });
      setHeldNotifications([]);
      setHeldCount(0);
    } catch (err) {
      console.error('Failed to clear notifications:', err);
    }
    setShowRecap(false);
  }, []);

  // ── Open notification recap panel ──
  const handleNotificationClick = useCallback(async () => {
    await fetchHeldNotifications();
    setShowRecap(true);
  }, [fetchHeldNotifications]);

  // ── End focus session & show recap ──
  const endSession = useCallback(async () => {
    setIsRunning(false);
    setIsPaused(false);
    setSessionEnded(true);
    await fetchHeldNotifications();
    setShowRecap(true);
  }, [fetchHeldNotifications]);

  // ── Start focus session ──
  const startFocusSession = useCallback(() => {
    setFocusStartTime(Date.now());
    setFocusSeconds(0);
    setDistractionSeconds(0);
    setScore(0);
    setMultiplier(1);
    setStreak(0);
    setSpeed(1);
    setDistractionsCount(0);
    setHeldNotifications([]);
    setHeldCount(0);
    setSessionEnded(false);
    setIsRunning(true);
    setIsPaused(false);
  }, []);

  // ── Fetch quiz from bouncer API when distraction is detected ──
  const triggerQuizFromBouncer = useCallback(async (topic) => {
    if (showQuiz || quizLoading) return;

    setQuizLoading(true);
    setShowQuiz(true);
    setDistractionsCount(prev => prev + 1);
    quizStartTimeRef.current = Date.now();

    try {
      const res = await fetch(`${BOUNCER_API}/api/brain/quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, num_questions: 3 }),
      });
      const data = await res.json();
      if (data.quiz && data.quiz.length > 0) {
        setQuizQuestions(data.quiz);
      } else {
        // Fallback questions
        setQuizQuestions([{
          question: `What are you supposed to be studying right now?`,
          options: [topic, "YouTube", "Instagram", "TikTok"],
          correct_answer: topic,
          explanation: `Get back to studying ${topic}!`
        }]);
      }
    } catch (err) {
      console.error('Quiz fetch failed:', err);
      setQuizQuestions([{
        question: `Focus check: What is your current study topic?`,
        options: [topic, "Social Media", "Gaming", "Random Browsing"],
        correct_answer: topic,
        explanation: `Stay focused on ${topic}!`
      }]);
    } finally {
      setQuizLoading(false);
    }
  }, [showQuiz, quizLoading]);

  // ── Handle quiz completion ──
  const handleQuizComplete = useCallback((allCorrect) => {
    const quizDuration = quizStartTimeRef.current
      ? Math.round((Date.now() - quizStartTimeRef.current) / 1000)
      : 0;
    setDistractionSeconds(prev => prev + quizDuration);

    if (allCorrect) {
      setStreak(prev => prev + 1);
      setMultiplier(prev => Math.min(prev + 3, 30));
    } else {
      setStreak(0);
      setMultiplier(Math.max(1, multiplier - 2));
    }

    setShowQuiz(false);
    setQuizQuestions([]);
  }, [multiplier]);

  // ── Keyboard: ESC to pause ──
  useEffect(() => {
    const handleKey = (e) => {
      if (showQuiz) return;
      if (e.key === 'Escape') setIsPaused(prev => !prev);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [showQuiz]);

  // Auto-start session for now (in production, triggered by bouncer lock event)
  useEffect(() => {
    if (!isRunning) startFocusSession();
  }, []);

  return (
    <div className="game-container">
      {/* Sky gradient */}
      <div className="sky" />

      {/* Buildings & scenery on the sides */}
      <Scenery speed={speed} />

      {/* Moving 3D track */}
      <Track speed={speed} />

      {/* Running character (back-view) */}
      <Character />

      {/* HUD overlay */}
      <HUD
        score={score}
        multiplier={multiplier}
        highScore={highScore}
        focusSeconds={focusSeconds}
        distractionSeconds={distractionSeconds}
        distractionsCount={distractionsCount}
        streak={streak}
        isPaused={isPaused}
        onPause={() => setIsPaused(prev => !prev)}
        heldNotificationsCount={heldCount}
        onNotificationClick={handleNotificationClick}
      />

      {/* Quiz popup (triggered by bouncer distraction detection) */}
      {showQuiz && (
        <QuizPopup
          questions={quizQuestions}
          loading={quizLoading}
          topic={activeTopic}
          streak={streak}
          onComplete={handleQuizComplete}
        />
      )}

      {/* Notification Recap panel */}
      {showRecap && (
        <NotificationRecap
          notifications={heldNotifications}
          onClose={() => setShowRecap(false)}
          onClear={clearHeldNotifications}
          isSessionOver={sessionEnded}
        />
      )}

      {/* Brief toast when a notification is held */}
      {heldToast && (
        <div className="notif-held-toast">
          <span className="notif-held-toast-icon">📬</span>
          Notification held for later
        </div>
      )}

      {/* Paused overlay */}
      {isPaused && !showQuiz && (
        <div className="pause-overlay">
          <div className="pause-box">
            <h2>⏸ PAUSED</h2>
            <p>Press ESC to resume</p>
            <button onClick={() => setIsPaused(false)} className="resume-btn">
              RESUME
            </button>
            <button onClick={endSession} className="end-session-btn">
              END SESSION
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
