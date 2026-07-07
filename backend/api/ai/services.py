import logging
from typing import List
from django.conf import settings

logger = logging.getLogger(__name__)
_model = None


def chunk_text(note_title: str, note_content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple character-based chunking. Prepend the title to the content so
    searches can match title text as well.

    Returns a list of text chunks (strings).
    """
    base = "".join([note_title or "", "\n\n", note_content or ""]) if (note_title or note_content) else ""
    base = base.strip()
    if not base:
        return []

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    length = len(base)
    while start < length:
        end = start + chunk_size
        chunk = base[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            # model isn't available in this environment; leave _model as None
            _model = None
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts to float vectors using a local sentence-transformers model.

    Returns list of float lists (one per input text).
    """
    if not texts:
        return []
    model = _get_model()
    if model is not None:
        embs = model.encode(texts, convert_to_numpy=True)
        return [emb.tolist() for emb in embs]

    # Fallback: deterministic lightweight embedding when sentence-transformers
    # isn't installed. This produces a pseudo-embedding of dimension 768 so
    # the system can operate in constrained environments (NOT a replacement
    # for real semantic embeddings).
    import hashlib
    import struct

    dim = 768
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        # expand hash into dim floats by repeating and interpreting bytes
        floats = []
        repeat = (dim * 4 + len(h) - 1) // len(h)
        data = h * repeat
        for i in range(dim):
            # take 4 bytes -> uint32 -> normalize to [0,1)
            chunk = data[i * 4 : i * 4 + 4]
            val = struct.unpack("I", chunk)[0]
            floats.append((val % 10000) / 10000.0)
        out.append(floats)
    return out


def llm_summarize(query: str, contexts: List[dict], model: str | None = None) -> dict:
    """Call an LLM to produce a concise answer with inline citations.

    `contexts` must be a list of dicts: {"note_id": int, "chunk_index": int, "text": str}.
    Returns a dict with keys: `answer` (str) and `sources` (list of source dicts).

    The prompt asks the model to return JSON. We attempt to parse it and fall
    back to a simple joined answer if parsing or API access fails.
    """
    if not contexts:
        return {"answer": "", "sources": []}

    model = model or getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")
    api_key = getattr(settings, "OPENAI_API_KEY", None)

    def _trim_text(t: str, max_chars: int = 1000) -> str:
        if len(t) <= max_chars:
            return t
        # keep start and end to preserve context
        head = t[: max_chars // 2].rsplit("\n", 1)[0]
        tail = t[-(max_chars // 2) :].split("\n", 1)[-1]
        return head + "\n...\n" + tail

    # trim contexts to avoid excessive token usage
    contexts = [
        {**c, "text": _trim_text(c.get("text", ""), max_chars=800)} for c in contexts
    ]

    # Prepare a deterministic fallback response if OpenAI isn't configured
    if api_key is None:
        logger.warning("OPENAI_API_KEY not set; returning concatenated chunks instead of LLM summary.")
        joined = "\n\n".join([c["text"] for c in contexts])
        sources = [
            {"note_id": c["note_id"], "chunk_index": c["chunk_index"], "text": c["text"]}
            for c in contexts
        ]
        return {"answer": joined, "sources": sources}

    try:
        import json
        import httpx
        from openai import OpenAI

        # Use an explicit httpx client so the OpenAI lib does not pass 'proxies'
        # (which can cause TypeError with older openai/httpx combinations in Docker).
        http_client = httpx.Client(proxy=None)
        client = OpenAI(api_key=api_key, http_client=http_client)

        # Few-shot examples to guide JSON structure and citation style.
        few_shot = (
            "Example 1:\n"
            "Query: What are the tasks for today?\n"
            "Context 1 [note:6#chunk:0]: To-dos for today\\n\\n- Buy milk\\n- Call Bob\\n- Finish report\n\n"
            "Response JSON:\n"
            '{"answer":"- Buy milk; - Call Bob; - Finish report [note:6#chunk:0]", "sources":[{"note_id":6,"chunk_index":0,"excerpt":"- Buy milk\\n- Call Bob\\n- Finish report"}]}'
            "\n---\n"
        )

        system_instructions = (
            "You are a concise assistant that answers user questions using the provided note chunks as context. "
            "Write in clear, natural language (e.g. short paragraphs or bullet points). Do NOT simply concatenate or list raw snippets. "
            "For 'summarize' requests, synthesize a coherent summary that captures main themes and key points. "
            "Produce a short, factual answer that directly addresses the user's query. "
            "When you use information from a chunk, add an inline citation immediately after the clause in the form "
            "[note:{note_id}#chunk:{chunk_index}]. Do NOT invent sources. "
            "Return a JSON object with two keys: `answer` (string) and `sources` (array). "
            "Each source object must contain `note_id`, `chunk_index`, and a short `excerpt` (1-2 sentences) showing the used text. "
            "Respond only with the JSON object and nothing else."
        )

        # Build the message payload
        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": few_shot},
            {"role": "user", "content": f"Query: {query}"},
        ]

        # append numbered contexts to the user messages with explicit metadata
        for i, c in enumerate(contexts, start=1):
            meta = f"[note:{c['note_id']}#chunk:{c['chunk_index']}]"
            messages.append({"role": "user", "content": f"Context {i} {meta}: {c['text']}"})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
        )

        content = (resp.choices[0].message.content or "").strip()
        try:
            parsed = json.loads(content)
            # Validate expected keys minimally
            if isinstance(parsed, dict) and "answer" in parsed and "sources" in parsed:
                return parsed
        except Exception:
            # Not valid JSON; fall through to best-effort parsing below
            pass

        # Fallback: try to extract answer section heuristically
        return {"answer": content, "sources": []}
    except Exception as e:
        logger.exception("OpenAI call failed; returning concatenated chunks: %s", e)
        # On any API/parsing error, fallback to joined contexts
        joined = "\n\n".join([c["text"] for c in contexts])
        sources = [
            {"note_id": c["note_id"], "chunk_index": c["chunk_index"], "text": c["text"]}
            for c in contexts
        ]
        return {"answer": joined, "sources": sources}
