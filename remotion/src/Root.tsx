import React from "react";
import { Composition } from "remotion";
import { GTA6ViralShort } from "./GTA6ViralShort";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="GTA6ViralShort"
        component={GTA6ViralShort}
        durationInFrames={30 * 40} // 40 seconds at 30 fps
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          videoSrc: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
          gameplaySrc: "",
          layout: "split" as const,
          subtitles: [
            { word: "GTA", start: 0.5, end: 0.9 },
            { word: "6", start: 0.9, end: 1.2 },
            { word: "IS", start: 1.2, end: 1.4 },
            { word: "FINALLY", start: 1.4, end: 1.8 },
            { word: "HERE!", start: 1.8, end: 2.3 }
          ]
        }}
      />
    </>
  );
};

