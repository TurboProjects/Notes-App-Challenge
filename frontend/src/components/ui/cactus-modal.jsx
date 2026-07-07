"use client";
import React, { useEffect, useRef, useState } from "react";
import { Textarea } from './textarea'
import axios from "axios";
import { useAuth } from "@/context/AuthProvider";

export default function CactusModal({ open, onClose }) {
  const ref = useRef(null);
  const { getToken } = useAuth();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const token = getToken();
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/ai/query/`,
        { query, top_k: 5 },
        { headers: token ? { Authorization: `Token ${token}` } : {} }
      );
      setResponse(res.data.answer ?? "");
    } catch (error) {
      console.error("Error generating summary:", error);
      setResponse("An error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && ref.current) {
      // focus the textarea
      try { ref.current.focus() } catch (e) {}
    }
  }, [open])

  if (!open) return null

  return (
    <div className="cactus-modal-overlay" onClick={onClose}>
      <div className="cactus-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <Textarea
          ref={ref}
          placeholder="Ask anything you need to know..."
          className="cactus-modal-textarea"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          className="cactus-modal-send"
          aria-label="Send question"
          onClick={handleSend}
          disabled={loading}
        >
          {loading ? "..." : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 19V6" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M5 12l7-7 7 7" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </button>
        {response && <div className="cactus-modal-response">{response}</div>}
      </div>
    </div>
  )
}
