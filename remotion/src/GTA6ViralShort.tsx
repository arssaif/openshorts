import React from "react";
import { AbsoluteFill, Video } from "remotion";
import { SubtitlesTrack } from "./Subtitles";

export interface GTA6ViralShortProps {
  videoSrc: string;
  gameplaySrc?: string;
  layout: "split" | "blur" | "crop";
  subtitles: Array<{ word: string; start: number; end: number }>;
}

export const GTA6ViralShort: React.FC<GTA6ViralShortProps> = ({
  videoSrc,
  gameplaySrc,
  layout,
  subtitles
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {layout === "split" ? (
        <>
          {/* Top Half: Main Video */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "50%",
              overflow: "hidden",
              borderBottom: "4px solid #ff007f"
            }}
          >
            <Video
              src={videoSrc}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover"
              }}
            />
          </div>

          {/* Bottom Half: Secondary or Ambient Gameplay */}
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              width: "100%",
              height: "50%",
              overflow: "hidden"
            }}
          >
            <Video
              src={gameplaySrc || videoSrc}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                filter: gameplaySrc ? "none" : "blur(8px) contrast(1.1) saturate(1.2)"
              }}
            />
          </div>
        </>
      ) : layout === "blur" ? (
        <>
          {/* Background Blurred */}
          <AbsoluteFill style={{ filter: "blur(25px) brightness(0.65)" }}>
            <Video
              src={videoSrc}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </AbsoluteFill>
          {/* Centered Main 16:9 Frame */}
          <div
            style={{
              position: "absolute",
              top: "28%",
              left: 0,
              width: "100%",
              height: "608px",
              boxShadow: "0 20px 50px rgba(0,0,0,0.8)"
            }}
          >
            <Video
              src={videoSrc}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          </div>
        </>
      ) : (
        /* Full Center 9:16 Crop */
        <AbsoluteFill>
          <Video
            src={videoSrc}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      )}

      {/* Kinetic Animated Subtitles Overlay */}
      <SubtitlesTrack subtitles={subtitles} />
    </AbsoluteFill>
  );
};

