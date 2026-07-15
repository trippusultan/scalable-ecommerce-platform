import React, { useEffect, useRef } from "react";

// Adapted from Originkit "electricborder" (stack: react). An animated canvas
// border that crackles around the element. Recolored for the clean-matte theme:
// a soft terracotta glow (not neon). The original used useIsStaticRenderer()
// (a Framer-only hook) — replaced with `false` since this app is always live.

function rand(x) {
  return (Math.sin(x * 12.9898) * 43758.5453) % 1;
}
function noise2D(x, y) {
  const i = Math.floor(x), j = Math.floor(y);
  const fx = x - i, fy = y - j;
  const a = rand(i + j * 57), b = rand(i + 1 + j * 57);
  const c = rand(i + (j + 1) * 57), d = rand(i + 1 + (j + 1) * 57);
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  return a * (1 - ux) * (1 - uy) + b * ux * (1 - uy) + c * (1 - ux) * uy + d * ux * uy;
}
function octavedNoise(x, octaves, lacunarity, gain, amplitude, frequency, time, seed, flatness) {
  let y = 0, amp = amplitude, freq = frequency;
  for (let i = 0; i < octaves; i++) {
    let oa = amp;
    if (i === 0) oa *= flatness;
    y += oa * noise2D(freq * x + seed * 100, time * freq * 0.3);
    freq *= lacunarity;
    amp *= gain;
  }
  return y;
}
function corner(cx, cy, r, start, arc, p) {
  const a = start + p * arc;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}
function roundedRectPoint(t, left, top, w, h, radius) {
  const sw = w - 2 * radius, sh = h - 2 * radius;
  const arc = (Math.PI * radius) / 2;
  const total = 2 * sw + 2 * sh + 4 * arc;
  const dist = t * total;
  let acc = 0;
  if (dist <= acc + sw) return { x: left + radius + ((dist - acc) / sw) * sw, y: top };
  acc += sw;
  if (dist <= acc + arc) return corner(left + w - radius, top + radius, radius, -Math.PI / 2, Math.PI / 2, (dist - acc) / arc);
  acc += arc;
  if (dist <= acc + sh) return { x: left + w, y: top + radius + ((dist - acc) / sh) * sh };
  acc += sh;
  if (dist <= acc + arc) return corner(left + w - radius, top + h - radius, radius, 0, Math.PI / 2, (dist - acc) / arc);
  acc += arc;
  if (dist <= acc + sw) return { x: left + w - radius - ((dist - acc) / sw) * sw, y: top + h };
  acc += sw;
  if (dist <= acc + arc) return corner(left + radius, top + h - radius, radius, Math.PI / 2, Math.PI / 2, (dist - acc) / arc);
  acc += arc;
  if (dist <= acc + sh) return { x: left, y: top + h - radius - ((dist - acc) / sh) * sh };
  acc += sh;
  return corner(left + radius, top + radius, radius, Math.PI, Math.PI / 2, (dist - acc) / arc);
}

export default function ElectricBorder({
  children,
  color = "#B15C3C",
  glowColor = "#C97E5E",
  glowIntensity = 4,
  speed = 0.6,
  chaos = 3,
  thickness = 2,
  radius = 16,
  active = true,
  className = "",
  style = {},
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const animationRef = useRef(null);
  const timeRef = useRef(0);
  const lastFrameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current, container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const octaves = 10, lacunarity = 1.6, gain = 0.7;
    const amplitude = chaos / 20, frequency = 10, flatness = 0;
    const displacement = 22;
    const gi = Math.max(1, Math.min(10, glowIntensity));
    const glowBlur = 5 + gi * 1.5, glowPasses = gi;
    const PAD = 60;

    let width = 0, height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function updateSize() {
      const rect = container.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      canvas.width = Math.floor((width + PAD * 2) * dpr);
      canvas.height = Math.floor((height + PAD * 2) * dpr);
      canvas.style.width = width + PAD * 2 + "px";
      canvas.style.height = height + PAD * 2 + "px";
      canvas.style.left = -PAD + "px";
      canvas.style.top = -PAD + "px";
    }
    updateSize();

    function draw(now) {
      if (!lastFrameRef.current) lastFrameRef.current = now;
      const dt = (now - lastFrameRef.current) / 1000;
      timeRef.current += dt * speed;
      lastFrameRef.current = now;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      const left = PAD, top = PAD, bw = width, bh = height;
      const maxR = Math.min(bw, bh) / 2;
      const r = Math.min(radius, Math.max(0, maxR));
      const perim = 2 * (bw + bh) + 2 * Math.PI * r;
      const samples = Math.max(24, Math.floor(perim / 2));

      ctx.beginPath();
      for (let i = 0; i <= samples; i++) {
        const t = i / samples;
        const pt = roundedRectPoint(t, left, top, bw, bh, r);
        const xn = octavedNoise(t * 8, octaves, lacunarity, gain, amplitude, frequency, timeRef.current, 0, flatness);
        const yn = octavedNoise(t * 8, octaves, lacunarity, gain, amplitude, frequency, timeRef.current, 1, flatness);
        const dx = pt.x + xn * displacement, dy = pt.y + yn * displacement;
        if (i === 0) ctx.moveTo(dx, dy); else ctx.lineTo(dx, dy);
      }
      ctx.closePath();

      if (glowBlur > 0) {
        ctx.lineWidth = 1;
        ctx.strokeStyle = glowColor;
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = glowBlur;
        for (let p = 0; p < glowPasses; p++) ctx.stroke();
        ctx.shadowBlur = 0;
      }
      ctx.lineWidth = thickness;
      ctx.strokeStyle = color;
      ctx.stroke();

      animationRef.current = requestAnimationFrame(draw);
    }

    if (active) {
      animationRef.current = requestAnimationFrame(draw);
    } else {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(updateSize) : null;
    ro?.observe(container);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      ro?.disconnect();
    };
  }, [color, glowColor, glowIntensity, speed, chaos, thickness, radius, active]);

  return (
    <div ref={containerRef} className={className} style={{ position: "relative", overflow: "visible", ...style }}>
      <canvas ref={canvasRef} style={{ position: "absolute", display: "block", pointerEvents: "none", zIndex: 3 }} />
      {children}
    </div>
  );
}
