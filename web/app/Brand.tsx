"use client";

import Link from "next/link";
import Mark from "./Mark";

/**
 * The TimeSense wordmark. Clicking it returns you home: if you're already on the landing page it
 * smooth-scrolls to the top (Next.js won't scroll on same-route navigation); otherwise it navigates.
 */
export default function Brand({ size = 19 }: { size?: number }) {
  return (
    <Link
      href="/"
      className="wordmark"
      style={{ fontSize: size }}
      onClick={(e) => {
        if (typeof window !== "undefined" && window.location.pathname === "/") {
          e.preventDefault();
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      }}
    >
      <Mark size={Math.round(size * 1.15)} />
      <span>
        Time<b>Sense</b>
      </span>
    </Link>
  );
}
