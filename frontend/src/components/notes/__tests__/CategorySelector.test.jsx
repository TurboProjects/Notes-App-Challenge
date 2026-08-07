import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CategorySelector } from '@/components/notes/CategorySelector'

const categories = [
    { id: 1, name: 'Personal', color: '#78ABA8' },
    { id: 2, name: 'School', color: '#FCDC94' },
]

const defaultProps = {
    categories,
    categoryId: 1,
    onCategoryChange: jest.fn(),
    onCreateNew: jest.fn(),
}

const renderSelector = (overrides = {}) =>
    render(<CategorySelector {...defaultProps} {...overrides} />)

beforeEach(() => jest.clearAllMocks())

describe('CategorySelector', () => {
    it('shows the selected category in the trigger', () => {
        renderSelector()
        expect(screen.getByRole('combobox')).toHaveTextContent('Personal')
    })

    it('lists all categories plus the create option when opened', async () => {
        const user = userEvent.setup()
        renderSelector()
        await user.click(screen.getByRole('combobox'))
        expect(screen.getByRole('option', { name: /Personal/ })).toBeInTheDocument()
        expect(screen.getByRole('option', { name: /School/ })).toBeInTheDocument()
        expect(screen.getByRole('option', { name: /Create New Category/ })).toBeInTheDocument()
    })

    it('reports category selection', async () => {
        const user = userEvent.setup()
        renderSelector()
        await user.click(screen.getByRole('combobox'))
        await user.click(screen.getByRole('option', { name: /School/ }))
        expect(defaultProps.onCategoryChange).toHaveBeenCalledWith(2)
        expect(defaultProps.onCreateNew).not.toHaveBeenCalled()
    })

    it('opens the create flow without changing the selection', async () => {
        const user = userEvent.setup()
        renderSelector()
        await user.click(screen.getByRole('combobox'))
        await user.click(screen.getByRole('option', { name: /Create New Category/ }))
        expect(defaultProps.onCreateNew).toHaveBeenCalledTimes(1)
        expect(defaultProps.onCategoryChange).not.toHaveBeenCalled()
    })
})
