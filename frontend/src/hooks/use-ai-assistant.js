'use client';

import { useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthProvider';
import { aiAssistantApi } from '@/lib/api';

export function useAiAssistant() {
    const { getToken } = useAuth();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    const askAssistant = useCallback(async (query) => {
        if (!query.trim()) {
            setError('Please enter a question');
            return null;
        }

        setIsLoading(true);
        setError(null);
        setResult(null);

        try {
            const token = getToken();
            if (!token) {
                throw new Error('Not authenticated');
            }

            const response = await aiAssistantApi.query(query, token);
            setResult(response);
            return response;
        } catch (error) {
            setError(error.message || 'Something went wrong');
            return null;
        } finally {
            setIsLoading(false);
        }
    }, [getToken]);

    const reset = useCallback(() => {
        setResult(null);
        setError(null);
    }, []);

    return { askAssistant, isLoading, error, result, reset };
}
