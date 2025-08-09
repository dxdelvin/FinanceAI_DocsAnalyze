# AI Hackathon Starter (Python-first)

A tiny, production-friendly starter that gives you a **Python FastAPI backend** and a **server-rendered frontend with Jinja2**.
Perfect for hackathons when you want to ship fast without wrestling a separate JS frontend.

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
