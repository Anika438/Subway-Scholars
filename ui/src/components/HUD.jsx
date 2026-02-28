import React from 'react';
import './HUD.css';

function formatTime(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function HUD({
  score,
  multiplier,
  highScore,
  focusSeconds,
  distractionSeconds,
  distractionsCount,
  streak,
  isPaused,
  onPause,
  heldNotificationsCount,
  onNotificationClick,
}) {
  const formattedScore = String(Math.floor(score)).padStart(6, '0');

  return (
    <div className="hud">
      {/* ── Row 1: Pause | Focus time | Multiplier | Score ── */}
      <div className="hud-row hud-row-top">
        <div className="hud-left-group">
          {/* Pause button (blue square like the image) */}
          <button className="hud-pause-btn" onClick={onPause}>
            {isPaused ? '▶' : '⏸'}
          </button>
          {/* Focus time (egg-style collectible counter) */}
          <div className="hud-focus-pill">
            <span className="focus-egg">📖</span>
            <span className="focus-value">{formatTime(focusSeconds)}</span>
          </div>
        </div>

        <div className="hud-right-group">
          {/* Multiplier (red badge) */}
          <div className="hud-multiplier">
            <span className="mult-x">x</span>
            <span className="mult-num">{multiplier}</span>
          </div>
          {/* Score */}
          <div className="hud-score">{formattedScore}</div>
        </div>
      </div>

      {/* ── Row 2: Distractions | Notifications | Coins (high score) ── */}
      <div className="hud-row hud-row-second">
        {distractionsCount > 0 && (
          <div className="hud-distract-pill">
            <span className="distract-bolt">⚡</span>
            <span className="distract-val">{formatTime(distractionSeconds)}</span>
            <span className="distract-count">({distractionsCount})</span>
          </div>
        )}
        {/* Held notifications badge */}
        <button
          className={`hud-notif-badge ${heldNotificationsCount > 0 ? 'has-notifs' : ''}`}
          onClick={onNotificationClick}
          title="Held notifications"
        >
          <span className="notif-bell">🔔</span>
          {heldNotificationsCount > 0 && (
            <span className="notif-count">{heldNotificationsCount}</span>
          )}
        </button>
        <div className="hud-coins">
          <span className="coins-value">{String(Math.floor(highScore)).padStart(3, '0')}</span>
          <span className="coins-icon">🪙</span>
        </div>
      </div>

      {/* ── Streak (shown when active) ── */}
      {streak > 0 && (
        <div className="hud-streak">
          <span className="streak-fire">🔥</span>
          <span className="streak-count">{streak} streak!</span>
        </div>
      )}
    </div>
  );
}

export default HUD;
