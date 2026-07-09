"use client"

import React, { useState, useEffect } from 'react'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

// Preset palette from the Figma design (left -> right).
export const CATEGORY_COLORS = [
    '#EF9C66',
    '#FCDC94',
    '#C8CFA0',
    '#78ABA8',
    '#FF9E9E',
    '#C0ACD0',
]

const ACCENT = '#957139'

/**
 * Modal for creating a new category. Owns its own name/color state and calls
 * `onCreate({ name, color })`, which should resolve truthy on success so the
 * modal can reset and close.
 */
const CategoryCreationModal = ({ open, onOpenChange, onCreate }) => {
    const [name, setName] = useState('')
    const [color, setColor] = useState(null)
    const [isCreating, setIsCreating] = useState(false)

    // Reset the form whenever the modal is opened.
    useEffect(() => {
        if (open) {
            setName('')
            setColor(null)
            setIsCreating(false)
        }
    }, [open])

    const isValid = name.trim().length > 0 && !!color

    const handleCreate = async () => {
        if (!isValid || isCreating) return
        setIsCreating(true)
        try {
            const success = await onCreate({ name: name.trim(), color })
            if (success) {
                onOpenChange(false)
            }
        } finally {
            setIsCreating(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="bg-[#faf1e3] border-2 border-[#957139] rounded-2xl sm:max-w-xl">
                <DialogHeader>
                    <DialogTitle className="text-2xl md:text-3xl font-bold text-[#3f2f1c]">
                        Create New Category
                    </DialogTitle>
                </DialogHeader>

                <div className="flex flex-col gap-4 py-2">
                    <Input
                        autoFocus
                        placeholder="Category name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="h-14 rounded-xl border-2 border-[#957139] bg-transparent text-lg px-4 text-[#3f2f1c] placeholder:text-[#957139]/60 focus-visible:ring-[#957139]"
                    />

                    <div className="flex items-center justify-between gap-2 rounded-xl border-2 border-[#957139] px-4 py-3">
                        {CATEGORY_COLORS.map((swatch) => {
                            const selected = color === swatch
                            return (
                                <button
                                    key={swatch}
                                    type="button"
                                    aria-label={`Select color ${swatch}`}
                                    aria-pressed={selected}
                                    onClick={() => setColor(swatch)}
                                    className="h-8 w-8 rounded-full transition-transform hover:scale-110 focus:outline-none"
                                    style={{
                                        backgroundColor: swatch,
                                        border: selected ? `3px solid ${ACCENT}` : '3px solid transparent',
                                    }}
                                />
                            )
                        })}
                    </div>
                </div>

                <div className="flex justify-end pt-2">
                    <Button
                        type="button"
                        onClick={handleCreate}
                        disabled={!isValid || isCreating}
                        className="h-12 px-8 rounded-xl text-base font-semibold text-white bg-[#957139] hover:bg-[#856330]"
                    >
                        {isCreating ? 'Creating...' : 'Create Category'}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}

export default CategoryCreationModal
