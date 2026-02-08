# reGenerate - Your Immersive Cinematic Digital Footprint

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)
![React](https://img.shields.io/badge/react-18.0-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.0-blue)
![Docker](https://img.shields.io/badge/docker-24.0-2496ED.svg)
![Gemini 3](https://img.shields.io/badge/AI-Gemini%203-8E44AD.svg)

**reGenerate** transforms your professional history into an immersive, cinematic narrative. It uses state-of-the-art AI to analyze your contributions across platforms (LinkedIn, GitHub, etc.) to tell your story better than a static resume ever could.

---

## 📖 About The Project

### The Problem
In the fast-paced world of technology and professional growth, we often become so focused on the "now" and "next" that we lose sight of the "past." Meaningful contributions, pivotal project milestones, and crucial skills learned years ago fade from memory. When it's time to update a resume or portfolio, we struggle to recall the depth of our impact, resulting in generic profiles that fail to capture our true journey.

### The Solution
**reGenerate** acts as your personal digital biographer. By connecting to your professional accounts (LinkedIn, GitHub, etc.), it uses advanced AI (Google Gemini 3) to:
1.  **Analyze** deep historical data and contributions.
2.  **Structure** your career path into a meaningful timeline.
3.  **Visualise** your journey using immersive 3D graphics and timelines.
4.  **Generate** cinematic video documentaries of your professional life using AI voiceovers and video segments.

It's not just a profile; it's a celebration of your career.

---

## ✨ Key Features

- **🤖 AI Profile Analysis**: Deep analysis of professional scopes (years of experience, skills, projects) using Google Gemini 3.
- **⏱️ Immersive Timeline Reconstruction**: Chronological 3D visualization of your journey, highlighting key milestones.
- **🔗 Multi-Platform Integration**: Seamlessly connects with LinkedIn, GitHub, and more.
- **📊 Code Contribution Analytics**: Specialized insights for developers, analyzing commits, PRs, and open-source impact.
- **🎥 AI Video Documentary**: Generates personalized 30-second (upto 120-second) video narratives (via Gemini Veo) to share on social media.
- **🔒 Privacy First**: User-controlled privacy settings to include or exclude specific data points for their public profile.
- **📈 Achievement Verification**: AI-driven quantification of your impact and contributions.

---

## 🛠️ Tech Stack

### Backend
-   **Language**: Python 3.10+
-   **Framework**: FastAPI
-   **Database**: SQLAlchemy (MySQL) with Alembic migrations
-   **AI Engine**: Google Gemini 3 (via `google-genai`), Gemini Veo
-   **Storage**: Google Cloud Storage (GCS)
-   **Task Queue**: Redis (Background jobs)

### Frontend
-   **Framework**: React (Vite)
-   **Language**: TypeScript
-   **Visualization**: Three.js, D3.js, Chart.js, Vis.js
-   **Animations**: GSAP, Framer Motion

### Infrastructure
-   **Containerization**: Docker & Docker Compose
-   **Cloud**: Google Cloud Run
-   **CI/CD**: Cloud Build

---

## 📂 Project Structure

```bash
regenerate/
├── app/                 # Backend FastAPI application
│   ├── api/             # API routes and controllers
│   ├── core/            # Config, security, and logging
│   ├── db/              # Database models and session management
│   ├── services/        # Business logic (AI, LinkedIn, Video gen)
│   └── schemas/         # Pydantic models for data validation
├── frontend/            # Frontend React application
│   ├── src/             # Source code (components, pages, hooks)
│   └── public/          # Static assets
├── alembic/             # Database migrations
├── docker-compose.yml   # Container orchestration configuration
└── scripts/             # Utility scripts for dev and deployment
```

---

## 🚀 Getting Started

### Prerequisites
-   **Docker** and **Docker Compose** installed.
-   **Python 3.10+** (if running backend locally without Docker).
-   **Node.js 18+** (if running frontend locally without Docker).
-   **Google Cloud Project** with Gemini API enabled.

### Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/iyinusa/regenerate.git
    cd regenerate
    ```

2.  **Environment Configuration**
    Create a `.env` file in the root directory. You can copy the example if provided, or set the following keys:
    ```env
    APP_ENV=dev
    DATABASE_URL=mysql+aiomysql://user:password@db/regenerate
    GOOGLE_API_KEY=your_gemini_api_key
    SECRET_KEY=your_secret_key
    # Add other provider keys (LinkedIn, GitHub) as needed
    ```

3.  **Run with Docker (Recommended)**
    Start the entire stack (Frontend, Backend, Database, Redis):
    ```bash
    docker-compose up --build
    ```
    -   **Frontend**: http://localhost:5173
    -   **Backend API**: http://localhost:8000
    -   **API Docs**: http://localhost:8000/docs

4.  **Run Locally (Manual)**

    *Backend:*
    ```bash
    # Install dependencies
    pip install -e .
    
    # Run migrations
    alembic upgrade head
    
    # Start Server
    uvicorn app.main:app --reload --port 8000
    ```

    *Frontend:*
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

---

## 🧪 Running Tests

To run the backend test suite:
```bash
docker-compose exec regen-api pytest
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the project
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
