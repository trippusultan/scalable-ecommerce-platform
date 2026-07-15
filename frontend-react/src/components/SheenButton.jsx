import React from "react";

// Adapted from Originkit's "shiny-pill" (stack: react, zero deps).
// Recolored for the clean-matte theme: a soft light sheen sweeps across the
// button (an overlay sweep, not a duplicated text layer) so it reads as
// premium polish on BOTH outline and solid buttons — never neon/gloss.

const KEYFRAMES_ID = "sheen-button-keyframes";

export default function SheenButton({ children, onClick, type = "button", className = "", disabled = false, ariaLabel }) {
  // The base button. Sheen is a separate absolute overlay so it works on any
  // button background without needing to re-render the label.
  const shellStyle = {
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    boxSizing: "border-box",
    whiteSpace: "nowrap",
    overflow: "hidden",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.5 : 1,
  };

  const sheenStyle = {
    position: "absolute",
    inset: 0,
    pointerEvents: "none",
    background:
      "linear-gradient(100deg, transparent 30%, rgba(244,242,237,0.35) 50%, transparent 70%)",
    WebkitMaskImage: "linear-gradient(to right, #000, #000)",
    transform: "translateX(-120%)",
    animation: "sheenButtonSweep 3.4s ease-in-out infinite",
  };

  return (
    <button type={type} className={className} onClick={onClick} disabled={disabled} aria-label={ariaLabel} style={shellStyle}>
      <style
        id={KEYFRAMES_ID}
        dangerouslySetInnerHTML={{
          // Static keyframes string (no user input) — safe.
          __html: `@keyframes sheenButtonSweep {
            0% { transform: translateX(-120%); }
            60%, 100% { transform: translateX(120%); }
          }`,
        }}
      />
      <span style={{ position: "relative", zIndex: 1 }}>{children}</span>
      <span style={sheenStyle} aria-hidden="true" />
    </button>
  );
}
