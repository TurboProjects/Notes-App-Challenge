"use client"

import React, { useState, useEffect, useRef, useCallback, forwardRef } from 'react'
import { useToast } from '@/hooks/use-toast'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from "@/components/ui/button"
import { PlusIcon } from 'lucide-react'
import { useAuth } from '@/context/AuthProvider'
import withAuth from '@/hoc/withAuth'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import CategorySidebar from '@/components/CategorySidebar'
import { AiAssistantModal } from '@/components/AiAssistantModal'

// Helper function to format dates
const formatDate = (date) => {
    const now = new Date()
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return "Today"
    if (diffDays === 1) return "Yesterday"
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// NewNoteButton component
const NewNoteButton = ({ onClick }) => (
    <Button
        onClick={onClick}
        className="bg-transparent text-[#95715e] border border-[#95715e] rounded-full px-4 py-2 flex items-center font-bold hover:bg-[#95715e] hover:text-white transition-colors"
    >
        <PlusIcon className="w-4 h-4 mr-2" />
        New Note
    </Button>
)

// NoteCard component
const NoteCard = forwardRef(({ note }, ref) => {
    const router = useRouter()
    return (
        <Card
            ref={ref}
            className="h-72 rounded-lg shadow border-2 cursor-pointer"
            style={{ borderColor: note.category.color, backgroundColor: `${note.category.color}80` }}
            onClick={() => router.push(`/notes/editor/${note.id}`)}
        >
            <CardHeader className="p-4">
                <div className="flex justify-between text-sm">
                    <span className="font-bold">{formatDate(new Date(note.updated_at))}</span>
                    <span>{note.category.name}</span>
                </div>
            </CardHeader>
            <CardContent className="px-4 pt-0 pb-4">
                <CardTitle className="text-2xl font-serif font-bold mb-2">{note.title}</CardTitle>
                <p className="line-clamp-6">{note.content}</p>
            </CardContent>
        </Card>
    )
})
NoteCard.displayName = 'NoteCard'

// NoteGrid component
const NoteGrid = ({ notes, lastNoteRef }) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {notes.map((note, index) => (
            <NoteCard
                key={note.id}
                note={note}
                ref={index === notes.length - 1 ? lastNoteRef : null}
            />
        ))}
    </div>
)

// MainContent component
const MainContent = ({ notes, isLoading, nextPage, lastNoteRef }) => (
    <main className="flex-grow p-8">
        {notes.length > 0 ? (
            <NoteGrid notes={notes} />
        ) : isLoading ? (
            <Skeleton className="h-full w-full" />
        ) : (
            <div className="flex flex-col items-center justify-center h-full">
                <Image
                    src="/bubbletea.png"
                    width={256}
                    height={256}
                    alt="Bubble Tea"
                    className="w-64 h-64 mb-4"
                />
                <p className="text-2xl text-[#89644d] text-center">
                    I&apos;m just here waiting for your charming notes...
                </p>
            </div>
        )}
        {isLoading && nextPage && <Skeleton className="h-10 w-full mt-4" />}
        <div ref={lastNoteRef} />
    </main>
)

// NotesPage component
const NotesPage = () => {
    // common
    const { getToken } = useAuth()
    const { toast } = useToast()
    const router = useRouter()

    // AI Assistant modal
    const [isAiModalOpen, setIsAiModalOpen] = useState(false)

    // categories
    const [categories, setCategories] = useState([])
    const [isLoadingCategories, setIsLoadingCategories] = useState(true)
    const [defaultCategoryId, setDefaultCategoryId] = useState(null)
    const [selectedCategory, setSelectedCategory] = useState(null) // null represents 'All Categories'

    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/categories/`, {
                    headers: {
                        'Authorization': `Token ${getToken()}`,
                        'Content-Type': 'application/json',
                    },
                })
                if (!response.ok) {
                    throw new Error('Network response was not ok')
                }
                const data = await response.json()
                setCategories(data) // set fetched categories
                setDefaultCategoryId(data[0].id) // set default category id
            } catch (error) {
                toast({ title: "Failed to load categories. Please try again later.", variant: "destructive" })
                console.log('Error fetching categories:', error)
                setCategories([]) // set empty categories on error
            } finally {
                setIsLoadingCategories(false) // end loading state
            }
        }
        fetchCategories()
    }, [toast])

    const handleCategorySelect = (categoryId) => {
        setSelectedCategory(categoryId)
        setNotes([])
        setNextPage(null)
        fetchNotes(categoryId)
    }

    // notes
    const [isCreating, setIsCreating] = useState(false)
    const [isLoadingNotes, setIsLoadingNotes] = useState(false)
    const [notes, setNotes] = useState([])
    const [nextPage, setNextPage] = useState(null)
    const observer = useRef()

    const handleNewNote = async () => {
        setIsCreating(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/notes/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Token ${getToken()}`,
                },
                body: JSON.stringify({
                    category_id: defaultCategoryId
                }),
            })
            if (!response.ok) {
                throw new Error('Network response was not ok')
            }
            const data = await response.json()
            const newNoteId = data.id // extract note ID
            router.push(`/notes/editor/${newNoteId}`) // navigate to editor
        } catch (error) {
            toast({ title: "Failed to create a new note. Please try again.", variant: "destructive" })
        } finally {
            setIsCreating(false)
        }
    }

    const fetchNotes = useCallback(async (categoryId = null) => {
        if (isLoadingNotes) return
        setIsLoadingNotes(true)
        try {
            let url = nextPage || `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/notes/`
            if (categoryId) {
                const separator = url.includes('?') ? '&' : '?'
                url += `${separator}category_id=${categoryId}`
            }
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Token ${getToken()}`,
                    'Content-Type': 'application/json',
                },
            })
            if (!response.ok) {
                throw new Error('Network response was not ok')
            }
            const data = await response.json()
            if (!data.results) {
                throw new Error('Malformed API response')
            }
            setNotes(prevNotes => [...prevNotes, ...data.results])
            if (!data.next) {
                setNextPage(null)
            } else {
                setNextPage(data.next)
            }
        } catch (error) {
            toast({ title: "Failed to load notes. Please try again later.", variant: "destructive" })
            console.error('Error fetching notes:', error)
        } finally {
            setIsLoadingNotes(false)
        }
    }, [nextPage, isLoadingNotes, getToken, toast])

    const lastNoteRef = useCallback(node => {
        if (isLoadingNotes) {
            return
        }
        if (observer.current) observer.current.disconnect()
        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && nextPage) {
                fetchNotes()
            }
        })
        if (node) observer.current.observe(node)
    }, [isLoadingNotes, nextPage, fetchNotes])

    const notesFetched = useRef(false);
    useEffect(() => {
        if (notesFetched.current) return;
        notesFetched.current = true;
        fetchNotes()
    }, [])

    return (
        <div className="flex flex-col min-h-screen bg-[#faf1e4] font-sans relative">
            <div className="flex justify-end p-4">
                <NewNoteButton onClick={handleNewNote} />
            </div>
            <div className="flex flex-1">
                <CategorySidebar
                    categories={categories}
                    loading={isLoadingCategories}
                    onSelectCategory={handleCategorySelect}
                    selectedCategory={selectedCategory}
                />
                <MainContent
                    notes={notes}
                    isLoading={isLoadingNotes || isCreating}
                    nextPage={nextPage}
                    lastNoteRef={lastNoteRef}
                />
            </div>

            <button
                onClick={() => setIsAiModalOpen(true)}
                className="fixed bottom-6 left-6 w-16 h-16 bg-[#8B9A6D] hover:bg-[#7a8a5c] rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-110 z-40"
                title="Ask AI Assistant"
            >
                <Image
                    src="/cactus.png"
                    width={48}
                    height={48}
                    alt="AI Assistant"
                    className="w-12 h-12"
                />
            </button>

            <AiAssistantModal
                isOpen={isAiModalOpen}
                onClose={() => setIsAiModalOpen(false)}
            />
        </div>
    )
}

export default withAuth(NotesPage)