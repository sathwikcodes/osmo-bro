from abc import ABC
from uuid import UUID
from postgrest.base_request_builder import APIResponse
from lib.supabase_client import supabase, NotFoundException
from lib.exceptions import NotFound


class BaseSupabaseModel(ABC):
    """
    An abstract base class representing a table in Supabase.
    Combine this class with Pydantic BaseModel and the lib.utils.model decorator

    ### Example usage:
    ```python
    from pydantic import BaseModel
    from lib.utils import model

    @model(table_name="messages")
    class Message(BaseSupabaseModel, BaseModel):
        message_id: UUID = Field(alias="id")
        email: EmailStr
        created_at: AwareDatetime
        content: str
        room_code: str
    """

    __TABLE_NAME__: str | None = None

    @classmethod
    def get_table(cls):
        """
        Get the table from Supabase using the table name
        """
        if cls.__TABLE_NAME__ is None:
            raise NotImplementedError("Table name has not been set.")
        return supabase.table(cls.__TABLE_NAME__)

    @classmethod
    def _from_api_response(cls, response: APIResponse):
        """
        Convert API response from Supabase to instances of the class
        """
        return [cls(**row) for row in response.data]

    @classmethod
    def _fetch_single_by_key_value(cls, key: str, value: str):
        """
        Fetch a single instance by key-value pair
        """
        response = cls.get_table().select("*").eq(key, value).limit(1).execute()
        if len(response.data) > 0:
            return cls(**response.data[0])
        raise NotFound(message=f"{cls.__name__} {key}:{value} not found!")

    @classmethod
    def _fetch_by_key_value(cls, key: str, value: str):
        """
        Fetch all instances by key-value pair
        """
        response = (
            cls.get_table().select("*").eq(key, value).order("created_at").execute()
        )
        return cls._from_api_response(response=response)

    @classmethod
    def fetch_by_id(cls, id: UUID):
        """
        Fetch an instance by ID
        """
        return cls._fetch_single_by_key_value("id", str(id))

    @classmethod
    def fetch_all(cls):
        """
        Fetch all instances of the table/model/class
        """
        response = cls.get_table().select("*").execute()
        return cls._from_api_response(response=response)

    @classmethod
    def _fetch_by_key_value_similar(cls, key: str, value: str):
        """
        Fetch all instances by key-value pair
        """
        response = (
            cls.get_table()
            .select("*")
            .filter(key, "like", f"{value}%")
            .order("created_at")
            .execute()
        )
        return cls._from_api_response(response=response)

    @classmethod
    def _fetch_last_single_by_mult_key_value(
        cls, keys: list[str], values: list[str], order_by: str = "created_at"
    ):
        """
        Fetch a single instance by key-value pair
        """
        if len(keys) != len(values):
            raise ValueError("Keys and values must be the same length")
        query = cls.get_table().select("*")
        for key, val in zip(keys, values):
            query = query.ilike(key, val)
        response = query.order(order_by, desc=True).limit(1).execute()
        if len(response.data) > 0:
            return cls(**response.data[0])
        raise NotFoundException(f"{cls.__name__} {keys}:{values} not found!")
