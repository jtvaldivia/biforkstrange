"""Historias: un documento por partida."""

from typing import Protocol

from supabase import Client

from app.story.model import Story


class StoryRepository(Protocol):
    def get(self, story_id: str) -> Story | None: ...
    def save(self, story: Story) -> Story: ...


class InMemoryStoryRepository:
    def __init__(self):
        self._docs: dict[str, dict] = {}

    def get(self, story_id):
        doc = self._docs.get(story_id)
        return Story.model_validate(doc) if doc else None

    def save(self, story):
        self._docs[story.id] = story.model_dump()
        return story


class SupabaseStoryRepository:
    table = "stories"

    def __init__(self, client: Client):
        self.client = client

    def get(self, story_id):
        rows = self.client.table(self.table).select("doc").eq("id", story_id).limit(1).execute().data
        return Story.model_validate(rows[0]["doc"]) if rows else None

    def save(self, story):
        self.client.table(self.table).upsert(
            {"id": story.id, "profile_id": story.profile_id, "doc": story.model_dump(mode="json")}
        ).execute()
        return story
