import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import { NewCategoryDialog, CategoryColors } from '@/components/notes/NewCategoryDialog'

const defaultProps = {
    open: true,
    onClose: jest.fn(),
    name: '',
    onNameChange: jest.fn(),
    color: CategoryColors[0],
    onColorChange: jest.fn(),
    onSubmit: jest.fn(),
    isCreating: false,
}

const renderDialog = (overrides = {}) =>
    render(<NewCategoryDialog {...defaultProps} {...overrides} />)

beforeEach(() => jest.clearAllMocks())

describe('NewCategoryDialog', () => {
    it('renders nothing when closed', () => {
        renderDialog({ open: false })
        expect(screen.queryByText('Create New Category')).not.toBeInTheDocument()
    })

    it('renders title, name input, color palette and submit button when open', () => {
        renderDialog()
        expect(screen.getByRole('heading', { name: 'Create New Category' })).toBeInTheDocument()
        expect(screen.getByPlaceholderText('Enter name')).toBeInTheDocument()
        CategoryColors.forEach(color => {
            expect(screen.getByRole('button', { name: `Select color ${color}` })).toBeInTheDocument()
        })
        expect(screen.getByRole('button', { name: 'Create Category' })).toBeInTheDocument()
    })

    it('reports name changes', () => {
        renderDialog()
        fireEvent.change(screen.getByPlaceholderText('Enter name'), { target: { value: 'Drama' } })
        expect(defaultProps.onNameChange).toHaveBeenCalledWith('Drama')
    })

    it('reports color selection and marks the active swatch', () => {
        renderDialog({ color: CategoryColors[1] })
        expect(screen.getByRole('button', { name: `Select color ${CategoryColors[1]}` }))
            .toHaveAttribute('aria-pressed', 'true')
        fireEvent.click(screen.getByRole('button', { name: `Select color ${CategoryColors[4]}` }))
        expect(defaultProps.onColorChange).toHaveBeenCalledWith(CategoryColors[4])
    })

    it('disables submit while the name is empty or whitespace', () => {
        renderDialog({ name: '   ' })
        expect(screen.getByRole('button', { name: 'Create Category' })).toBeDisabled()
    })

    it('submits when a valid name is set', () => {
        renderDialog({ name: 'Drama' })
        const submit = screen.getByRole('button', { name: 'Create Category' })
        expect(submit).toBeEnabled()
        fireEvent.click(submit)
        expect(defaultProps.onSubmit).toHaveBeenCalledTimes(1)
    })

    it('shows a loading state and blocks submit while creating', () => {
        renderDialog({ name: 'Drama', isCreating: true })
        expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled()
    })

    it('closes via the X button', () => {
        renderDialog()
        fireEvent.click(screen.getByRole('button', { name: 'Close' }))
        expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })

    it('closes when clicking the overlay but not the dialog itself', () => {
        const { container } = renderDialog()
        fireEvent.click(screen.getByRole('heading', { name: 'Create New Category' }))
        expect(defaultProps.onClose).not.toHaveBeenCalled()
        fireEvent.click(container.firstChild)
        expect(defaultProps.onClose).toHaveBeenCalledTimes(1)
    })
})
