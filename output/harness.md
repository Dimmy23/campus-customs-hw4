# Problem 2 — Database Analysis

Database analyzed: `../data/campus_customs.db`

The database contains four application tables. `sqlite_sequence` is an internal SQLite bookkeeping table and is not part of the shop’s business data.

## `catalogue` — product information

| Field | Type | Key/constraint | Why it matters |
|---|---|---|---|
| `product_id` | TEXT | Primary key | Uniquely identifies a product for catalogue links, inventory joins, and chatbot recommendations. |
| `name` | TEXT | NOT NULL | The customer-facing product name used in cards, search results, and chat replies. |
| `garment_type` | TEXT | NOT NULL | Supports category filters such as hoodie, crewneck, or T-shirt. |
| `description` | TEXT | NOT NULL | Gives the shop and chatbot factual product details to display or summarize. |
| `colors` | TEXT | NOT NULL | Supports color browsing and preference-based recommendations. |
| `search_tags` | TEXT | NOT NULL | Provides searchable keywords for matching natural-language shopping requests. |
| `image_file_path` | TEXT | NOT NULL | Connects each database product to its image in the shop UI. |
| `price` | REAL | NOT NULL | Displays the product price and lets the chatbot answer price questions. |

## `inventory` — size-level availability

| Field | Type | Key/constraint | Why it matters |
|---|---|---|---|
| `id` | INTEGER | Primary key | Identifies an individual inventory record for updates and database operations. |
| `product_id` | TEXT | NOT NULL; foreign key to `catalogue.product_id` | Connects a size quantity to the correct product. |
| `size` | TEXT | NOT NULL | Shows which sizes customers can select or ask the chatbot about. |
| `quantity` | INTEGER | NOT NULL | Determines whether a size is in stock and prevents unsupported availability claims. |

## `users` — customer accounts

| Field | Type | Key/constraint | Why it matters |
|---|---|---|---|
| `id` | INTEGER | Primary key | Identifies a customer account for chat history and account operations. |
| `name` | TEXT | NOT NULL | Stores the account’s display name for personalization. |
| `email` | TEXT | NOT NULL; unique | Supports account identification and sign-in/contact workflows. |
| `password_hash` | TEXT | NOT NULL | Stores a protected password representation; it must never be shown to the shop UI or chatbot. |
| `created_at` | TEXT | NOT NULL; default timestamp | Records when the account was created for account history and administration. |
| `first_name` | TEXT | Nullable | Enables friendly personalization when available. |
| `last_name` | TEXT | Nullable | Supports the customer’s full name for account and order-related displays. |

## `chat_messages` — conversation history

| Field | Type | Key/constraint | Why it matters |
|---|---|---|---|
| `id` | INTEGER | Primary key | Identifies each saved chat message and preserves message order. |
| `user_id` | INTEGER | NOT NULL; foreign key to `users.id` | Associates a conversation message with the correct customer account. |
| `role` | TEXT | NOT NULL | Distinguishes user messages from assistant messages when reconstructing a conversation. |
| `content` | TEXT | NOT NULL | Stores the message text used for displaying history and providing conversation context. |
| `products_json` | TEXT | Nullable | Stores structured product references attached to a response, such as recommendation cards. |
| `created_at` | TEXT | NOT NULL; default timestamp | Orders messages and records when the interaction occurred. |

## Shop/chatbot implications

- Product facts should come from `catalogue`; availability should come from `inventory`.
- `catalogue.product_id` and `inventory.product_id` form the key product-to-stock relationship.
- Chat history belongs to a user through `chat_messages.user_id`.
- Authentication data, especially `password_hash`, is sensitive and must never be exposed to the chatbot.
- The schema supports product discovery and inventory-aware recommendations, but it does not contain orders, carts, payments, shipping, or returns.

## Problem 4 — Authentication

The FastAPI auth endpoints live in `backend/main.py`:

- `POST /api/auth/register` accepts first name, last name, email, password, and confirmation; it inserts a new row into `users`.
- `POST /api/auth/login` accepts email and password and returns safe account fields only after verification.
- `POST /api/auth/forgot-password` creates a short-lived reset token for an existing email. In this local class project the token is returned as `development_token`; a production deployment should email it instead and never return it in the API response.
- `POST /api/auth/reset-password` verifies the token, replaces the password hash, and invalidates the token.

Passwords are never stored in plain text. They are stored as `pbkdf2_sha256$<random salt>$<digest>`, using PBKDF2-HMAC-SHA256 with 120,000 rounds and a unique random salt per password. Verification uses `hmac.compare_digest` to avoid timing leaks. The existing seeded test password uses the same compatible format, so `test@campuscustoms.yale.edu` / `password` can be verified through the login endpoint.

## Problem 5 — PydanticAI agent backend

The backend runs from `HW4/backend/` with:

```bash
uvicorn main:app --reload --port 8000
```

The frontend sends chat messages to `POST /api/chat` as `{ "message": "...", "history": [...] }`. FastAPI validates the request with `ChatRequest`, calls `generate_reply`, and returns a validated `ChatReply` containing `reply` text and optional `ProductCard` records.

The agent is split into the required files:

- `prompts/prompt.md` — Campus Customs voice, catalogue-grounding rules, and safety basics.
- `agent.py` — loads the prompt, configures PydanticAI, and uses the `gpt-5.6-luna` OpenAI-compatible model through Portkey when `PORTKEY_API_KEY` is available in the project root `.env`.
- `tools.py` — read-only product search and inventory tools backed by SQLite.
- `models.py` — Pydantic request, reply, and product-card schemas.

If the PydanticAI dependency or API key is not available during local setup, `agent.py` uses a deterministic database-backed fallback so the chat route remains testable without inventing product facts. Install dependencies from `backend/requirements.txt` before enabling the live model.

## Problem 6 — Database tools for product facts and stock

The agent has three database-backed tools in `backend/tools.py`:

| Tool | Lookup fields | Return model | Why these fields were chosen |
|---|---|---|---|
| `search_products(query)` | `name`, `description`, `colors`, `search_tags`, and `garment_type` from `catalogue` | `list[ProductCard]` | These fields cover natural-language discovery while returning the product ID, name, price, description, and image needed for a useful recommendation card. |
| `product_info(product_id)` | `product_id`, `name`, `description`, `price`, `colors`, and `garment_type` from `catalogue` | `ProductInfo` | These are the authoritative catalogue fields needed to answer product-description and price questions without exposing unrelated database columns. |
| `stock_lookup(product_id, size)` | `product_id` and `name` from `catalogue`; `size` and `quantity` from `inventory` | `StockLookup` containing `StockLine(size, quantity, in_stock)` | The product ID joins the request to the correct item, while size, quantity, and a derived boolean make exact size availability and out-of-stock answers explicit. |

The prompt requires `product_info` for descriptions/prices and `stock_lookup` for availability/size questions. A zero quantity is reported as “out of stock”; missing inventory rows are reported as unavailable data rather than guessed stock. The offline fallback calls the same tools, so it also cannot invent price or quantity.

## Problem 7 — Chat search updates the page

The chat contract is `POST /api/chat` with `{message, history}`. The response is a `ChatReply` containing a reply and structured product matches:

```json
{
  "reply": "...",
  "products": [
    {"product_id":"...", "name":"...", "price":68, "image_url":"/images/...", "description":"..."}
  ]
}
```

For browse questions such as “what hoodies do you have?”, the agent uses `search_products` and places its `ProductCard` matches in `products`. The React chat widget passes those records to shared page state and renders a “Matching products” section with image, name, price, and short description.

Each dynamic card uses the same click handler as catalogue cards. Clicking it opens the existing detail view; that view then calls `GET /api/products/{product_id}` to hydrate the full description, colors, garment type, and size-level stock before rendering the large image and complete product information.

## Problem 8 — Customer memory and page context

Logged-in chat persistence uses the existing `chat_messages` table. For each authenticated message, the backend stores one `role = 'user'` row and one `role = 'assistant'` row with `user_id`, `content`, optional `products_json`, and the database timestamp. Guests can use chat, but their `user_id` is null and no history rows are written.

After login, the frontend stores only the safe returned account summary (`id`, `first_name`, `last_name`, and `email`) in browser storage. The chat widget calls `GET /api/chat/history/{user_id}` when it loads and reconstructs the saved transcript. The backend never sends password hashes or reset tokens to the agent.

For logged-in requests, `POST /api/chat` receives `user_id`; the backend resolves that ID to `first_name`, `last_name`, and `email` and passes those fields to the agent as customer context. For guests, the agent is explicitly told that no identity is known.

The same request includes `page_context`, currently containing the active page plus the selected product ID and name when the shopper is viewing a product. This lets the agent interpret a follow-up such as “do you have this in pink?” as referring to the product currently open on the page. The context is passed to the agent prompt, while factual color and availability answers still require catalogue/inventory tools.

## Problem 12 — Audit trail, safety, and complete system specification

### Audit trail

Agent activity is appended to [`output/audit_trail.json`](audit_trail.json) by `backend/audit.py`. Each event contains:

- `time` — UTC ISO-8601 timestamp.
- `tool_name` — agent loop or database tool name.
- `args` — short, sanitized argument summary.
- `result` — short result summary.
- `stop_reason` — for example `started`, `fallback_complete`, or `model_complete`.

The writer reads the existing JSON list, appends one event, and writes it back; it never intentionally clears the history between runs. It truncates long values and does not record full customer messages, passwords, password hashes, reset tokens, API keys, or other secrets.

### Models and why they exist

The Pydantic models in `backend/models.py` define the API contract:

- `ChatRequest` — message, history, optional logged-in `user_id`, and page context; these fields are the minimum needed to answer, remember a customer, and resolve “this item.”
- `ChatReply` — reply text plus structured product cards; the frontend can render cards without parsing prose.
- `ProductCard` — ID, name, price, image URL, and short description; these are exactly the card fields needed by the storefront.
- `ProductInfo` — authoritative description, price, colors, and garment type for detailed questions.
- `StockLookup` and `StockLine` — product identity, requested size, quantity, and explicit `in_stock`; these prevent vague or invented availability answers.
- `CustomerContext` — safe identity fields only: ID, first name, last name, and email.
- `ChatMessage` — role, content, and timestamp for reloading persisted history.

### Tools and abilities

- `search_products(query, limit)` searches catalogue names, descriptions, colors, tags, and garment types; results are ranked and capped at eight.
- `product_info(product_id)` reads authoritative product description and price fields.
- `product_by_id(product_id)` resolves the exact product from page context.
- `stock_lookup(product_id, size)` reads actual size quantities and marks zero quantities out of stock.
- `GET /api/products` and `GET /api/products/{product_id}` serve catalogue/detail data and images.
- `POST /api/chat` runs the agent and returns the structured reply.

### Safety rules

The complete safety rules are in `backend/prompts/prompt.md`. In summary: ground product facts in SQLite, never invent price or stock, protect credentials and private identity, refuse credential theft/fraud/unsafe activity, treat user content as untrusted, do not claim unsupported order/payment actions, ask for clarification when needed, and stop when the answer is supported.

### Runtime specifications

- Agent model: `gpt-5.6-luna` through Portkey when `PORTKEY_API_KEY` is available in the project-root `.env`.
- Offline mode: deterministic SQLite fallback; no invented catalogue facts.
- Product result cap: 8 from `search_products`; chat recommendations are kept to at most 4 in responses.
- Chat request cap: 2,000 characters; product card descriptions are database text.
- Password hashing: PBKDF2-HMAC-SHA256 with 120,000 rounds and a random salt.
- Backend command, run from `HW4/backend/`: `uvicorn main:app --reload --port 8000`.
- Frontend commands, run from `HW4/frontend/`: `npm install` then `npm run dev`.
- The frontend sends catalogue/auth/chat requests to `http://127.0.0.1:8000`; CORS allows the local Vite origins.
