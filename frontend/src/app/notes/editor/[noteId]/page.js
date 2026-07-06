"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem, SelectSeparator } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Circle, Plus, X } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/context/AuthProvider';
import withAuth from '@/hoc/withAuth';
import { formatDate } from '@/lib/utils';

const CREATE_CATEGORY_VALUE = "create-new-category"

const CATEGORY_COLORS = [
    "#B78452", // brown
    "#F2D06B", // yellow
    "#AFC97E", // green
    "#66A093", // teal
    "#E88F8F", // pink
    "#B08FC9", // purple
]

const CategoryEditor = ({ onCreated, onCancel }) => {
    const { toast } = useToast()
    const { getToken } = useAuth()
    const [name, setName] = useState("")
    const [color, setColor] = useState(CATEGORY_COLORS[0])
    const [isSaving, setIsSaving] = useState(false)

    const createCategory = async (retryCount = 0) => {
        if (!name.trim()) {
            toast({ title: "Please enter a category name.", variant: "destructive" })
            return
        }
        setIsSaving(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/categories/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Token ${getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name.trim(),
                    color
                }),
            })
            if (response.status === 409) {
                toast({ title: "Conflict detected. Please reload the category.", variant: "destructive" })
                return
            }
            if (!response.ok) {
                throw new Error('Failed to save category')
            }
            const data = await response.json()
            onCreated(data)
        } catch (error) {
            if (retryCount < 3 && error.message === 'Failed to save category') {
                setTimeout(() => {
                    createCategory(retryCount + 1)
                }, 1000)
            } else {
                toast({ title: "Error saving category. Please try again.", variant: "destructive" })
                console.error('Save category error:', error)
            }
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
            <Card className="w-[320px] bg-[#faf1e3] border-[#957139]">
                <CardContent className="p-6 flex flex-col gap-4">
                    <h2 className="text-lg font-semibold font-serif">Create New Category</h2>
                    <div className="flex flex-col gap-2">
                        <Label htmlFor="category-name">Name</Label>
                        <Input
                            id="category-name"
                            type="text"
                            placeholder="Category Name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            autoFocus
                        />
                    </div>
                    <div className="flex flex-col gap-2">
                        <Label>Color</Label>
                        <div className="flex items-center justify-between rounded-lg border border-neutral-300 bg-white px-4 py-2.5">
                            {CATEGORY_COLORS.map(swatch => (
                                <button
                                    key={swatch}
                                    type="button"
                                    aria-label={`Select color ${swatch}`}
                                    className={`w-5 h-5 rounded-full ${color === swatch ? "ring-2 ring-offset-2 ring-neutral-500" : ""}`}
                                    style={{ backgroundColor: swatch }}
                                    onClick={() => setColor(swatch)}
                                />
                            ))}
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={onCancel} disabled={isSaving}>
                            Cancel
                        </Button>
                        <Button onClick={createCategory} disabled={isSaving}>
                            {isSaving ? "Saving..." : "Save"}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
};

const CategorySelector = ({ categories, categoryId, onCategoryChange }) => (
    <Select value={categoryId} onValueChange={onCategoryChange}>
        <SelectTrigger className="w-[240px] h-10 rounded-lg border border-neutral-300 bg-white text-neutral-800">
            <SelectValue placeholder="Select Category" />
        </SelectTrigger>
        <SelectContent className="rounded-lg border-neutral-300">
            {categories.map(category => (
                <SelectItem key={category.id} value={String(category.id)}>
                    <div className="flex items-center text-neutral-800">
                        <Circle className="w-2.5 h-2.5 mr-2" fill={category.color} strokeWidth={0} />
                        {category.name}
                    </div>
                </SelectItem>
            ))}
            <SelectSeparator />
            <SelectItem value={CREATE_CATEGORY_VALUE}>
                <div className="flex items-center text-neutral-800">
                    <Plus className="w-3.5 h-3.5 mr-2" />
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
            className="w-8 h-8 mr-2 cursor-pointer text-neutral-700"
            onClick={() => router.push('/notes')}
            strokeWidth={1.5}
        />
    )
}

const Header = ({ categories, categoryId, onCategoryChange }) => (
    <header className="flex justify-between items-center mb-4">
        <CategorySelector categories={categories} categoryId={categoryId} onCategoryChange={onCategoryChange} />
        <CloseButton />
    </header>
)

const NoteCard = ({ color, title, content, onTitleChange, onContentChange, lastEdited, isSaving }) => (
    <Card className="rounded-xl shadow-md border-2 h-full"
        style={{ borderColor: color, backgroundColor: `${color}80` }}>
        <CardContent className="px-6 md:px-8 lg:px-12 py-3 md:py-4 lg:py-6 h-full flex flex-col">
            <div className="flex justify-end">
                <Label className="text-xs text-neutral-700">
                    Last Edited: {lastEdited}
                </Label>
            </div>
            <Input
                className="text-2xl md:text-3xl font-bold mb-4 font-serif bg-transparent border-none shadow-none placeholder:text-neutral-800"
                placeholder="Note Title"
                value={title}
                onChange={onTitleChange}
            />
            <Textarea
                className="text-base md:text-lg bg-transparent border-none resize-none shadow-none flex-grow text-neutral-800 placeholder:text-neutral-800"
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
    const [categoryId, setCategoryId] = useState("")
    const [title, setTitle] = useState("")
    const [content, setContent] = useState("")
    const [lastEdited, setLastEdited] = useState(null)
    const [version, setVersion] = useState(null)
    const [isSaving, setIsSaving] = useState(false)
    const [isCreatingCategory, setIsCreatingCategory] = useState(false)
    const params = useParams()
    const noteId = params.noteId

    const handleCategoryIdChange = (newCategoryId) => {
        if (newCategoryId === CREATE_CATEGORY_VALUE) {
            setIsCreatingCategory(true)
            return
        }
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
                setCategoryId(String(data.category.id))
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

    const handleCategoryCreated = (newCategory) => {
        setCategories(prev => [...prev, newCategory])
        setCategoryId(String(newCategory.id))
        setIsCreatingCategory(false)
    }

    const currentCategoryColor = useMemo(() => {
        const category = categories.find(cat => String(cat.id) === categoryId)
        return category ? category.color : 'gray'
    }, [categoryId, categories])

    // render
    return (
        <div className="bg-[#faf1e3] h-screen flex flex-col">
            <div className="px-4 md:px-8 lg:px-12 pt-4 md:pt-8 lg:pt-12">
                <Header categories={categories} categoryId={categoryId} onCategoryChange={handleCategoryIdChange} />
            </div>
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
            {isCreatingCategory && (
                <CategoryEditor
                    onCreated={handleCategoryCreated}
                    onCancel={() => setIsCreatingCategory(false)}
                />
            )}
        </div>
    )
}

export default withAuth(NoteEditorPage)
