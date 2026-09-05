"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";

const CIRCLE = 2 * Math.PI * 54;

/** Animated probability dial: counts up on mount, frozen final state for SR. */
export function ScoreDial({ value, label }: { value: number; label: string }) {
  const numRef = useRef<HTMLParagraphElement>(null);
  const ringRef = useRef<SVGCircleElement>(null);
  const clamped = Math.min(1, Math.max(0, value));

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const target = { p: 0 };
    const controls = animate(target, {
      p: clamped,
      duration: 900,
      ease: "outExpo",
      onUpdate: () => {
        if (numRef.current) numRef.current.textContent = target.p.toFixed(2);
        if (ringRef.current)
          ringRef.current.setAttribute(
            "stroke-dashoffset",
            (CIRCLE * (1 - target.p)).toFixed(1),
          );
      },
    });
    return () => {
      controls.revert();
    };
  }, [clamped]);

  return (
    <div
      role="meter"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={Number(clamped.toFixed(2))}
      aria-label={label}
      className="relative size-32 shrink-0"
    >
      <svg viewBox="0 0 120 120" className="size-32 -rotate-90" aria-hidden>
        <circle cx="60" cy="60" r="54" fill="none" strokeWidth="10" className="stroke-gridline" />
        <circle
          ref={ringRef}
          cx="60"
          cy="60"
          r="54"
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCLE.toFixed(1)}
          strokeDashoffset={(CIRCLE * (1 - clamped)).toFixed(1)}
          className="lab-dial-ring stroke-scan"
        />
      </svg>
      <p
        ref={numRef}
        className="absolute inset-0 flex items-center justify-center font-mono text-2xl text-foam tabular-nums"
      >
        {clamped.toFixed(2)}
      </p>
    </div>
  );
}
