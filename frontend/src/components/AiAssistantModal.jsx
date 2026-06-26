'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAiAssistant } from '@/hooks/use-ai-assistant';
import { Button } from '@/components/ui/button';
import { Loader2, Send, X, FileText } from 'lucide-react';

export function AiAssistantModal({ isOpen, onClose }) {
    const [query, setQuery] = useState('');
    const { askAssistant, isLoading, error, result, reset } = useAiAssistant();
    const router = useRouter();

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (query.trim()) await askAssistant(query);
    };

    const handleClose = () => {
        setQuery('');
        reset();
        onClose();
    };

    const goToNote = (noteId) => {
        handleClose();
        router.push(`/notes/editor/${noteId}`);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-[#faf1e4] rounded-2xl shadow-xl w-full max-w-2xl mx-4 overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b border-[#e5d9c9]">
                    <h2 className="text-lg font-semibold text-[#5c4033]">AI Assistant</h2>
                    <button onClick={handleClose} className="p-1 rounded-full hover:bg-[#e5d9c9]">
                        <X className="w-5 h-5 text-[#5c4033]" />
                    </button>
                </div>

                <div className="p-4 max-h-[60vh] overflow-y-auto">
                    <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Ask anything you need to know..."
                            className="flex-1 px-4 py-3 rounded-xl bg-white border border-[#e5d9c9] focus:outline-none focus:ring-2 focus:ring-[#95715e] text-[#5c4033]"
                            disabled={isLoading}
                        />
                        <Button
                            type="submit"
                            disabled={isLoading || !query.trim()}
                            className="bg-[#95715e] hover:bg-[#7d5f4e] text-white rounded-xl px-4"
                        >
                            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                        </Button>
                    </form>

                    {error && (
                        <div className="p-3 mb-4 bg-red-100 text-red-700 rounded-xl">{error}</div>
                    )}

                    {result && (
                        <div className="space-y-4">
                            <div className="p-4 bg-white rounded-xl border border-[#e5d9c9]">
                                <p className="text-[#5c4033] whitespace-pre-wrap">{result.response}</p>
                            </div>

                            {result.references?.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-semibold text-[#95715e] mb-2">Referenced Notes:</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {result.references.map((reference) => (
                                            <button
                                                key={reference.note_id}
                                                onClick={() => goToNote(reference.note_id)}
                                                className="flex items-center gap-2 px-3 py-2 bg-white border border-[#e5d9c9] rounded-lg hover:bg-[#e5d9c9]"
                                            >
                                                <FileText className="w-4 h-4 text-[#95715e]" />
                                                <span className="text-sm text-[#5c4033]">{reference.note_title}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {isLoading && (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-8 h-8 animate-spin text-[#95715e]" />
                            <span className="ml-2 text-[#95715e]">Searching your notes...</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
