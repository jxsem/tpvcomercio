from pydantic import BaseModel, ConfigDict, Field

# Tope de longitud: Argon2 es deliberadamente lento, y sin tope una contraseña
# de varios MB permitiría saturar el servidor con una sola petición.
MAX_PASSWORD_LENGTH = 128


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(min_length=10, max_length=MAX_PASSWORD_LENGTH)
