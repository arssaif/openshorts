import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";

export interface WordToken {
  word: string;
  start: number; // in seconds
  end: number;
}

export const SubtitlesTrack: React.FC<{ subtitles: WordToken[] }> = ({ subtitles }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Find active word
  const activeWordIndex = subtitles.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  if (activeWordIndex === -1) return null;

  // Window of 3-4 words centered around active word
  const startChunk = Math.max(0, activeWordIndex - 1);
  const endChunk = Math.min(subtitles.length, startChunk + 4);
  const currentChunk = subtitles.slice(startChunk, endChunk);

  const scaleSpring = spring({
    frame: frame - Math.floor(subtitles[activeWordIndex].start * fps),
    fps,
    config: { damping: 12, stiffness: 150 }
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: "22%",
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "14px",
        padding: "0 40px",
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.7)",
          padding: "16px 28px",
          borderRadius: "24px",
          display: "flex",
          gap: "14px",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(255, 255, 255, 0.15)"
        }}
      >
        {currentChunk.map((w, idx) => {
          const isActive = startChunk + idx === activeWordIndex;
          return (
            <span
              key={w.start + w.word}
              style={{
                fontFamily: "Arial Black, Impact, sans-serif",
                fontSize: "52px",
                fontWeight: 900,
                color: isActive ? "#FFE500" : "#FFFFFF",
                textTransform: "uppercase",
                textShadow: "0 0 10px rgba(0,0,0,0.9), 3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000",
                transform: isActive ? `scale(${1 + scaleSpring * 0.15})` : "scale(1)",
                display: "inline-block"
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </div>
  );
};

