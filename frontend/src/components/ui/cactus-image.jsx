import React from 'react'

export default function CactusImage({ onClick, alt = 'Cactus' }) {
  return (
    <div className="cactus-wrapper" onClick={onClick} role="button" aria-label="Cactus wrapper">
      <img
        src="/cactus.png"
        alt={alt}
        width={56}
        height={66}
        className="cactus-image"
      />
    </div>
  )
}
