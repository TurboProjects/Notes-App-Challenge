"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Circle, X } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/context/AuthProvider';
import withAuth from '@/hoc/withAuth';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button'


const CategorySelector = ({ categories, categoryId, onCategoryChange, onNewCategory }) => (
    <Select value={categoryId} onValueChange={onCategoryChange}>
        <SelectTrigger className="w-[240px] h-10 rounded-md border border-[#957139]">
            <SelectValue placeholder="Select Category" />
        </SelectTrigger>
        <SelectContent>
            <>
                {categories.map(category => (
                    <SelectItem key={category.id} value={category.id}>
                        <div className="flex items-center">
                            <Circle className="w-4 h-4 mr-2" fill={category.color} strokeWidth={0} />
                            {category.name}
                        </div>
                    </SelectItem>
                ))}
                <div className="flex items-center" onClick={() => onNewCategory()}>
                    {/* <Circle className="w-4 h-4 mr-2" fill={category.color} strokeWidth={0} /> */}
                    {"Create New Category "}
                </div>
            </>
        </SelectContent>
    </Select>
)

const ModalNewCategory = ({ onClose, show, setCategories, setCategoryId }) => {
    const { getToken } = useAuth()
    const { toast } = useToast()
    const [categoryName, setCategoryName] = useState("")
    const [categoryColor, setCategoryColor] = useState("#78ABA8")
    const [colors, setColors] = useState([
        "#78ABA8",
        "#EF9C66",
        "#FCDC94",
        "#957139"
    ])
    const handleSubmit = async () => {
        console.log(categoryName, categoryColor)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/categories/`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${getToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: categoryName,
                color: categoryColor,
            }),
        })
        if (!response.ok) {
            throw new Error('Failed to create category')
        }
        const data = await response.json()
        console.log(data)
        setCategories(prev => [...prev, data])
        setCategoryId(data.id)
        onClose()
    } catch (error) {
        console.error('Error creating category:', error)
        toast(error.name)
    }
    }
    return (
        <div className='absolute left-0 w-full h-full bg-black/50' style={{ display: show ? 'block' : 'none' }}>
            <div className="card bg-white p-4 rounded-md max-w-md mx-auto justify-center" >
                <h1 className="text-2xl font-bold mb-4">Create New Category</h1>
                <Input className="mb-4" type="text" placeholder="Category Name" value={categoryName} onChange={(e) => setCategoryName(e.target.value)} />
                <div className="flex flex-wrap gap-2 mb-4 justify-center border-2 border-[#957139] rounded-md p-2">
                    {colors.map((color) => (
                        <div key={color} className="w-10 h-10 rounded-full cursor-pointer" style={{ backgroundColor: color }} onClick={() => setCategoryColor(color)} />
                    ))}
                </div>
                <Button onClick={handleSubmit} className="bg-[#957139] text-white">Create Category</Button>
            </div>
        </div>
    )
}

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

const Header = ({ categories, categoryId, onCategoryChange, onNewCategory }) => (
    <header className="flex justify-between items-center mb-4">
        <CategorySelector
            categories={categories}
            categoryId={categoryId}
            onCategoryChange={onCategoryChange}
            onNewCategory={onNewCategory}
        />
        <CloseButton />
    </header>
)

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
    const [showModalNewCategory, setShowModalNewCategory] = useState(false)
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
                    onNewCategory={() => setShowModalNewCategory(true)}
                />
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
            <ModalNewCategory
                onClose={() => setShowModalNewCategory(false)}
                show={showModalNewCategory}
                setCategories={setCategories}
                setCategoryId={setCategoryId}
            />
        </div>
    )
}

export default withAuth(NoteEditorPage)
