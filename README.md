# 🔗 URL Shortener System

A high-performance, scalable URL shortener system built using **FastAPI**, **MongoDB**, and **Redis**. Designed with modern best practices including **asynchronous programming**, **containerization**, **CI/CD**, and **Kubernetes deployment**.

---

## 🚀 Features

- ✂️ Generate short URLs from long links
- 🔁 Redirect short codes to original URLs
- ⚡ Redis caching for low-latency performance
- 📦 Dockerized with Compose for dev & prod
- ☸️ Kubernetes-ready (with HPA, Ingress, Services)
- ✅ Health endpoints & Swagger UI
- 🧪 Pytest test suite with async fixtures
- 🔄 GitHub Actions CI pipeline

---

## 📁 Project Structure
├── fapp.py                 # Main FastAPI application ├── url_post_req.py         # Script to populate MongoDB ├── requirements.txt        # Python dependencies ├── .github/workflows/ci.yml  # GitHub Actions CI setup ├── docker-compose.yml      # Docker multi-container config ├── kubernetes/             # YAMLs for deployment, services, ingress ├── tests/                  # Pytest test cases ├── Notes.md                # System design notes

---

## 🛠️ Setup Instructions

### 🔹 1. Create & Activate Virtual Environment

```bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

🔹 2. Install Dependencies

pip install -r requirements.txt


---

🧪 Local Development

⚙️ Prerequisites

MongoDB running locally or via Docker

Redis running locally or via Docker


Run Redis via Docker:

docker run -d --name redis -p 6379:6379 redis

Run MongoDB via Docker:

docker run -d --name mongodb -p 27017:27017 mongo

🚦 Start the Application

uvicorn fapp:app --port 5000


---

🔌 API Endpoints

Method	Endpoint	Description

GET	/	Root route; interacts with Redis
POST	/api/encode	Accepts long_url and returns a shortened URL
GET	/{short_code}	Redirects to original URL (via short code)
