"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem, SelectSeparator } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Circle, Plus, X } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/context/AuthProvider';
import withAuth from '@/hoc/withAuth';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button'


const CREATE_CATEGORY_VALUE = "__create_new_category__"

const CategoryColors = ["#EF9C66", "#FCDC94", "#C8CFA0", "#78ABA8", "#ED9AA2", "#B7A6D9"]

const CategorySelector = ({ categories, categoryId, onCategoryChange, onCreateNew }) => (
    <Select
        value={categoryId}
        onValueChange={(value) => {
            if (value === CREATE_CATEGORY_VALUE) {
                onCreateNew()
                return
            }
            onCategoryChange(value)
        }}
    >
        <SelectTrigger className="w-[240px] h-10 rounded-md border border-[#957139]">
            <SelectValue placeholder="Select Category" />
        </SelectTrigger>
        <SelectContent>
            {categories.map(category => (
                <SelectItem key={category.id} value={category.id}>
                    <div className="flex items-center">
                        <Circle className="w-4 h-4 mr-2" fill={category.color} strokeWidth={0} />
                        {category.name}
                    </div>
                </SelectItem>
            ))}
            <SelectSeparator />
            <SelectItem value={CREATE_CATEGORY_VALUE}>
                <div className="flex items-center">
                    <Plus className="w-4 h-4 mr-2" />
                    Create New Category
                </div>
            </SelectItem>
        </SelectContent>
    </Select>
)

const CloseButton = () => {
    const router = useRouter()
    return (
        <X
            className="w-10 h-10 mr-2 cursor-pointer"
            color="#957139"
            onClick={() => router.push('/notes')}
            strokeWidth={1}
        />
    )
}

const Header = ({ categories, categoryId, onCategoryChange, onCreateNew }) => (
    <header className="flex justify-between items-center mb-4">
        <CategorySelector
            categories={categories}
            categoryId={categoryId}
            onCategoryChange={onCategoryChange}
            onCreateNew={onCreateNew}
        />
        <CloseButton />
    </header>
)

const NewCategoryDialog = ({ open, onClose, name, onNameChange, color, onColorChange, onSubmit, isCreating }) => {
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
                    className="border-[#957139] mb-4 bg-transparent"
                    placeholder="Enter name"
                    value={name}
                    onChange={(e) => onNameChange(e.target.value)}
                    autoFocus
                />
                <div className="flex justify-between items-center rounded-md border border-[#957139] px-4 py-2.5 mb-6">
                    {CategoryColors.map(paletteColor => (
                        <button
                            key={paletteColor}
                            type="button"
                            aria-label={`Select color ${paletteColor}`}
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

const NoteCard = ({ color, title, content, onTitleChange, onContentChange, lastEdited, isSaving }) => (
    <Card className="rounded-xl shadow-md border-2 h-full"
        style={{ borderColor: color, backgroundColor: `${color}80` }}>
        <CardContent className="px-6 md:px-8 lg:px-12 py-3 md:py-4 lg:py-6 h-full flex flex-col">
            <div className="flex justify-end">
                <Label className="text-xs">
                    Last Edited: {lastEdited}
                </Label>
            </div>
            <Input
                className="text-2xl md:text-3xl font-bold mb-4 font-serif bg-transparent border-none shadow-none"
                placeholder="Note Title"
                value={title}
                onChange={onTitleChange}
            />
            <Textarea
                className="text-base md:text-lg bg-transparent border-none resize-none shadow-none flex-grow"
                placeholder="Pour your heart out..."
                value={content}
                onChange={onContentChange}
            />
        </CardContent>
    </Card>
)

const NoteEditorPage = () => {

    // common
    const { toast } = useToast()
    const { getToken } = useAuth()

    // note
    const [categoryId, setCategoryId] = useState("random")
    const [title, setTitle] = useState("")
    const [content, setContent] = useState("")
    const [lastEdited, setLastEdited] = useState(null)
    const [version, setVersion] = useState(null)
    const [isSaving, setIsSaving] = useState(false)
    const params = useParams()
    const noteId = params.noteId

    // create category
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [newCategoryName, setNewCategoryName] = useState("")
    const [newCategoryColor, setNewCategoryColor] = useState(CategoryColors[0])
    const [isCreating, setIsCreating] = useState(false)


    const handleCategoryIdChange = (newCategoryId) => {
        setCategoryId(newCategoryId)
    }
    const handleTitleChange = (e) => {
        setTitle(e.target.value)
    }
    const handleContentChange = (e) => {
        setContent(e.target.value)
    }

    useEffect(() => {
        if (!title) return
      
        const timeout = setTimeout(() => {
            setLastEdited(formatDate(new Date()))
            saveNote()
        }, 1000)
      
        // Cleanup function:
        return () => clearTimeout(timeout)
      }, [title, content, categoryId])

    const saveNote = async (retryCount = 0) => {
        setIsSaving(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/notes/${noteId}/`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Token ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title,
                    content,
                    category_id: categoryId,
                    updated_at: version
                }),
            })
            if (response.status === 409) {
                toast({ title: "Conflict detected. Please reload the note.", variant: "destructive" })
                return
            }
            if (!response.ok) {
                throw new Error('Failed to save note')
            }
            const data = await response.json()
            setVersion(data.updated_at)
        } catch (error) {
            if (retryCount < 3 && error.message === 'Failed to save note') {
                setTimeout(() => {
                    saveNote(retryCount + 1)
                }, 1000)
            } else {
                toast({ title: "Error saving note. Please try again.", variant: "destructive" })
                console.error('Save note error:', error)
            }
        } finally {
            setIsSaving(false)
        }
    }
    const createCategory = async () => {
        const name = newCategoryName.trim()
        if (!name || isCreating) return
        setIsCreating(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/categories/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Token ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name,
                    color: newCategoryColor,
                }),
            })
            const data = await response.json().catch(() => null)
            if (!response.ok) {
                const message = data?.name?.[0] || data?.detail || "Error creating category. Please try again."
                toast({ title: message, variant: "destructive" })
                return
            }
            setCategories(prev => [...prev, data])
            setCategoryId(data.id)
            setIsDialogOpen(false)
            setNewCategoryName("")
            setNewCategoryColor(CategoryColors[0])
        } catch (error) {
            toast({ title: "Error creating category. Please try again.", variant: "destructive" })
            console.error('Create category error:', error)
        } finally {
            setIsCreating(false)
        }
    }

    
    useEffect(() => {
        const fetchNote = async () => {
            try {
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/notes/${noteId}/`, {
                    headers: {
                        'Authorization': `Token ${getToken()}`,
                        'Content-Type': 'application/json',
                    },
                })
                if (!response.ok) {
                    throw new Error('Failed to fetch note data')
                }
                const data = await response.json()
                setCategoryId(data.category.id)
                setTitle(data.title)
                setContent(data.content)
                setVersion(data.updated_at)
                setLastEdited(formatDate(data.updated_at))
            } catch (error) {
                toast({ title: "Error fetching note data.", variant: "destructive" })
                console.error('Fetch note error:', error)
            }
        }
        if (noteId) {
            fetchNote()
        }
    }, [noteId])

    // categories
    const [categories, setCategories] = useState([])
    const [isLoadingCategories, setIsLoadingCategories] = useState(true)

    useEffect(() => {
        const fetchCategories = async () => {
        setIsLoadingCategories(true) // start loading state
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

    const currentCategoryColor = useMemo(() => {
        const category = categories.find(cat => cat.id === categoryId)
        return category ? category.color : 'gray'
    }, [categoryId, categories])

    // render
    return (
        <div className="bg-[#faf1e3] h-screen flex flex-col">
            <div className="px-4 md:px-8 lg:px-12 pt-4 md:pt-8 lg:pt-12">
                <Header
                    categories={categories}
                    categoryId={categoryId}
                    onCategoryChange={handleCategoryIdChange}
                    onCreateNew={() => setIsDialogOpen(true)}
                />
            </div>
            <NewCategoryDialog
                open={isDialogOpen}
                onClose={() => setIsDialogOpen(false)}
                name={newCategoryName}
                onNameChange={setNewCategoryName}
                color={newCategoryColor}
                onColorChange={setNewCategoryColor}
                onSubmit={createCategory}
                isCreating={isCreating}
            />
            <div className="px-4 md:px-8 lg:px-12 pb-4 md:pb-8 lg:pb-12 flex-1">
                <NoteCard
                    color={currentCategoryColor}
                    title={title}
                    content={content}
                    onTitleChange={handleTitleChange}
                    onContentChange={handleContentChange}
                    lastEdited={lastEdited}
                    isSaving={isSaving}
                />
            </div>
        </div>
    )
}

export default withAuth(NoteEditorPage)
