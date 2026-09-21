import React from 'react';

/**
 * Renders a list of short strings as bullet points using a flex layout
 * instead of native `list-style` markers — avoids the inconsistent marker
 * gap that `list-disc list-inside` produces across fonts/browsers.
 */
export default function BulletList({ items, className = '' }) {
  if (!items || items.length === 0) return null;

  return (
    <ul className={`space-y-1.5 ${className}`}>
      {items.map((item, idx) => (
        <li key={idx} className="flex items-start gap-2">
          <span className="mt-[7px] w-1.5 h-1.5 rounded-full bg-current opacity-60 shrink-0" />
          <span className="leading-snug">{item}</span>
        </li>
      ))}
    </ul>
  );
}
