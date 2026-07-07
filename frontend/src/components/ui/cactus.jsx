import React from 'react'

export default function Cactus({ onClick }) {
  return (
    <button className="cactus-button" onClick={onClick} aria-label="Cactus">
      <svg width="40" height="47" viewBox="0 0 40 47" fill="none" xmlns="http://www.w3.org/2000/svg" role="img">
        <defs>
          <filter id="f1" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.15"/>
          </filter>
        </defs>
        <g filter="url(#f1)">
          <rect x="2" y="10" width="36" height="30" rx="6" fill="#F3E6D8" stroke="#E6CDAE" strokeWidth="1.5"/>
          <rect x="6" y="34" width="28" height="6" rx="3" fill="#E6CDAE"/>
          <g transform="translate(11,8)">
            <ellipse cx="8" cy="22" rx="8" ry="10" fill="#9CC6B7" stroke="#7EA99A" strokeWidth="1"/>
            <path d="M8 6 C6 6,4 8,4 11 C4 14,6 16,8 16" stroke="#7EA99A" strokeWidth="1.2" fill="#9CC6B7"/>
            <path d="M16 12 C18 12,20 14,20 17 C20 20,18 22,16 22" stroke="#7EA99A" strokeWidth="1.2" fill="#9CC6B7"/>
            <circle cx="6" cy="14" r="0.8" fill="#E6F3EA"/>
            <circle cx="18" cy="18" r="0.8" fill="#E6F3EA"/>
          </g>
        </g>
      </svg>
    </button>
  )
}
