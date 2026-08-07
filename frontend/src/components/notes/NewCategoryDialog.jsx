"use client"

import React, { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const CategoryColors = ["#EF9C66", "#FCDC94", "#C8CFA0", "#78ABA8", "#ED9AA2", "#B7A6D9"]

const NewCategoryDialog = ({ open, onClose, name, onNameChange, color, onColorChange, onSubmit, isCreating }) => {
    const inputRef = useRef(null)

    useEffect(() => {
        if (!open) return
        const handleKeyDown = (e) => { if (e.key === 'Escape') onClose() }
        document.addEventListener('keydown', handleKeyDown)
        const focusTimer = setTimeout(() => inputRef.current?.focus(), 0)
        return () => {
            document.removeEventListener('keydown', handleKeyDown)
            clearTimeout(focusTimer)
        }
    }, [open, onClose])

    if (!open) return null
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
            onClick={onClose}
        >
            <div
                className="w-[440px] rounded-xl bg-[#faf1e3] p-6 shadow-lg"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">Create New Category</h2>
                    <button type="button" aria-label="Close" onClick={onClose}>
                        <X className="w-5 h-5" strokeWidth={1.5} />
                    </button>
                </div>
                <Input
                    ref={inputRef}
                    className="border-[#957139] mb-4 bg-transparent"
                    placeholder="Enter name"
                    value={name}
                    onChange={(e) => onNameChange(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !isCreating && name.trim()) onSubmit()
                    }}
                />
                <div className="flex justify-between items-center rounded-md border border-[#957139] px-4 py-2.5 mb-6">
                    {CategoryColors.map(paletteColor => (
                        <button
                            key={paletteColor}
                            type="button"
                            aria-label={`Select color ${paletteColor}`}
                            aria-pressed={color === paletteColor}
                            className={`w-5 h-5 rounded-full ${color === paletteColor ? 'ring-2 ring-offset-2 ring-[#957139]' : ''}`}
                            style={{ backgroundColor: paletteColor }}
                            onClick={() => onColorChange(paletteColor)}
                        />
                    ))}
                </div>
                <div className="flex justify-end">
                    <Button
                        className="bg-[#957139] hover:bg-[#7a5c2e] text-white"
                        onClick={onSubmit}
                        disabled={isCreating || !name.trim()}
                    >
                        {isCreating ? "Creating..." : "Create Category"}
                    </Button>
                </div>
            </div>
        </div>
    )
}

export { NewCategoryDialog, CategoryColors }
