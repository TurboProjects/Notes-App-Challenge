"""Unit tests for the SSE stream generator's delta path — fake broadcaster,
patched snapshot, no DB.

ADR-0007: `kind: delta` payloads are forwarded as `event: delta` frames
WITHOUT a re-snapshot; `kind: status` (or unknown kinds) re-snapshot and
terminate when the question is terminal.
"""

import asyncio
from unittest import mock

from django.test import SimpleTestCase

from api.notes.domain.entities import Answer
from api.notes.domain.entities import Question
from api.notes.domain.enums import QuestionStatus
from api.notes.infrastructure.api import sse


class FakeBroadcaster:
    def __init__(self, payloads):
        self._payloads = payloads
        self.unsubscribed = False

    async def subscribe(self, question_id):
        queue = asyncio.Queue()
        for payload in self._payloads:
            queue.put_nowait(payload)
        return queue

    async def unsubscribe(self, question_id, queue):
        self.unsubscribed = True


def _pending_question():
    return Question(id=1, user_id="u-1", text="what?")


def _terminal_question():
    return Question(
        id=1,
        user_id="u-1",
        text="what?",
        status=QuestionStatus.SUCCESS,
        answer=Answer(text="Hello!", citations=[]),
    )


class QuestionStreamDeltaTests(SimpleTestCase):
    def _collect(self, payloads, snapshots):
        broadcaster = FakeBroadcaster(payloads)

        async def run():
            frames = []
            with (
                mock.patch.object(sse, "broadcaster", broadcaster),
                mock.patch.object(sse, "_snapshot", side_effect=snapshots) as snap,
            ):
                async for frame in sse._stream(1, "u-1"):
                    frames.append(frame)
            return frames, snap

        frames, snap = asyncio.run(run())
        return frames, snap, broadcaster

    def test_delta_frames_forward_without_resnapshot(self):
        payloads = [
            {"kind": "delta", "question_id": 1, "seq": 1, "text": "Hel"},
            {"kind": "delta", "question_id": 1, "seq": 2, "text": "lo!"},
            {"kind": "status", "question_id": 1},
        ]
        frames, snap, broadcaster = self._collect(
            payloads,
            snapshots=[_pending_question(), _terminal_question()],
        )

        self.assertEqual(len(frames), 4)
        self.assertIn("event: status", frames[0])  # initial PENDING snapshot
        self.assertIn("event: delta", frames[1])
        self.assertIn("id: 1", frames[1])
        self.assertIn('"text": "Hel"', frames[1])
        self.assertIn("event: delta", frames[2])
        self.assertIn('"seq": 2', frames[2])
        self.assertIn("event: status", frames[3])  # terminal
        self.assertIn("Hello!", frames[3])
        # Deltas never hit the DB: one snapshot on connect + one on status.
        self.assertEqual(snap.call_count, 2)
        self.assertTrue(broadcaster.unsubscribed)

    def test_unknown_kind_degrades_to_resnapshot(self):
        frames, snap, _ = self._collect(
            payloads=[{"question_id": 1}],  # legacy payload, no kind
            snapshots=[_pending_question(), _terminal_question()],
        )

        self.assertEqual(len(frames), 2)
        self.assertIn("event: status", frames[1])
        self.assertEqual(snap.call_count, 2)

    def test_terminal_on_connect_closes_without_subscribing(self):
        frames, snap, broadcaster = self._collect(
            payloads=[],
            snapshots=[_terminal_question()],
        )

        self.assertEqual(len(frames), 1)
        self.assertIn("event: status", frames[0])
        self.assertEqual(snap.call_count, 1)
        self.assertFalse(broadcaster.unsubscribed)  # never subscribed
