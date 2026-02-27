

"use client";

import { motion } from "framer-motion";
import { useState, useEffect, useRef } from "react";

export default function Home() {
  const [lane, setLane] = useState(0); // -1: Left, 0: Center, 1: Right

  // Obstacle state
  const [obstacleLane, setObstacleLane] = useState(0);
  const [obstacleY, setObstacleY] = useState(-50); // Starts offscreen/distant
  const [obstacleType, setObstacleType] = useState('youtube'); // youtube, instagram, notification

  // Focus Rewards State
  const [focusTime, setFocusTime] = useState(0); // in seconds
  const [distractionsAvoided, setDistractionsAvoided] = useState(0);
  const [multiplier, setMultiplier] = useState(1);
  const [pulseActive, setPulseActive] = useState(false);
  const [isGameOver, setIsGameOver] = useState(false);

  const gameStartTimeRef = useRef<number | null>(null);
  const lastRewardTimeRef = useRef<number | null>(null);

  const formatTime = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' || e.key === 'a') {
        setLane((prev) => Math.max(prev - 1, -1));
      } else if (e.key === 'ArrowRight' || e.key === 'd') {
        setLane((prev) => Math.min(prev + 1, 1));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isGameOver]);

  // Obstacle Game Loop
  useEffect(() => {
    if (isGameOver) return;

    let animationFrameId: number;
    let speed = 8; // Pixels per frame

    const gameLoop = () => {
      // 1. Move Obstacle
      setObstacleY((prevY) => {
        const newY = prevY + speed;
        // Collision threshold (based on perspective scaling and runner position)
        if (newY > 380 && newY < 480) {
          // Wait until state settles or use the ref/latest closure value if needed
          setLane((currentLane) => {
            if (currentLane === obstacleLane) {
              setIsGameOver(true);
            }
            return currentLane;
          });
        }
        // Reset if passed runner
        if (newY > 500) {
          setObstacleLane([-1, 0, 1][Math.floor(Math.random() * 3)]); // Pick new random lane
          const types = ['youtube', 'instagram', 'notification'];
          setObstacleType(types[Math.floor(Math.random() * types.length)]);
          setDistractionsAvoided(prev => prev + 1);
          return -50;
        }
        return newY;
      });

      // 2. Focus Mechanics (20s pulse)
      const now = Date.now();
      if (!gameStartTimeRef.current || !lastRewardTimeRef.current) {
        gameStartTimeRef.current = now;
        lastRewardTimeRef.current = now;
      } else {
        setFocusTime(Math.floor((now - gameStartTimeRef.current) / 1000));

        if (now - lastRewardTimeRef.current >= 20000) {
          lastRewardTimeRef.current = now;
          setMultiplier(m => m + 1);
          setPulseActive(true);
          setTimeout(() => setPulseActive(false), 2000);
        }
      }

      animationFrameId = requestAnimationFrame(gameLoop);
    };

    animationFrameId = requestAnimationFrame(gameLoop);
    return () => cancelAnimationFrame(animationFrameId);
  }, [lane, obstacleLane, isGameOver]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 relative">

      {/* Game Over Screen */}
      {isGameOver && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/80 backdrop-blur-sm pointer-events-none">
          <h1 className="text-white text-4xl font-bold mb-2">FOCUS BROKEN</h1>
          <div className="flex gap-6 mb-8 mt-4 text-center">
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-widest font-bold">Time</p>
              <p className="text-white font-mono text-xl">{formatTime(focusTime)}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-widest font-bold">Avoided</p>
              <p className="text-sky-400 font-mono text-xl">{distractionsAvoided}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-widest font-bold">Momentum</p>
              <p className="text-emerald-400 font-mono text-xl">{multiplier}x</p>
            </div>
          </div>
          <button
            onClick={() => {
              setIsGameOver(false);
              setObstacleY(-50);
              setFocusTime(0);
              setDistractionsAvoided(0);
              setMultiplier(1);
              setLane(0);
              const now = Date.now();
              gameStartTimeRef.current = now;
              lastRewardTimeRef.current = now;
            }}
            className="px-8 py-3 bg-white text-black font-bold rounded-lg shadow-lg pointer-events-auto hover:bg-slate-200 transition-colors"
          >
            Restart Focus Session
          </button>
        </div>
      )}

      {/* Focus Dashboard Overlay */}
      <div className="absolute top-4 inset-x-4 z-40 flex justify-between items-start pointer-events-none">

        {/* Left Stats */}
        <div className="bg-slate-900/80 backdrop-blur-md px-4 py-3 rounded-xl border border-slate-700 shadow-xl flex flex-col gap-1 min-w-[120px]">
          <div className="text-slate-400 text-[10px] font-bold tracking-wider uppercase">Focus Time</div>
          <div className="text-white font-mono font-bold text-2xl tracking-widest">{formatTime(focusTime)}</div>
        </div>

        {/* Right Stats */}
        <div className="flex flex-col gap-2 items-end">
          <div className="bg-slate-900/80 backdrop-blur-md px-4 py-2 rounded-xl border border-slate-700 shadow-xl flex flex-col items-end min-w-[120px]">
            <div className="text-slate-400 text-[10px] font-bold tracking-wider uppercase">Momentum</div>
            <div className="text-emerald-400 font-mono font-bold text-lg">{multiplier}x</div>
          </div>

          <div className="bg-slate-900/80 backdrop-blur-md px-4 py-2 rounded-xl border border-slate-700 shadow-xl flex flex-col items-end min-w-[120px]">
            <div className="text-slate-400 text-[10px] font-bold tracking-wider uppercase">Avoided</div>
            <div className="text-sky-400 font-mono font-bold text-lg">{distractionsAvoided}</div>
          </div>
        </div>

      </div>

      {/* 420x750 game container */}
      <div className="relative w-[420px] h-[750px] bg-sky-200 overflow-hidden shadow-2xl rounded-lg">

        {/* Sky gradient at the top */}
        <div className="absolute inset-x-0 top-0 h-[400px] bg-gradient-to-b from-blue-500 via-sky-300 to-sky-200" />

        {/* Distant city silhouette at the top */}
        <div className="absolute top-[180px] inset-x-0 flex items-end justify-center h-[120px] opacity-30">
          <div className="w-12 h-[80px] bg-slate-800 mx-1 rounded-t-sm" />
          <div className="w-16 h-[110px] bg-slate-800 mx-1 rounded-t-sm" />
          <div className="w-10 h-[60px] bg-slate-800 mx-1 rounded-t-sm" />
          <div className="w-20 h-[100px] bg-slate-800 mx-1 rounded-t-sm" />
          <div className="w-14 h-[75px] bg-slate-800 mx-1 rounded-t-sm" />
          <div className="w-12 h-[90px] bg-slate-800 mx-1 rounded-t-sm" />
        </div>

        {/* Ground track area */}
        <div className="absolute inset-x-0 bottom-0 h-[450px] flex justify-center perspective-[800px] overflow-hidden">
          {/* Tracks layout (simulated depth) */}
          <style>{`
            @keyframes trackScroll {
              from { background-position: 0 0px; }
              to { background-position: 0 40px; }
            }
          `}</style>
          <div
            className="w-[120%] h-[150%] origin-top absolute top-0"
            style={{
              transform: 'rotateX(60deg) translateY(20%)',
              background: 'repeating-linear-gradient(0deg, #5c4033, #5c4033 10px, transparent 10px, transparent 40px)',
              backgroundColor: '#8b5a2b',
              animation: 'trackScroll 0.4s linear infinite'
            }}
          >
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/60 to-transparent pointer-events-none z-10" />

            {/* 3 Rails container */}
            <div className="absolute inset-0 flex justify-between px-[15%]">
              {/* Left Rail */}
              <div className="w-6 h-full bg-gradient-to-r from-slate-400 via-slate-300 to-slate-500 shadow-[2px_0_5px_rgba(0,0,0,0.5)]" />
              {/* Center Rail */}
              <div className="w-6 h-full bg-gradient-to-r from-slate-400 via-slate-300 to-slate-500 shadow-[0_0_5px_rgba(0,0,0,0.5)]" />
              {/* Right Rail */}
              <div className="w-6 h-full bg-gradient-to-r from-slate-400 via-slate-300 to-slate-500 shadow-[-2px_0_5px_rgba(0,0,0,0.5)]" />
            </div>
          </div>
        </div>

        {/* Side yellow bridge walls */}
        {/* Left wall */}
        <div className="absolute bottom-0 left-0 w-[60px] h-[450px] bg-gradient-to-r from-yellow-500 to-yellow-400 border-r-4 border-yellow-600 shadow-[4px_0_10px_rgba(0,0,0,0.3)] z-10 flex flex-col justify-evenly">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="w-full h-4 bg-yellow-700/80 border-y border-yellow-800" />
          ))}
        </div>

        {/* Right wall */}
        <div className="absolute bottom-0 right-0 w-[60px] h-[450px] bg-gradient-to-l from-yellow-500 to-yellow-400 border-l-4 border-yellow-600 shadow-[-4px_0_10px_rgba(0,0,0,0.3)] z-10 flex flex-col justify-evenly">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="w-full h-4 bg-yellow-700/80 border-y border-yellow-800" />
          ))}
        </div>

        {/* Falling Obstacle (UI Distraction Card) */}
        {!isGameOver && (
          <div
            className="absolute left-1/2 z-10 pointer-events-none perspective-[500px]"
            style={{
              top: `${Math.max(250, 250 + obstacleY * 0.5)}px`, // Visual curve projection offset
              transform: `translate(-50%, ${obstacleY}px) scale(${Math.min(1.2, Math.max(0.4, obstacleY / 300))})`,
              marginLeft: `${obstacleLane * 110}px`,
              transition: 'margin-left 0.2s ease-in-out'
            }}
          >
            <div className="relative w-28 flex flex-col items-center origin-bottom" style={{ transformStyle: 'preserve-3d', transform: 'rotateX(15deg)' }}>
              {/* Floating animation */}
              <style>{`
               @keyframes float {
                 0%, 100% { transform: translateY(0px) translateZ(10px); }
                 50% { transform: translateY(-10px) translateZ(10px); }
               }
             `}</style>
              <div
                className="w-full bg-slate-50/95 backdrop-blur-sm rounded-lg shadow-sm border border-slate-200/50 flex flex-col items-center justify-center p-2 gap-1.5"
                style={{ animation: 'float 2s ease-in-out infinite' }}
              >
                {/* Dynamically render icon based on type */}
                {obstacleType === 'youtube' && (
                  <>
                    <div className="w-10 h-7 bg-red-600 rounded-[6px] flex items-center justify-center">
                      <div className="w-0 h-0 border-t-3 border-b-3 border-l-4 border-transparent border-l-white" />
                    </div>
                    <span className="text-[10px] leading-tight font-semibold text-slate-700 text-center">YouTube<br />Attempted</span>
                  </>
                )}

                {obstacleType === 'instagram' && (
                  <>
                    <div className="w-8 h-8 bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 rounded-[8px] flex items-center justify-center p-[2px]">
                      <div className="w-full h-full border-2 border-white rounded-[6px] flex items-center justify-center">
                        <div className="w-3 h-3 border-2 border-white rounded-full" />
                        <div className="absolute top-[4px] right-[4px] w-1 h-1 bg-white rounded-full" />
                      </div>
                    </div>
                    <span className="text-[10px] leading-tight font-semibold text-slate-700 text-center">Instagram<br />Opened</span>
                  </>
                )}

                {obstacleType === 'notification' && (
                  <>
                    <div className="w-8 h-8 bg-blue-500 rounded-full flex flex-col items-center justify-center relative">
                      <div className="w-4 h-3 bg-white rounded-t-md" />
                      <div className="w-5 h-1.5 bg-white rounded-b-sm border-t border-blue-500" />
                      <div className="absolute top-0 right-0 w-2.5 h-2.5 bg-red-500 rounded-full border border-white" />
                    </div>
                    <span className="text-[10px] leading-tight font-semibold text-slate-700 text-center">Distraction!</span>
                  </>
                )}
              </div>

              {/* Card Shadow */}
              <div className="absolute -bottom-6 w-16 h-4 bg-black/40 rounded-[50%] blur-[4px]" />
            </div>
          </div>
        )}

        {/* Minimalist Symbolic Runner Character (Framer Motion) */}
        <motion.div
          className="absolute bottom-[60px] left-1/2 z-20 pointer-events-none perspective-[500px]"
          style={{ marginLeft: '-24px' }} // w-12 child width offset
          animate={{
            x: lane * 110, // Smooth horizontal lane movement 
            y: [0, -7, 0]  // Subtle smooth vertical motion (6-8px)
          }}
          transition={{
            x: { type: "spring", stiffness: 300, damping: 20 },
            y: { repeat: Infinity, duration: 0.5, ease: "easeInOut" }
          }}
        >
          {/* Character Container - Slight 4 degree forward lean to represent motion */}
          <div className="relative w-12 h-32 origin-bottom transform translate-y-4" style={{ transformStyle: 'preserve-3d', transform: 'rotateX(4deg)' }}>
            {/* Ground Shadow */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-14 h-3 bg-black/60 rounded-[50%] blur-[3px]" />

            {/* Focus Reward Ripple */}
            {pulseActive && (
              <style>{`
                 @keyframes ripple {
                   0% { transform: scale(1); opacity: 0.8; }
                   100% { transform: scale(3.5); opacity: 0; }
                 }
               `}</style>
            )}
            {pulseActive && (
              <div className="absolute inset-x-0 bottom-0 top-12 flex items-center justify-center pointer-events-none z-0">
                <div className="absolute w-20 h-20 bg-yellow-400 rounded-full mix-blend-screen blur-[4px]" style={{ animation: 'ripple 1.5s ease-out forwards' }} />
              </div>
            )}

            {/* Minimalist Abstract Body (Glossy Capsule) */}
            <div className="absolute inset-x-0 bottom-2 top-12 bg-gradient-to-b from-slate-200 to-slate-400 rounded-full shadow-[0_5px_15px_rgba(0,0,0,0.3)] border border-white/50 overflow-hidden">
              {/* Reflection highlight */}
              <div className="absolute top-0 right-1 w-3 h-full bg-gradient-to-b from-white to-transparent opacity-60 rounded-full" />
            </div>

            {/* Minimalist Abstract Head (Glossy Sphere) */}
            <div className="absolute inset-x-0 top-0 h-10 w-10 mx-auto bg-gradient-to-tr from-slate-300 to-white rounded-full shadow-[0_4px_10px_rgba(0,0,0,0.2)] border border-white/60">
              {/* Reflection highlight */}
              <div className="absolute top-1 right-1 w-3 h-3 bg-white opacity-80 rounded-full" />
            </div>
          </div>
        </motion.div>

      </div>
    </div>
  );
}

