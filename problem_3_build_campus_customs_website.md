# Problem 3 — Build the Campus Customs Website

The React + Vite + TypeScript frontend is in [`frontend/`](frontend/).

The catalogue API is in [`backend/main.py`](backend/main.py). It reads products and inventory directly from `data/campus_customs.db`, serves the database image paths through `/images`, and is intentionally small so it can grow into the agent backend in Problem 5.

It includes the requested top navigation:

- Home
- Products
- About us
- Log in
- Create account

The Home and About us pages now follow the reference store's official-merchandise voice and Yale-blue retail presentation. The copy is original and avoids copying the reference site's text.

## Run

```bash
cd HW4/backend
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

In a second terminal:

```bash
cd HW4/frontend
npm install
npm run dev
```
