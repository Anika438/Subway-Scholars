import React from 'react';
import './Character.css';

function Character() {
  return (
    <div className="character-container">
      <div className="character">
        {/* Shadow on the ground */}
        <div className="char-shadow" />

        {/* Left arm (swinging) */}
        <div className="char-arm char-arm-l" />

        {/* Right arm (swinging) */}
        <div className="char-arm char-arm-r" />

        {/* Body (hoodie - seen from behind) */}
        <div className="char-body">
          {/* Hoodie back panel */}
          <div className="char-hoodie" />
          {/* Backpack */}
          <div className="char-backpack">
            <div className="backpack-pocket" />
          </div>
        </div>

        {/* Head (back view - hair visible, no face) */}
        <div className="char-head">
          <div className="char-hair" />
          {/* Cap/beanie */}
          <div className="char-cap" />
        </div>

        {/* Left leg (running) */}
        <div className="char-leg char-leg-l" />

        {/* Right leg (running) */}
        <div className="char-leg char-leg-r" />

        {/* Shoes */}
        <div className="char-shoe char-shoe-l" />
        <div className="char-shoe char-shoe-r" />
      </div>
    </div>
  );
}

export default Character;
