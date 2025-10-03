# AI Hackathon Starter (Python-first)

A tiny, production-friendly starter that gives you a **Python FastAPI backend** and a **server-rendered frontend with Jinja2**.
(THE DOCS analyze Part is not Updated, its still work in progress what it does is it will Scan your DOCS not using OCR but Markdown Technique and can analyze Your Text more accurately with all tables and THE AI can answer your questions more accurately)

<img width="1375" height="900" alt="Screenshot 2025-08-09 143243" src="https://github.com/user-attachments/assets/889b71cb-3152-48ea-bb7f-79f8f87eca6c" />
<img width="1751" height="964" alt="Screenshot 2025-08-09 170003" src="https://github.com/user-attachments/assets/a9903bcf-83ef-46ae-ad03-80bf9a89ffcd" />
<img width="1266" height="955" alt="Screenshot 2025-08-09 143419" src="https://github.com/user-attachments/assets/4972ae6f-a369-4fce-a7c2-baec6259aa1e" />


## Features
- FastAPI backend with `/api/health`
- Jinja2 templates for a clean Home page
- Static assets (CSS) already wired
- One-command dev server with auto-reload

---

## Quickstart

### 1) Requirements
- Python 3.10+ recommended

### 2) Clone + set up
```bash
git init ai-hackathon-starter
cd ai-hackathon-starter

# (Optional) create a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install deps
pip install -r requirements.txt
```

### 3) Run the server
```bash
# From the project root
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload

```

- App will be at: http://localhost:8000
- Health check: http://localhost:8000/api/health

### 4) (Optional) Environment vars
Copy `.env.example` to `.env` and tweak values. The app auto-loads `.env` on start.

---

## Docker (optional)
```bash
# Build
docker build -t ai-hackathon-starter .

# Run
docker run -p 8000:8000 --env-file .env ai-hackathon-starter
```

Or via Compose:
```bash
docker compose up --build
```

---

## Project structure
```
ai-hackathon-starter/
  app/
    routers/
      health.py
    views/
      web.py
    templates/
      base.html
      index.html
    static/
      styles.css
    __init__.py
    config.py
    main.py
  .env.example
  .gitignore
  requirements.txt
  Dockerfile
  docker-compose.yml
  README.md
```

Happy hacking! ✨
