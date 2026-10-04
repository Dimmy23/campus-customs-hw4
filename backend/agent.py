"""PydanticAI agent with a deterministic local fallback for offline development."""

import os
from pathlib import Path
from models import ChatReply, CustomerContext
from tools import product_by_id, product_info, search_products, stock_lookup
from audit import record

PROMPT = (Path(__file__).parent / "prompts" / "prompt.md").read_text()

try:
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider
except ImportError:  # Allows catalogue/auth work to run before dependencies are installed.
    Agent = None


def _env_file_value(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"\'')
    return ""


def _fallback(message: str, page_context: dict[str, str] | None = None) -> ChatReply:
    lowered = message.lower()
    context_id = (page_context or {}).get("product_id")
    if context_id and any(word in lowered for word in ("pink", "color", "price", "cost", "stock", "available", "size")):
        record("product_by_id", {"product_id": context_id}, "context lookup")
        exact = product_by_id(context_id)
        if exact:
            return ChatReply(reply=f"{exact.name} is listed at ${exact.price:.2f}. Its catalogue colors are {exact.colors}. For exact size availability, ask me about a size and I’ll check the inventory.")
    cards = search_products(message)
    record("search_products", {"query": message[:80], "limit": 4}, {"count": len(cards)})
    if any(word in lowered for word in ("price", "cost", "how much")) and cards:
        prices = "; ".join(f"{card.name}: ${card.price:.2f}" for card in cards[:3])
        return ChatReply(reply=f"Here are the catalogue prices: {prices}.", products=cards)
    if any(word in lowered for word in ("stock", "available", "availability", "size")) and cards:
        details = []
        for card in cards[:3]:
            stock = stock_lookup(card.product_id)
            record("stock_lookup", {"product_id": card.product_id}, {"lines": len(stock.lines) if stock else 0})
            if stock and stock.lines:
                details.append(f"{card.name}: " + ", ".join(f"{line.size} ({line.quantity} in stock)" if line.in_stock else f"{line.size} (out of stock)" for line in stock.lines))
            else:
                details.append(f"{card.name}: no size-level stock record")
        return ChatReply(reply="Stock from the database: " + "; ".join(details) + ".", products=cards)
    if cards:
        names = ", ".join(card.name for card in cards[:3])
        return ChatReply(reply=f"Here are a few Yale merchandise options that match your search: {names}.", products=cards)
    return ChatReply(reply="I can help you find Yale apparel, accessories, and gifts. Try asking for a hoodie, hat, crewneck, school, color, or price range.")


async def generate_reply(message: str, history: list[dict[str, str]] | None = None, customer: CustomerContext | None = None, page_context: dict[str, str] | None = None) -> ChatReply:
    record("agent_loop", {"message_length": len(message), "has_customer": bool(customer), "has_page_context": bool(page_context)}, None, "started")
    api_key = _env_file_value("PORTKEY_API_KEY")
    if Agent is None or not api_key:
        reply = _fallback(message, page_context)
        record("agent_loop", None, {"product_count": len(reply.products)}, "fallback_complete")
        return reply
    provider = OpenAIProvider(base_url="https://api.portkey.ai/v1", api_key=api_key)
    model = OpenAIModel("gpt-5.6-luna", provider=provider)
    context = f"\nCustomer context: {customer.first_name} {customer.last_name} ({customer.email})." if customer else "\nCustomer is a guest; do not assume an identity."
    page = f"\nCurrent page context: {page_context}." if page_context else ""
    agent = Agent(model, output_type=ChatReply, system_prompt=PROMPT + context + page)
    agent.tool_plain(product_info)
    agent.tool_plain(product_by_id)
    agent.tool_plain(stock_lookup)
    agent.tool_plain(search_products)
    # The frontend history is retained for the API contract; PydanticAI history
    # conversion can be added when persistent conversation state is introduced.
    result = await agent.run(message)
    record("agent_loop", None, {"product_count": len(result.output.products)}, "model_complete")
    return result.output
