"use client"
import React, { useState } from 'react'
import CactusImage from './cactus-image'
import CactusModal from './cactus-modal'

export default function CactusController() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <CactusImage onClick={() => setOpen(true)} />
      <CactusModal open={open} onClose={() => setOpen(false)} />
    </>
  )
}
