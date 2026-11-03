from pydantic import BaseModel, ConfigDict, Field


class ChatMessageIn(BaseModel):
    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str


class InferenceRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    messages: list[ChatMessageIn]
    temperature: float = 0.7


class InferenceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    content: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = "text-embed-3"
    texts: list[str] = Field(min_length=1)


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    vectors: list[list[float]]
