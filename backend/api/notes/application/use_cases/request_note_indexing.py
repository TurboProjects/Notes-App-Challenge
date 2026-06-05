from api.notes.domain.ports import EventOutbox
from api.notes.domain.ports import NoteIndexRepository
from api.notes.domain.value_objects import sha256_of

NOTE_EMBED_TOPIC = "note.embed.requested"


class RequestNoteIndexingUseCase:
    """
    Debounced re-index trigger, invoked by the note controller after a note
    is created or updated.

    Recomputes the content hash, emits `note.embed.requested` ONLY when the
    content changed. Runs inside the request transaction, so
    the hash update and the outbox event commit or roll back together with the
    note.
    """

    def __init__(self, *, notes_index: NoteIndexRepository, outbox: EventOutbox):
        self._notes_index = notes_index
        self._outbox = outbox

    def execute(self, *, note_id: int) -> bool:
        """Returns True if a re-index was requested, False if debounced."""
        content, stored_hash = self._notes_index.get_content_and_hash(note_id=note_id)
        new_hash = sha256_of(content or "")
        if new_hash == stored_hash:
            return False

        self._notes_index.set_content_hash(note_id=note_id, content_hash=new_hash)
        self._outbox.emit(
            topic=NOTE_EMBED_TOPIC,
            correlation_id=str(note_id),
            payload={
                "schema_version": 1,
                "note_id": note_id,
                "content_hash": new_hash,
            },
        )
        return True
