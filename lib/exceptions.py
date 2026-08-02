from http import HTTPStatus


class DetailedException(Exception):
    status_code = 400

    def __init__(
        self,
        code,
        debug_message,
        status_code=None,
        payload=None,
    ):
        self.code = code
        self.debug_message = debug_message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.args = (debug_message,)

    def to_dict(self):
        return {
            "payload": self.payload or {},
            "code": self.code,
            "message": self.debug_message,
        }

    def __str__(self):
        return self.debug_message or str(self.to_dict())


class BadRequest(DetailedException):
    def __init__(
        self, message="Bad Request", code=HTTPStatus.BAD_REQUEST.value, payload=None
    ):
        super().__init__(
            code=code,
            debug_message=message,
            status_code=HTTPStatus.BAD_REQUEST.value,
            payload=payload,
        )


class Unauthorized(DetailedException):
    def __init__(
        self, message="Unauthorized", code=HTTPStatus.UNAUTHORIZED.value, payload=None
    ):
        super().__init__(
            code=code,
            debug_message=message,
            status_code=HTTPStatus.UNAUTHORIZED.value,
            payload=payload,
        )


class Forbidden(DetailedException):
    def __init__(
        self, message="Forbidden", code=HTTPStatus.FORBIDDEN.value, payload=None
    ):
        super().__init__(
            code=code,
            debug_message=message,
            status_code=HTTPStatus.FORBIDDEN.value,
            payload=payload,
        )


class NotFound(DetailedException):
    def __init__(self, message="Not Found", code=HTTPStatus.NOT_FOUND, payload=None):
        super().__init__(
            code=code,
            debug_message=message,
            status_code=HTTPStatus.NOT_FOUND,
            payload=payload,
        )
