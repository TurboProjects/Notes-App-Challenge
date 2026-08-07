"use client"

import React from 'react'
import { Circle, Plus } from 'lucide-react'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem, SelectSeparator } from "@/components/ui/select"

const CREATE_CATEGORY_VALUE = "__create_new_category__"

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

export { CategorySelector, CREATE_CATEGORY_VALUE }
