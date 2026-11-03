from pydantic import BaseModel


class SearchResults(BaseModel):
    prompts: list[dict]
    agents: list[dict]
    documents: list[dict]
