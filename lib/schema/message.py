from pydantic import BaseModel, EmailStr


class CreateMessage(BaseModel):
    content: str
    email: EmailStr
    role: str
    room_code: str
    is_public: bool = True
    is_context: bool = True
    has_image: bool = False
    image_url: str | None = None
    image_analysis: str | None = None
