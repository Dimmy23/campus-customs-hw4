"""Small catalogue API for Problem 3; this becomes the agent backend in Problem 5."""

from pathlib import Path
import sqlite3
import hashlib
import hmac
import secrets
import time
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from agent import generate_reply
from models import ChatMessage, ChatReply, ChatRequest, CustomerContext

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "campus_customs.db"
DATA_DIR = ROOT / "data"

app = FastAPI(title="Campus Customs API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
app.mount("/images", StaticFiles(directory=DATA_DIR / "products"), name="images")

PBKDF2_ROUNDS = 120_000


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotRequest(BaseModel):
    email: str


class ResetRequest(BaseModel):
    email: str
    token: str
    password: str
    confirm_password: str


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def password_matches(password: str, stored: str) -> bool:
    try:
        algorithm, salt, expected = stored.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS).hex()
        return hmac.compare_digest(actual, expected)
    except ValueError:
        return False


def ensure_auth_table() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS auth_reset_tokens (email TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires_at INTEGER NOT NULL)")
    connection.commit()
    connection.close()


ensure_auth_table()


def row_to_product(row: sqlite3.Row, sizes: list[dict]) -> dict:
    item = dict(row)
    item["image_url"] = f"/images/{Path(item['image_file_path']).name}"
    item["sizes"] = sizes
    return item


def product_rows(product_id: str | None = None) -> list[dict]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        query = "SELECT product_id, name, garment_type, description, colors, search_tags, image_file_path, price FROM catalogue"
        params: tuple[str, ...] = ()
        if product_id:
            query += " WHERE product_id = ?"
            params = (product_id,)
        query += " ORDER BY name"
        products = []
        for row in connection.execute(query, params):
            stock = connection.execute("SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY size", (row["product_id"],)).fetchall()
            products.append(row_to_product(row, [{"size": s["size"], "quantity": s["quantity"]} for s in stock]))
        return products
    finally:
        connection.close()


@app.post("/api/auth/register")
def register(payload: RegisterRequest) -> dict:
    if not payload.first_name.strip() or not payload.last_name.strip():
        raise HTTPException(status_code=400, detail="First and last name are required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    connection = sqlite3.connect(DB_PATH)
    try:
        if connection.execute("SELECT 1 FROM users WHERE email = ?", (str(payload.email).lower(),)).fetchone():
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        connection.execute("INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)", (f"{payload.first_name.strip()} {payload.last_name.strip()}", str(payload.email).lower(), password_hash(payload.password), payload.first_name.strip(), payload.last_name.strip()))
        connection.commit()
        return {"message": "Account created", "first_name": payload.first_name.strip(), "email": str(payload.email).lower()}
    finally:
        connection.close()


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        user = connection.execute("SELECT id, first_name, last_name, email, password_hash FROM users WHERE email = ?", (str(payload.email).lower(),)).fetchone()
        if not user or not password_matches(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return {"message": "Logged in", "user": {"id": user["id"], "first_name": user["first_name"], "last_name": user["last_name"], "email": user["email"]}}
    finally:
        connection.close()


@app.post("/api/auth/forgot-password")
def forgot_password(payload: ForgotRequest) -> dict:
    email = str(payload.email).lower()
    connection = sqlite3.connect(DB_PATH)
    try:
        exists = connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if not exists:
            return {"message": "If that account exists, reset instructions have been created."}
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        connection.execute("INSERT OR REPLACE INTO auth_reset_tokens (email, token_hash, expires_at) VALUES (?, ?, ?)", (email, token_hash, int(time.time()) + 900))
        connection.commit()
        # A real deployment emails this token. Returning it keeps the local class project testable.
        return {"message": "Reset instructions created. Use the development token to reset your password.", "development_token": raw_token}
    finally:
        connection.close()


@app.post("/api/auth/reset-password")
def reset_password(payload: ResetRequest) -> dict:
    if len(payload.password) < 8 or payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Password must be 8+ characters and match confirmation")
    email = str(payload.email).lower()
    connection = sqlite3.connect(DB_PATH)
    try:
        record = connection.execute("SELECT token_hash, expires_at FROM auth_reset_tokens WHERE email = ?", (email,)).fetchone()
        token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
        if not record or record[1] < int(time.time()) or not hmac.compare_digest(token_hash, record[0]):
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        connection.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash(payload.password), email))
        connection.execute("DELETE FROM auth_reset_tokens WHERE email = ?", (email,))
        connection.commit()
        return {"message": "Password reset successfully"}
    finally:
        connection.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatReply)
async def chat(payload: ChatRequest) -> ChatReply:
    customer = None
    if payload.user_id is not None:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        user = connection.execute("SELECT id, first_name, last_name, email FROM users WHERE id = ?", (payload.user_id,)).fetchone()
        connection.close()
        if user:
            customer = CustomerContext(**dict(user))
    reply = await generate_reply(payload.message, payload.history, customer, payload.page_context)
    if customer:
        connection = sqlite3.connect(DB_PATH)
        connection.execute("INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, ?)", (customer.user_id, payload.message, None))
        connection.execute("INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)", (customer.user_id, reply.reply, __import__('json').dumps([card.model_dump() for card in reply.products])))
        connection.commit()
        connection.close()
    return reply


@app.get("/api/chat/history/{user_id}", response_model=list[ChatMessage])
def chat_history(user_id: int) -> list[ChatMessage]:
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute("SELECT role, content, created_at FROM chat_messages WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()
    connection.close()
    return [ChatMessage(role=row[0], content=row[1], created_at=row[2]) for row in rows]


@app.get("/api/products")
def products() -> list[dict]:
    return product_rows()


@app.get("/api/products/{product_id}")
def product(product_id: str) -> dict:
    matches = product_rows(product_id)
    if not matches:
        raise HTTPException(status_code=404, detail="Product not found")
    return matches[0]
