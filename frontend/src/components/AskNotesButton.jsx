"use client"

import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

/**
 * Circular cactus trigger for the "Ask your notes" modal (Figma 4213-153).
 * Icon-only by design; aria-label + tooltip preserve discoverability.
 * Positioning is the caller's concern (used as a bottom-left floating button
 * via `className`), keeping this component layout-agnostic.
 */
export function AskNotesButton({ onClick, className }) {
    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={onClick}
                    aria-label="Ask your notes"
                    className={cn(
                        "h-16 w-16 rounded-full border-2 border-cactus-ring/70 bg-cactus shadow-[0_8px_24px_rgba(0,0,0,0.22)] transition hover:bg-cactus hover:scale-105 hover:brightness-105 hover:shadow-[0_12px_28px_rgba(0,0,0,0.28)] focus-visible:ring-2 focus-visible:ring-cactus",
                        className,
                    )}
                >
                    <Image
                        src="/cactus.png"
                        alt=""
                        aria-hidden
                        width={96}
                        height={114}
                        draggable={false}
                        className="h-12 w-auto select-none object-contain"
                    />
                </Button>
            </TooltipTrigger>
            <TooltipContent>Ask your notes</TooltipContent>
        </Tooltip>
    )
}

export default AskNotesButton
