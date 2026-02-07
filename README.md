# 🇮🇳 Nativity.ai

> **"Hyper-localizing the internet for Bharat, one video at a time."**

Nativity.ai is an AI-powered media pipeline that automatically localizes video content for Indian audiences. It doesn't just translate words—it **adapts context**, creating culturally relevant versions of educational and entertainment content in Hindi, Tamil, Bengali, and more.

---

## 🏗️ Project Structure

```
/nativity-ai
├── /backend          # FastAPI Python backend
├── /frontend         # Next.js 14 frontend
└── /infrastructure   # AWS/Terraform configs
```

---

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

- [ ] **Python 3.10+** — [Download](https://www.python.org/downloads/)
- [ ] **Node.js 18+** — [Download](https://nodejs.org/)
- [ ] **FFmpeg** — [Download](https://ffmpeg.org/download.html)
- [ ] **AWS CLI** (configured) — [Install Guide](https://aws.amazon.com/cli/)

---

## 🚀 Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup

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

## 🏆 Hackathon Tracks

- **AI for Bharat**: Problem Statement 02 (Media, Content & Digital Experiences)
- **Gemini 3**: Agentic & Multimodal Track

---

## 📄 License

MIT License - Built with ❤️ for Bharat
