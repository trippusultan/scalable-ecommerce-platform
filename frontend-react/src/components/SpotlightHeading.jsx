import React, { useEffect, useRef } from "react";
import { animate, motion, useMotionTemplate, useMotionValue, useReducedMotion } from "framer-motion";

// Adapted from Originkit "spotlighttext" (FlashlightText), stack: react.
// Cursor-following spotlight reveals the bright heading inside a soft circle.
// Recolored for the clean-matte theme: DIM base = light bone, BRIGHT = ink.
// (Original used useIsStaticRenderer() — a Framer-only hook; replaced with a
// constant false since this app always runs in a live, interactive browser.)

const DEFAULT_FONT =
  'Fraunces, Georgia, "Times New Roman", serif';

export default function SpotlightHeading({ text, font = DEFAULT_FONT, className = "", as = "h1" }) {
  const prefersReducedMotion = useReducedMotion();

  const containerRef = useRef(null);
  const contentRef = useRef(null);

  const maskX = useMotionValue(0);
  const maskY = useMotionValue(0);
  const maskSizeMV = useMotionValue(0);

  const brightColor = "#1F1D1A"; // ink
  const dimColor = "rgba(31,29,26,0.22)"; // light bone-dim
  const maskSize = 220;
  const intensity = 12;

  const core = Math.max(10, Math.min(100, intensity));
  const maskImage = useMotionTemplate`radial-gradient(circle ${maskSizeMV}px at ${maskX}px ${maskY}px, black, black ${core}%, transparent 100%)`;

  const interactive = !prefersReducedMotion;

  useEffect(() => {
    if (!interactive) return;
    const el = containerRef.current;
    if (!el) return;
    const onMove = (e) => {
      const rect = (contentRef.current ?? el).getBoundingClientRect();
      maskX.set(e.clientX - rect.left);
      maskY.set(e.clientY - rect.top);
    };
    const onEnter = () => animate(maskSizeMV, maskSize, { duration: 0.35, ease: "easeOut" });
    const onLeave = () => animate(maskSizeMV, 0, { duration: 0.45, ease: "easeOut" });
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerenter", onEnter);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerenter", onEnter);
      el.removeEventListener("pointerleave", onLeave);
    };
  }, [interactive, maskSize, maskX, maskY, maskSizeMV]);

  const textStyle = {
    margin: 0,
    fontFamily: font,
    fontWeight: 500,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    userSelect: "none",
  };

  const Tag = as;

  return (
    <div ref={containerRef} className={className} style={{ position: "relative", width: "100%" }}>
      <div ref={contentRef} style={{ position: "relative", width: "100%" }}>
        <Tag aria-label={text} style={{ ...textStyle, position: "relative", color: dimColor }}>
          {text}
        </Tag>
        <motion.div
          aria-hidden
          style={{
            ...textStyle,
            position: "absolute",
            top: 0,
            left: 0,
            color: brightColor,
            pointerEvents: "none",
            WebkitMaskImage: maskImage,
            maskImage: maskImage,
            WebkitMaskSize: "100%",
            maskSize: "100%",
            WebkitMaskRepeat: "no-repeat",
            maskRepeat: "no-repeat",
          }}
        >
          {text}
        </motion.div>
      </div>
    </div>
  );
}
