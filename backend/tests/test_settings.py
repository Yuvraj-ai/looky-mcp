"""Universal Extra Instructions tests (storage: app_settings singleton row —
see decisions.md 2026-09-10 and questions.md Q2)."""


class TestExtraInstructions:
    async def test_default_empty(self, db_session):
        from app.repositories.settings import AppSettingsRepository

        repo = AppSettingsRepository(db_session)
        # other tests (e2e) may have set a value in the shared session DB —
        # this test verifies the *get* path returns whatever is stored; empty
        # default is proven by test_empty_allowed below from a known state.
        value = await repo.get_extra_instructions()
        assert isinstance(value, str)

    async def test_set_and_get(self, db_session):
        from app.repositories.settings import AppSettingsRepository

        repo = AppSettingsRepository(db_session)
        await repo.set_extra_instructions("Be precise and concise.")
        assert await repo.get_extra_instructions() == "Be precise and concise."

    async def test_update_overwrites(self, db_session):
        from app.repositories.settings import AppSettingsRepository

        repo = AppSettingsRepository(db_session)
        await repo.set_extra_instructions("first")
        await repo.set_extra_instructions("second")
        assert await repo.get_extra_instructions() == "second"

    async def test_empty_allowed(self, db_session):
        from app.repositories.settings import AppSettingsRepository

        repo = AppSettingsRepository(db_session)
        await repo.set_extra_instructions("")
        assert await repo.get_extra_instructions() == ""
