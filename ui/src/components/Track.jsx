import React from 'react';
import './Track.css';

function Track({ speed }) {
  const tieDuration = Math.max(0.35, 1.4 / speed);

  return (
    <div className="track-wrapper">
      <div className="track-surface">
        {/* Base ground (warm golden brown) */}
        <div className="track-ground" />

        {/* Darker gravel edges */}
        <div className="gravel gravel-left" />
        <div className="gravel gravel-right" />

        {/* Rail ties (wooden sleepers) - scrolling */}
        <div
          className="track-ties"
          style={{ animationDuration: `${tieDuration}s` }}
        >
          {Array.from({ length: 50 }).map((_, i) => (
            <div key={i} className="tie" />
          ))}
        </div>

        {/* Metal rails (3 lanes = 6 rails) */}
        <div className="rail rail-1" />
        <div className="rail rail-2" />
        <div className="rail rail-3" />
        <div className="rail rail-4" />
        <div className="rail rail-5" />
        <div className="rail rail-6" />
      </div>
    </div>
  );
}

export default Track;
