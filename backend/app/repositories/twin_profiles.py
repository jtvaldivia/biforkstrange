"""Un documento por persona, con control de versión: una pestaña vieja no pisa datos más nuevos."""

from datetime import datetime, timezone
from typing import Protocol

from supabase import Client

from app.twin.profile import TwinProfile


class StaleVersionError(Exception):
    def __init__(self, current: TwinProfile):
        super().__init__("La versión guardada es más nueva")
        self.current = current


class TwinProfileRepository(Protocol):
    def get(self, profile_id: str) -> TwinProfile | None: ...
    def create(self, profile: TwinProfile) -> TwinProfile: ...
    def save(self, profile: TwinProfile, expected_version: int) -> TwinProfile:
        """Guarda con version = expected_version + 1. StaleVersionError si la remota no es expected_version."""
        ...


class InMemoryTwinProfileRepository:
    def __init__(self):
        self._docs: dict[str, dict] = {}

    def get(self, profile_id):
        doc = self._docs.get(profile_id)
        return TwinProfile.model_validate(doc) if doc else None

    def create(self, profile):
        self._docs[profile.id] = profile.model_dump()
        return profile

    def save(self, profile, expected_version):
        current = self.get(profile.id)
        if current is None or current.version != expected_version:
            raise StaleVersionError(current or profile)
        saved = profile.model_copy(update={"version": expected_version + 1})
        self._docs[profile.id] = saved.model_dump()
        return saved


class SupabaseTwinProfileRepository:
    table = "twin_profiles"

    def __init__(self, client: Client):
        self.client = client

    def get(self, profile_id):
        rows = self.client.table(self.table).select("doc").eq("id", profile_id).limit(1).execute().data
        return TwinProfile.model_validate(rows[0]["doc"]) if rows else None

    def create(self, profile):
        self.client.table(self.table).insert(
            {"id": profile.id, "version": profile.version, "doc": profile.model_dump(mode="json")}
        ).execute()
        return profile

    def save(self, profile, expected_version):
        saved = profile.model_copy(update={"version": expected_version + 1})
        rows = (
            self.client.table(self.table)
            .update({"version": saved.version, "doc": saved.model_dump(mode="json"), "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", profile.id)
            .eq("version", expected_version)  # escritura condicional: si otra pestaña escribió antes, no toca nada
            .execute()
            .data
        )
        if not rows:
            raise StaleVersionError(self.get(profile.id) or profile)
        return saved
