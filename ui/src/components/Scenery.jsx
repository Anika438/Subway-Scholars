import React from 'react';
import './Scenery.css';

function Scenery({ speed }) {
  const scrollDuration = Math.max(3, 10 / speed);

  return (
    <>
      {/* ── Distant background (misty buildings + sky) ── */}
      <div className="distant-bg">
        <div className="distant-buildings">
          <div className="dist-bld dist-bld-1" />
          <div className="dist-bld dist-bld-2" />
          <div className="dist-bld dist-bld-3" />
          <div className="dist-bld dist-bld-4" />
          <div className="dist-bld dist-bld-5" />
        </div>
        {/* Distant train/tram */}
        <div className="distant-train">
          <div className="train-body" />
          <div className="train-windows" />
          <div className="train-roof" />
        </div>
      </div>

      {/* ── Left barrier WALL (solid golden bridge railing) ── */}
      <div className="barrier-wall barrier-wall-left">
        <div className="wall-face" />
        <div className="wall-top-cap" />
        {/* Flower pots that scroll along the wall */}
        <div className="wall-pots wall-pots-scroll" style={{ animationDuration: `${scrollDuration}s` }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="wall-pot-segment">
              <div className="pot-box">
                <div className="pot-box-body" />
                <div className="pot-greenery" />
                <div className="pot-flower pot-flower-red" />
                <div className="pot-flower pot-flower-white" />
                <div className="pot-leaf pot-leaf-l" />
                <div className="pot-leaf pot-leaf-r" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right barrier WALL (solid golden bridge railing) ── */}
      <div className="barrier-wall barrier-wall-right">
        <div className="wall-face" />
        <div className="wall-top-cap" />
        {/* Flower pots that scroll along the wall */}
        <div className="wall-pots wall-pots-scroll" style={{ animationDuration: `${scrollDuration}s` }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="wall-pot-segment">
              <div className="pot-box">
                <div className="pot-box-body" />
                <div className="pot-greenery" />
                <div className="pot-flower pot-flower-red" />
                <div className="pot-flower pot-flower-white" />
                <div className="pot-leaf pot-leaf-l" />
                <div className="pot-leaf pot-leaf-r" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Dark diagonal support poles (from barrier up to overhead) ── */}
      <div className="support-pole support-pole-left" />
      <div className="support-pole support-pole-right" />

      {/* ── Overhead arch frames with wires ── */}
      <div className="overhead">
        <div className="arch-frame arch-frame-1">
          <div className="arch-leg arch-leg-left" />
          <div className="arch-leg arch-leg-right" />
          <div className="arch-top" />
        </div>
        <div className="arch-frame arch-frame-2">
          <div className="arch-leg arch-leg-left" />
          <div className="arch-leg arch-leg-right" />
          <div className="arch-top" />
        </div>
        <div className="wire wire-1" />
        <div className="wire wire-2" />
        <div className="wire wire-3" />
      </div>

      {/* ── Water/ocean visible on right side ── */}
      <div className="ocean-bg" />
    </>
  );
}

export default Scenery;
