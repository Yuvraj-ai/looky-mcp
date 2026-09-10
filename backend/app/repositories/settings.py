"""App settings repository: Universal Extra Instructions singleton
(one global row — Decision #1/#2: one universal prompt, describe-only)."""

from app.db import models

EXTRA_INSTRUCTIONS_KEY = "universal_extra_instructions"


class AppSettingsRepository:
    def __init__(self, session):
        self.session = session

    async def get_extra_instructions(self) -> str:
        row = await self.session.get(models.AppSettings, EXTRA_INSTRUCTIONS_KEY)
        return row.value if row is not None else ""

    async def set_extra_instructions(self, value: str) -> None:
        row = await self.session.get(models.AppSettings, EXTRA_INSTRUCTIONS_KEY)
        if row is None:
            row = models.AppSettings(key=EXTRA_INSTRUCTIONS_KEY, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.commit()
