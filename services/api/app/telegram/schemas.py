from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    is_bot: bool = False


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    type: str


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    message_id: int
    chat: TelegramChat
    from_: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    update_id: int
    message: TelegramMessage | None = None
