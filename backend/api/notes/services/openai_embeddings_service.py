from typing import List
from openai import OpenAI
from pydantic import BaseModel


class NoteReference(BaseModel):
    note_id: int
    note_title: str


class AssistantResponse(BaseModel):
    response: str
    references: List[NoteReference]


class OpenAIService:
    EMBEDDING_MODEL = "text-embedding-3-small"
    CHAT_MODEL = "gpt-4o-mini"
    
    def __init__(self):
        self.client = OpenAI()

    def get_embeddings(self, texts):
        response = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=texts,
            dimensions=1024,
        )
        return [item.embedding for item in response.data]

    def get_embedding(self, text):
        response = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
            dimensions=1024,
        )
        return response.data[0].embedding

    def ask(self, query, context):
        context_formatted = "\n\n".join([
            f"[Note ID: {note['note_id']}, Title: {note['note_title']}]\n{note['content']}"
            for note in context
        ])

        system_message = (
            "You are a helpful assistant that answers questions based on the user's notes. "
            "Use ONLY the provided notes as context. If the information is not in the notes, say so. "
            "Always cite which notes you used by including their note_id and note_title in references. "
            "Do NOT use markdown. Use plain text, dashes (-) or numbers for lists."
        )

        user_message = f"Context:\n{context_formatted}\n\nQuestion: {query}"

        response = self.client.beta.chat.completions.parse(
            model=self.CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            response_format=AssistantResponse,
        )
        return response.choices[0].message.parsed
