"use client"

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUp, X } from 'lucide-react'
import { useRouter } from 'next/navigation'
import AskNotesButton from '@/components/AskNotesButton'
import { useAuth } from '@/context/AuthProvider'

const API = process.env.NEXT_PUBLIC_API_BASE_URL

// Ask flow states: idle -> asking -> success | failed
const AskYourNotes = () => {
    const { getToken } = useAuth()
    const router = useRouter()

    const [open, setOpen] = useState(false)
    const [text, setText] = useState('')
    const [phase, setPhase] = useState('idle')
    const [result, setResult] = useState(null)
    const [streamText, setStreamText] = useState('')
    const eventSourceRef = useRef(null)
    const pollTimerRef = useRef(null)
    const sseErrorsRef = useRef(0)
    const lastSeqRef = useRef(0)

    const cleanup = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close()
            eventSourceRef.current = null
        }
        if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
        }
    }, [])

    useEffect(() => cleanup, [cleanup])

    const close = () => {
        cleanup()
        setOpen(false)
        setPhase('idle')
        setResult(null)
        setText('')
        setStreamText('')
        sseErrorsRef.current = 0
        lastSeqRef.current = 0
    }

    const authHeaders = () => ({
        'Authorization': `Token ${getToken()}`,
        'Content-Type': 'application/json',
    })

    const handleTerminal = useCallback((question) => {
        if (question.status === 'PENDING') return false
        cleanup()
        setResult(question)
        setPhase(question.status === 'SUCCESS' ? 'success' : 'failed')
        return true
    }, [cleanup])

    // Polling fallback: dumb-simple, works anywhere SSE doesn't.
    const startPolling = useCallback((questionId) => {
        if (pollTimerRef.current) return
        pollTimerRef.current = setInterval(async () => {
            try {
                const response = await fetch(`${API}/api/v1/questions/${questionId}/`, {
                    headers: authHeaders(),
                })
                if (!response.ok) return
                handleTerminal(await response.json())
            } catch {
                // keep polling; the question keeps processing server-side
            }
        }, 2000)
    }, [handleTerminal]) // eslint-disable-line react-hooks/exhaustive-deps

    // SSE wrapper: EventSource can't send auth headers, so every (re)connect
    // mints a fresh short-lived signed ticket first.
    const connectStream = useCallback(async (questionId) => {
        try {
            const ticketResponse = await fetch(
                `${API}/api/v1/questions/${questionId}/stream-ticket/`,
                { method: 'POST', headers: authHeaders() },
            )
            if (!ticketResponse.ok) throw new Error('ticket mint failed')
            const { ticket } = await ticketResponse.json()

            const source = new EventSource(
                `${API}/api/v1/questions/${questionId}/stream?ticket=${encodeURIComponent(ticket)}`,
            )
            eventSourceRef.current = source
            // Token streaming: append delta suffixes; a seq that goes backwards
            // means a worker retry restarted the stream.
            source.addEventListener('delta', (event) => {
                const { seq, text: deltaText } = JSON.parse(event.data)
                if (seq <= lastSeqRef.current) {
                    setStreamText(deltaText)
                } else {
                    setStreamText((prev) => prev + deltaText)
                }
                lastSeqRef.current = seq
            })
            source.addEventListener('status', (event) => {
                if (handleTerminal(JSON.parse(event.data))) source.close()
            })
            source.onerror = () => {
                source.close()
                eventSourceRef.current = null
                sseErrorsRef.current += 1
                if (sseErrorsRef.current >= 2) {
                    startPolling(questionId) // degrade gracefully
                } else {
                    connectStream(questionId) // fresh ticket, reconnect
                }
            }
        } catch {
            startPolling(questionId)
        }
    }, [handleTerminal, startPolling]) // eslint-disable-line react-hooks/exhaustive-deps

    const ask = async () => {
        const question = text.trim()
        if (!question || phase === 'asking') return
        setPhase('asking')
        setStreamText('')
        lastSeqRef.current = 0
        try {
            const response = await fetch(`${API}/api/v1/questions/`, {
                method: 'POST',
                headers: authHeaders(),
                body: JSON.stringify({ text: question }),
            })
            if (!response.ok) throw new Error('ask failed')
            const { id } = await response.json()
            connectStream(id)
        } catch {
            setPhase('failed')
            setResult({ error: { code: 'REQUEST_FAILED' } })
        }
    }

    const citations = result?.answer?.citations ?? []

    return (
        <>
            <AskNotesButton
                onClick={() => setOpen(true)}
                className="fixed bottom-6 left-6 z-40"
            />

            {open && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
                    onClick={close}
                >
                    <div
                        className="w-full max-w-2xl rounded-2xl border border-[#d4b896] bg-[#fdf6ec] shadow-xl"
                        onClick={(event) => event.stopPropagation()}
                    >
                        {(phase === 'idle' || phase === 'asking') && (
                            <div className="relative p-6">
                                <textarea
                                    autoFocus
                                    value={text}
                                    onChange={(event) => setText(event.target.value)}
                                    onKeyDown={(event) => {
                                        if (event.key === 'Enter' && !event.shiftKey) {
                                            event.preventDefault()
                                            ask()
                                        }
                                    }}
                                    placeholder="Ask anything about your notes..."
                                    rows={4}
                                    disabled={phase === 'asking'}
                                    className="w-full resize-none bg-transparent text-lg text-[#4a3728] placeholder-[#a08b76] outline-none"
                                />
                                <div className="flex justify-end">
                                    <button
                                        onClick={ask}
                                        disabled={phase === 'asking' || !text.trim()}
                                        aria-label="Ask"
                                        className="flex h-12 w-12 items-center justify-center rounded-full bg-[#a3a838] text-white transition-opacity disabled:opacity-50"
                                    >
                                        {phase === 'asking' ? (
                                            <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                        ) : (
                                            <ArrowUp className="h-5 w-5" />
                                        )}
                                    </button>
                                </div>
                                {phase === 'asking' && (
                                    streamText ? (
                                        <p className="mt-2 max-h-60 overflow-y-auto whitespace-pre-wrap text-[#4a3728]">
                                            {streamText}
                                            <span className="animate-pulse">▍</span>
                                        </p>
                                    ) : (
                                        <p className="mt-2 text-sm text-[#a08b76]">
                                            Searching your notes and writing an answer...
                                        </p>
                                    )
                                )}
                            </div>
                        )}

                        {(phase === 'success' || phase === 'failed') && (
                            <div className="relative max-h-[70vh] overflow-y-auto p-8">
                                <button
                                    onClick={close}
                                    aria-label="Close"
                                    className="absolute right-4 top-4 text-[#95715e] hover:text-[#4a3728]"
                                >
                                    <X className="h-5 w-5" />
                                </button>

                                <h2 className="mb-4 pr-8 font-serif text-2xl font-bold text-[#4a3728]">
                                    {result?.text ?? text}
                                </h2>

                                {phase === 'success' ? (
                                    <>
                                        <p className="whitespace-pre-wrap text-[#4a3728]">
                                            {result?.answer?.text}
                                        </p>
                                        {citations.length > 0 ? (
                                            <div className="mt-6">
                                                <p className="font-bold text-[#4a3728]">References:</p>
                                                <ul className="mt-2 space-y-1">
                                                    {citations.map((citation) => (
                                                        <li key={`${citation.cited_order}-${citation.chunk_id}`}>
                                                            <button
                                                                onClick={() => citation.note_id
                                                                    && router.push(`/notes/editor/${citation.note_id}`)}
                                                                className="flex items-center text-[#4a3728] hover:text-[#95715e] hover:underline"
                                                            >
                                                                {citation.note_title || 'Untitled note'}
                                                                <ArrowRight className="ml-1 h-4 w-4" />
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ) : (
                                            <p className="mt-6 text-sm italic text-[#a08b76]">
                                                No notes were used for this answer.
                                            </p>
                                        )}
                                    </>
                                ) : (
                                    <p className="text-[#4a3728]">
                                        Something went wrong while answering
                                        {result?.error?.code ? ` (${result.error.code})` : ''}.
                                        Please try again in a moment.
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    )
}

export default AskYourNotes
