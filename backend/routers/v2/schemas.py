"""Base de los esquemas de v2: snake_case sin alias [Q-2]."""

from pydantic import BaseModel, ConfigDict


class V2Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)
