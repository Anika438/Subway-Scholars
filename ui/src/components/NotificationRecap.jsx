import React from 'react';
import './NotificationRecap.css';

/**
 * Shows all notifications that were filtered out (held) during the focus session.
 * Displayed when the session ends or when the user clicks the notification badge.
 */

function getAppEmoji(appName) {
  const name = (appName || '').toLowerCase();
  if (name.includes('mail') || name.includes('outlook') || name.includes('gmail')) return '📧';
  if (name.includes('whatsapp')) return '💬';
  if (name.includes('instagram')) return '📷';
  if (name.includes('messenger') || name.includes('facebook')) return '💭';
  if (name.includes('telegram')) return '✈️';
  if (name.includes('discord')) return '🎮';
  if (name.includes('slack') || name.includes('teams')) return '💼';
  if (name.includes('twitter') || name.includes('x')) return '🐦';
  if (name.includes('snapchat')) return '👻';
  if (name.includes('youtube')) return '▶️';
  if (name.includes('reddit')) return '🔴';
  if (name.includes('tiktok')) return '🎵';
  if (name.includes('linkedin')) return '🔗';
  return '🔔';
}

function timeAgo(isoString) {
  if (!isoString) return '';
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function NotificationRecap({ notifications, onClose, onClear, isSessionOver }) {
  const hasNotifications = notifications && notifications.length > 0;

  return (
    <div className="notif-recap-overlay">
      <div className="notif-recap-panel">
        {/* Header */}
        <div className="notif-recap-header">
          <div className="notif-recap-title-row">
            <span className="notif-recap-icon">📬</span>
            <h2 className="notif-recap-title">
              {isSessionOver ? 'Session Over — Missed Notifications' : 'Held Notifications'}
            </h2>
          </div>
          <button className="notif-recap-close" onClick={onClose}>✕</button>
        </div>

        {/* Subtitle */}
        <p className="notif-recap-subtitle">
          {hasNotifications
            ? `${notifications.length} notification${notifications.length !== 1 ? 's' : ''} were filtered out during your focus session.`
            : 'No notifications were held — great focus!'}
        </p>

        {/* Notification List */}
        {hasNotifications && (
          <div className="notif-recap-list">
            {notifications.map((notif, idx) => (
              <div className="notif-recap-card" key={idx}>
                <div className="notif-card-icon">{getAppEmoji(notif.app_name)}</div>
                <div className="notif-card-content">
                  <div className="notif-card-top">
                    <span className="notif-card-app">{notif.app_name}</span>
                    <span className="notif-card-time">{timeAgo(notif.timestamp)}</span>
                  </div>
                  {notif.title && <div className="notif-card-title">{notif.title}</div>}
                  {notif.body && <div className="notif-card-body">{notif.body}</div>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="notif-recap-actions">
          {hasNotifications && (
            <button className="notif-recap-clear-btn" onClick={onClear}>
              Clear All
            </button>
          )}
          <button className="notif-recap-done-btn" onClick={onClose}>
            {isSessionOver ? 'Done' : 'Back to Session'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default NotificationRecap;
