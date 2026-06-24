"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Circle, X, Plus } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/context/AuthProvider';
import withAuth from '@/hoc/withAuth';
import { formatDate } from '@/lib/utils';


const CategorySelector = ({ categories, categoryId, onCategoryChange, setShowModal }) => {
    const openModal = () => {
        setShowModal(true)
    }

    return (
        <Select value={categoryId} onValueChange={onCategoryChange}>
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
                <button className="w-full flex flex-row items-center border-t border-[#957139] p-2" onClick={() => openModal()}> <Plus className="h-4 w-4 mx-2" /> <span className="text-sm">Create New Category</span></button>
            </SelectContent>
        </Select>
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

const Header = ({ categories, categoryId, onCategoryChange, setShowModal }) => (
    <header className="flex justify-between items-center mb-4">
        <CategorySelector categories={categories} categoryId={categoryId} onCategoryChange={onCategoryChange} setShowModal={setShowModal} />
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
    const [showModal, setShowModal] = useState(false)
    const [name, setName] = useState("")
    const params = useParams()
    const noteId = params.noteId

    const handleOpenModal = (value) => {
        console.log("handleOpenModal", value)
        setShowModal(value)
    }

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
    const [categoryColorForCreate, setCategoryColorForCreate] = useState(1)

    // colors: 217 146 95, 243 215 141, 195 200 151, 124 161 158, 232 149 149, 179 163 201
    const selectColors = [
        { id: 1, color: '#d9925f'},
        { id: 2, color: '#f3d88d'},
        { id: 3, color: '#c3c897'},
        { id: 4, color: '#7ca19e'},
        { id: 5, color: '#e89595'},
        { id: 6, color: '#b3a3c9'},
    ]

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

    const handleCreateCategory = async () => {
        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/categories/`, {
            method: 'POST',
            headers: {
              'Authorization': `Token ${getToken()}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              "name": name,
              "color": selectColors.find(color => color.id === categoryColorForCreate).color,
            }),
          })
          if (response.ok) {
              const data = await response.json()
              console.log('Category created successfully', data)
              handleOpenModal(false)
              setCategories([{
                  "id": data.id,
                  "name": data.name,
                  "color": data.color,
                  "note_count": data.note_count
              }, ...categories])
              setCategoryId(data.id)
              setCategoryColorForCreate(1)
          } else {
              console.error('Failed to create category')
          }
        } catch (error) {
          console.error('Error creating category:', error)
        }
    }

    const renderCategorySelector = () => {
        return (
            <div className="flex justify-between w-full">
                {selectColors.map((color) => (
                    <button key={color.id} onClick={() => setCategoryColorForCreate(color.id)}>
                        <Circle className="w-6 h-6 text-[#826638]" fill={color.color} strokeWidth={categoryColorForCreate === color.id ? 2 : 0} />
                    </button>
                ))}
            </div>
        )
    }

    // render
    return (
        <div className="bg-[#faf1e3] h-screen flex flex-col">
            <div className="px-4 md:px-8 lg:px-12 pt-4 md:pt-8 lg:pt-12">
                <Header categories={categories} categoryId={categoryId} onCategoryChange={handleCategoryIdChange} setShowModal={handleOpenModal} />
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
            {showModal &&
                <div className="fixed inset-0 flex items-center justify-center bg-black/20">
                    <div className="flex flex-col bg-[#f7efdf] rounded-lg w-[30rem] shadow-lg">
                        <div className="flex justify-end mt-2 mr-2 font-light">
                            <button onClick={() => setShowModal(false)}><X className="h-4 w-4"/></button>
                        </div>
                        <div className="px-6 pb-6 flex flex-col">
                            <label className="font-bold mb-2 text-lg">Create New Category</label>
                            <input placeholder="Enter name" className="my-1 py-3 px-3 border border-[#826638] rounded-md bg-[#f7efdf]" onInput={(e) => setName(e.target.value)}></input>
                            <div className="flex flex-row my-1 py-3 px-3 border border-[#826638] rounded-md bg-[#f7efdf]">
                                {renderCategorySelector()}
                            </div>
                            <div className="flex justify-end text-white mt-2">
                                <button className="bg-[#826638] rounded-lg right-0 w-1/2 font-light px-4 py-2" onClick={() => handleCreateCategory()}> Create Category</button>
                            </div>
                        </div>
                    </div>
                </div>
            }
        </div>
    )
}

export default withAuth(NoteEditorPage)
