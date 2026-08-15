# 🇮🇳 Nativity.ai

> **"Hyper-localizing the internet for Bharat, one video at a time."**

Nativity.ai is an AI-powered media pipeline that automatically localizes video content for Indian audiences. It doesn't just translate words—it **adapts context**, creating culturally relevant versions of educational and entertainment content in Hindi, Tamil, Bengali, and more.

---

## 🏗️ Project Structure

```
/nativity-ai
├── /backend          # FastAPI Python backend (Celery Worker + Web API)
├── /frontend         # Next.js 14 frontend (Clerk Auth)
└── /render.yaml      # Render deployment configuration
```

---

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

- [ ] **Python 3.10+** — [Download](https://www.python.org/downloads/)
- [ ] **Node.js 18+** — [Download](https://nodejs.org/)
- [ ] **Docker & Docker Compose** (for local services)
- [ ] **FFmpeg** — [Download](https://ffmpeg.org/download.html)

---

### Services Used (Free Tier)
- **Compute:** Render.com
- **Database:** Supabase PostgreSQL
- **Storage:** Cloudflare R2
- **Queue/Cache:** Upstash Redis
- **Auth:** Clerk
- **AI:** Google Gemini 2.0 Flash

### Environment Variables
Copy `.env.example` to `.env` and fill in your credentials.

### Run Locally (Docker Compose - Recommended)
This spins up the Redis broker, FastAPI backend, Celery worker, and Next.js frontend all at once.
```bash
docker-compose up --build
```

### Run Locally (Manual)

**1. Start Redis** (Requires Redis running locally on port 6379)

**2. Backend + Worker**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1: Start API
uvicorn main:app --reload

# Terminal 2: Start Celery Worker
python start_worker.py
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

---


## 📄 License

MIT License 
