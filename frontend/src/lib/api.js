const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

async function fetchApi(endpoint, token, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Token ${token}`,
            ...options.headers,
        },
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Request failed');
    }

    return response.json();
}

export const aiAssistantApi = {
    query(query, token) {
        return fetchApi('/api/v1/ai_assistant/', token, {
            method: 'POST',
            body: JSON.stringify({ query }),
        });
    },
};

export const notesApi = {
    getAll(token, categoryId = null) {
        const queryString = categoryId ? `?category_id=${categoryId}` : '';
        return fetchApi(`/api/v1/notes/${queryString}`, token);
    },
    
    getById(noteId, token) {
        return fetchApi(`/api/v1/notes/${noteId}/`, token);
    },
    
    create(data, token) {
        return fetchApi('/api/v1/notes/', token, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
    
    update(noteId, data, token) {
        return fetchApi(`/api/v1/notes/${noteId}/`, token, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },
    
    delete(noteId, token) {
        return fetchApi(`/api/v1/notes/${noteId}/`, token, {
            method: 'DELETE',
        });
    },
};

export const categoriesApi = {
    getAll(token) {
        return fetchApi('/api/v1/categories/', token);
    },
};
