# SmartCast

SmartCast is a **production-grade, Python-based live-streaming platform** inspired by Twitch and YouTube Live.  It delivers end-to-end broadcasting – from RTMP ingest with OBS Studio through adaptive HLS playback – in a single Docker-Compose stack that you can run locally or deploy to the cloud.

---

## ✨ Key Features

| Area | Capability |
|------|------------|
| **Live Ingest** | RTMP/OBS compatible, secure stream-key authentication |
| **Adaptive Bitrate** | FFmpeg transcoding to 1080p / 720p / 480p HLS variants, HLS.js auto-switching |
| **Multi-CDN** | Three simulated CDN origins with latency-aware or manual routing |
| **Real-Time Chat** | WebSocket chat with emojis, Redis pub/sub fan-out & PostgreSQL persistence |
| **VOD Workflow** | Automatic recording, thumbnail generation & VOD listing once a stream ends |
| **Auth** | JWT tokens, OAuth2 flow, streamer / viewer / admin role-based access |
| **Recommendations** | **NEW!** Self-attentive sequential recommender (`LiveRec`) with dynamic item availability & repeat consumption tracking. See [`KAGGLE_SETUP.md`](KAGGLE_SETUP.md) for Kaggle multi-GPU training instructions. |
| **Observability** | Prometheus metrics + pre-built Grafana dashboards |
| **One-Command Run** | `docker-compose up` boots the entire micro-service stack |

---

## 🗂️ Repository Layout

```
.
├── backend/            # FastAPI application
│   ├── app/            #  ├─ routers, services, models, schemas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           # Streamlit UI
│   ├── streamlit_app.py
│   ├── pages/
│   ├── utils/
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf      # RTMP ingest + CDN reverse-proxy
├── ffmpeg_scripts/
│   ├── vod_worker.sh   # post-stream VOD + thumbnails
│   └── segmenter.sh    # live multi-bitrate encoding
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/        # JSON dashboards & provisioning
├── docker/
│   └── entrypoint.sh   # shared helper scripts
├── docker-compose.yml  # brings every service up
├── .env.example        # copy → .env and tweak
└── README.md           # you are here
```

---

## 🏗️ Tech Stack

* **Python** 3.11 • FastAPI • Streamlit
* **Video**: FFmpeg • nginx-rtmp • HLS.js
* **Data**: PostgreSQL • SQLAlchemy • Alembic
* **Machine Learning**: PyTorch • Scikit-learn • Pandas (LiveRec Recommender)
* **Realtime / Cache**: Redis (pub/sub)
* **Messaging**: WebSockets (Starlette)
* **Infra**: Docker • docker-compose • Nginx
* **Observability**: Prometheus • Grafana

---

## ⚡ Quick Start (Local Laptop)

```bash
# 1 – clone
$ git clone https://github.com/<your-user>/smartcast.git && cd smartcast

# 2 – env
$ cp .env.example .env   # edit JWT_SECRET, DB_PASS … if you wish

# 3 – launch everything
$ docker-compose up ‑-build
```

Wait ~1-2 minutes; you should see all services healthy.

| Service | URL | Default Creds |
|---------|-----|---------------|
| Frontend (Streamlit) | <http://localhost:8501> | create account in UI |
| API Docs (FastAPI) | <http://localhost:8000/docs> | — |
| Grafana | <http://localhost:3000> | admin / admin |

---

## 🎥 Streaming via OBS Studio

1. **Create Stream** – Log in as a *streamer* → “New Stream” → note the *Stream Key*.
2. **OBS Settings**  
   * *Server*: `rtmp://localhost:1935/live`  
   * *Stream Key*: the key from step 1.
3. **Start Streaming** – OBS → *Start Streaming*.  FastAPI callbacks authenticate the key and FFmpeg starts multi-bitrate encoding automatically.
4. **Watch** – Open the stream card on the **Streams** page → HLS player auto-selects quality; you can override via the *Quality* dropdown.

---

## 💬 Chat & Emojis

* Chat runs on `ws://localhost:8000/ws/chat/{stream_id}`.
* Messages are fanned out through Redis pub/sub → saved in PostgreSQL.
* Emoji reactions are supported with shortcodes (`:fire:`, `:heart:` …).

---

## 📈 Monitoring

Prometheus scrapes each container; Grafana dashboards include:

* **Streamer-Overview** – bitrate, key-frame interval, transcoder CPU
* **Viewer-Experience** – buffer health, quality switches, latency
* **System** – container CPU / mem, database throughput, Redis ops/sec

---

## 🧑‍💻 Development Workflow

```bash
# hot-reload backend
$ docker compose exec backend uvicorn app.main:app --reload --host 0.0.0.0

# run Streamlit locally outside Docker
$ cd frontend && poetry install && streamlit run streamlit_app.py
```
*DB / Redis environment variables are already exposed by Compose network aliases.*

---

## 🔐 Security Notes

* All private routes require Bearer JWT (see `backend/app/core/security.py`).
* Passwords are hashed with **bcrypt**; never stored plaintext.
* Stream ingestion is protected by signed stream keys validated before nginx-rtmp accepts the connection.

---

## 📅 Roadmap / Future Work

* **Ultra-Low-Latency** (WebRTC ingest + playback)
* **Mobile Apps** (Flutter)
* **Admin Panel** for moderation & stream takedown
* **AI Highlights** – automatic clip generation
* **Real CDN** integration (Cloudflare Stream/KeyCDN)

---

## 📝 License

SmartCast is released under the MIT License – see `LICENSE` for details.
