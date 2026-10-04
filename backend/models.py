from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    product_id: str
    name: str
    price: float
    image_url: str
    description: str


class ProductInfo(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    colors: str
    garment_type: str


class StockLine(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class StockLookup(BaseModel):
    product_id: str
    product_name: str
    requested_size: str | None = None
    lines: list[StockLine]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)
    user_id: int | None = None
    page_context: dict[str, str] = Field(default_factory=dict)


class CustomerContext(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: str


class ChatReply(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
