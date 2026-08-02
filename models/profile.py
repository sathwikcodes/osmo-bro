from functools import lru_cache
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, PastDatetime, Field
from models.base import BaseSupabaseModel
from lib.utils import model


@model(table_name="profiles")
class Profile(BaseModel, BaseSupabaseModel):
    """
    This class represents the "profiles" table in the database.
    Each row/instance in the table represents the profile of a user who has signed up on the platform.
    The class provides methods to fetch a profile by email, and to automatically generate a username from the email.
    """

    profile_id: UUID = Field(alias="id")
    display_name: str
    email: EmailStr
    is_admin: bool = Field(default=False)
    created_at: PastDatetime
    updated_at: Optional[PastDatetime]

    def __hash__(self) -> int:
        return hash(self.email)

    @property
    def username(self):
        return self.email.split("@")[0]

    @classmethod
    @lru_cache
    def fetch_by_email(cls, email: str):
        return cls._fetch_single_by_key_value("email", email)
