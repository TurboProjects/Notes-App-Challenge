"use client"

import React, { useState } from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthProvider'
import { useToast } from '@/hooks/use-toast'

const COLORS = ['#EF9C66', '#FCDC94', '#C8CFA0', '#78ABA8', '#FF9E9E', '#C0ACD0']
const DEFAULT_COLOR = COLORS[0]

const NewCategoryDialog = ({ open, onOpenChange, onCreated }) => {
    const { getToken } = useAuth()
    const { toast } = useToast()
    const [name, setName] = useState('')
    const [color, setColor] = useState(DEFAULT_COLOR)
    const [submitting, setSubmitting] = useState(false)

    const reset = () => {
        setName('')
        setColor(DEFAULT_COLOR)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        // prevent empty name submission
        if (!name.trim()) return

        setSubmitting(true)

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/categories/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Token ${getToken()}`,
                },
                body: JSON.stringify({ name: name.trim(), color }),
            })
            if (!response.ok) {
                const err = await response.json().catch(() => ({}))
                throw new Error(err.detail || err.name?.[0] || 'Failed to create category')
            }
            const data = await response.json()
            onCreated?.(data)
            reset()
            onOpenChange(false)
        } catch (error) {
            toast({ title: error.message || 'Failed to create category', variant: 'destructive' })
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <DialogPrimitive.Root open={open} onOpenChange={(v) => { if (!v) reset(); onOpenChange(v) }}>
            <DialogPrimitive.Portal>
                <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50" />
                <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 bg-[#faf1e4] p-6 rounded-lg shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <DialogPrimitive.Title className="text-lg font-bold">Create New Category</DialogPrimitive.Title>
                        <DialogPrimitive.Close className="opacity-70 hover:opacity-100">
                            <X className="h-4 w-4" />
                        </DialogPrimitive.Close>
                    </div>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Input
                                id="cat-name"
                                className="border-[1px] border-[#95715e] focus:ring-0 focus:border-[#95715e]"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Name"
                                maxLength={50}
                                autoFocus
                            />
                        </div>
                        <div className="space-y-2">
                            <div id="cat-color" role="radiogroup" className="flex items-center justify-between gap-3 rounded border-[1px] border-[#95715e] p-3">
                                {COLORS.map((c) => (
                                    <button
                                        key={c}
                                        type="button"
                                        role="radio"
                                        aria-checked={color === c}
                                        aria-label={c}
                                        onClick={() => setColor(c)}
                                        className={`w-4 h-4 rounded-full border-2 transition-transform ${color === c ? 'border-[#95715e] scale-110' : 'border-transparent'}`}
                                        style={{ backgroundColor: c }}
                                    />
                                ))}
                            </div>
                        </div>
                        <div className="flex justify-end gap-2 pt-2">
                            <Button type="submit" disabled={submitting || !name.trim()} className="bg-[#95715e] hover:bg-[#957139] text-white"  >
                                {submitting ? 'Creating...' : 'Create Category'}
                            </Button>
                        </div>
                    </form>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    )
}

export default NewCategoryDialog
