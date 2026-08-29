from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactSource(StrictModel):
    url: HttpUrl
    publisher: str = Field(min_length=1)
    title: str = Field(min_length=1)


class CandidateFact(StrictModel):
    claim: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class CandidateFacts(StrictModel):
    facts: list[CandidateFact] = Field(min_length=1, max_length=100)


class Fact(CandidateFact):
    id: str = Field(pattern=r"^fact_[0-9]{3,}$")


class FactSet(StrictModel):
    schema_version: int = 1
    source: FactSource
    facts: list[Fact] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self) -> "FactSet":
        ids = [fact.id for fact in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("Fact IDs must be unique")
        return self
