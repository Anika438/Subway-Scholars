import React from 'react';
import './Obstacle.css';

function Obstacle({ lane, z, type }) {
  // Map lane to X position
  const xPercent = 50 + lane * 28;

  // Scale & opacity based on distance (z: 100=far, 0=near)
  const scale = Math.max(0.2, 1 - z / 120);
  const opacity = Math.min(1, scale + 0.2);
  const bottom = `${15 + (100 - z) * 0.45}%`;

  return (
    <div
      className={`obstacle obstacle-${type}`}
      style={{
        left: `${xPercent}%`,
        bottom,
        transform: `translateX(-50%) scale(${scale})`,
        opacity,
      }}
    >
      {type === 'barrier' ? (
        <div className="barrier">
          <div className="barrier-post barrier-post-l" />
          <div className="barrier-bar" />
          <div className="barrier-post barrier-post-r" />
          <div className="barrier-warning">⚠</div>
        </div>
      ) : (
        <div className="quiz-orb">
          <div className="orb-glow" />
          <span className="orb-icon">❓</span>
        </div>
      )}
    </div>
  );
}

export default Obstacle;
