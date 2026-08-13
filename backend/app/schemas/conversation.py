from pydantic import BaseModel, Field


class CustomerProfile(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    persona: str = Field(min_length=3, max_length=500)
    opening_line: str = Field(min_length=1, max_length=500)
    disclosed_facts: dict[str, str | int | float] = Field(default_factory=dict)
    internal_notes: list[str] = Field(default_factory=list)


class PublicCustomerProfile(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    persona: str = Field(min_length=3, max_length=500)
    opening_line: str = Field(min_length=1, max_length=500)
    disclosed_facts: dict[str, str | int | float] = Field(default_factory=dict)


class CustomerMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ConversationMessageRead(BaseModel):
    id: int
    speaker: str
    message: str
    created_at: str


class CustomerMessageResponse(BaseModel):
    learner_message: ConversationMessageRead
    customer_message: ConversationMessageRead
    ai_generated: bool
