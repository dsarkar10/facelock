# Shan — Face Recognition Authentication System

A biometric authentication system that uses **facial recognition** to register and log in users instead of passwords. Built with FastAPI, face_recognition (dlib), SQLite, and Svelte.

Users register a face (given a name like "Face 1", "Face 2"), then log in by looking at their webcam. Failed login attempts are recorded and surfaced as security alerts on the dashboard. Multiple faces per account are supported with inline rename and delete.

---

## Features

| Feature | Details |
|---------|---------|
| **Face Registration** | Capture via webcam, name your face (e.g. "Face 1"), stores a 128-dimensional encoding |
| **Face Login** | Compare live webcam feed against all registered faces for that username |
| **Multiple Faces** | Add, rename, and delete face IDs; minimum 1 face enforced |
| **Security Alerts** | Failed login attempts logged; unread alerts shown on dashboard |
| **Activity History** | Full timeline of REGISTER, LOGIN, and FAILED_LOGIN events |
| **Live Network Info** | Real-time IP, connection type, downlink, RTT, and online status |
| **Face Detection Guide** | Red/green oval overlay on the camera feed using the browser's `FaceDetector` API |
| **Session Auth** | Cookie-based sessions via signed cookies (no JWT needed) |
| **Zero-Config DB** | SQLite database auto-created in the project directory (no daemon) |

---

## Tech Stack

```
┌───────────────────────────────────────────────────┐
│                    Frontend                        │
│  Svelte 5 + Vite 6 + FaceDetector API (browser)   │
├───────────────────────────────────────────────────┤
│                    Backend                         │
│  FastAPI + SessionMiddleware + face_recognition    │
├───────────────────────────────────────────────────┤
│                    Storage                         │
│  SQLite + pickle (face encodings stored as BLOB)  │
└───────────────────────────────────────────────────┘
```

- **Backend:** Python 3.13, FastAPI, face_recognition (dlib), SQLite3
- **Frontend:** Svelte 5, Vite 6, FaceDetector API
- **Auth:** `starlette.middleware.sessions.SessionMiddleware` (signed cookies via `itsdangerous`)
- **Infrastructure:** uv (package manager), cmake (dlib build)

---

## How It Works

### 1. Face Encoding Pipeline

```
Webcam → canvas.toBlob("image/jpeg") → FormData → FastAPI
                                                      ↓
                                       face_recognition.load_image_file()
                                                      ↓
                                         face_recognition.face_encodings()
                                                      ↓
                                         128-dimensional numpy array
                                                      ↓
                                               pickle.dumps()
                                                      ↓
                                          SQLite BLOB column
```

Each face is converted to a **128-dimensional embedding** — a vector of floats that mathematically represents facial features. The `face_recognition` library (by Adam Geitgey) wraps dlib's deep learning model (ResNet-34) trained on ~3 million faces.

### 2. Registration Flow

```
User types username + face name → captures webcam → POST /api/register
                                                          ↓
                                             1. Create user in `users` table
                                             2. Encode face → store in `faces` table
                                             3. Log REGISTER event in `security_logs`
                                                          ↓
                                                Redirect to Login
```

### 3. Login Flow

```
User types username → captures webcam → POST /api/login
                                              ↓
                              Fetch ALL face encodings for this user
                                              ↓
                              For each stored encoding:
                                face_recognition.compare_faces(
                                  stored_encoding, live_encoding, tolerance=0.6
                                )
                                              ↓
                              ┌───── Match ─────┐     ┌── No Match ──┐
                              │ Set session      │     │ Log FAILED_  │
                              │ cookie (user,    │     │ LOGIN event  │
                              │ face_id,         │     │ Return 401   │
                              │ face_name)       │     └──────────────┘
                              │ Log LOGIN event  │
                              └──────────────────┘
```

The tolerance of **0.6** is the default — lower values are stricter, higher are more lenient.

### 4. Notification System

```
Failed login → INSERT into security_logs (attempt_type='FAILED_LOGIN', read=0)
                                                      ↓
Dashboard Home tab checks GET /api/notifications → shows badge count
                                                      ↓
User clicks "Dismiss All" → UPDATE read=1 for all FAILED_LOGIN entries
```

Only `FAILED_LOGIN` events count as unread notifications. REGISTER and LOGIN events appear in the History tab but never trigger alerts.

### 5. Face ID Management

```
GET  /api/faces      → list all faces for logged-in user
POST /api/faces      → add a new face (capture + name)
PUT  /api/faces/{id} → rename a face
DELETE /api/faces/{id} → delete a face (rejected if last remaining)
```

The `faces` table is separate from `users` — one user can have many faces. Login iterates through all of them and returns the matched face name.

---

## Project Structure

```
shan/
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── backend/
│   ├── main.py                   # FastAPI app, all routes
│   ├── database.py               # SQLite connection, schema, CRUD
│   ├── face_utils.py             # encode_face(), compare_faces()
│   ├── shan.db                   # SQLite database (auto-created)
│   └── __init__.py
├── frontend/
│   ├── package.json              # Node dependencies
│   ├── vite.config.js            # Vite config + /api proxy
│   ├── index.html
│   └── src/
│       ├── main.js               # App entry point (mount Svelte)
│       ├── App.svelte            # Router: loading → login/register/dashboard
│       └── lib/
│           ├── Camera.svelte     # Webcam with oval overlay + FaceDetector
│           ├── Register.svelte   # Username + face name + capture
│           ├── Login.svelte      # Username + capture
│           └── Dashboard.svelte  # Sidebar, home, network, history, face ID
└── .venv/                        # Python virtual environment (uv-managed)
```

---

## API Reference

All endpoints except `/api/register` and `/api/login` require a valid session cookie.

### Auth

| Method | Path | Body | Response | Description |
|--------|------|------|----------|-------------|
| POST | `/api/register` | `username`, `face_name` (default "Face 1"), `face` (file) | `{"status": "ok"}` | Create account + register first face |
| POST | `/api/login` | `username`, `face` (file) | `{"status": "ok", "face_name": "..."}` | Authenticate via face, sets session cookie |
| GET | `/api/me` | — | `{"username": "..." , "face_id": ..., "face_name": "..."}` | Current session info |
| POST | `/api/logout` | — | `{"status": "ok"}` | Clear session |

### Faces

| Method | Path | Body | Response | Description |
|--------|------|------|----------|-------------|
| GET | `/api/faces` | — | `{"faces": [{id, face_name, created_at}]}` | List all registered faces |
| POST | `/api/faces` | `face_name`, `face` (file) | `{"status": "ok", "id": ...}` | Register a new face |
| PUT | `/api/faces/{id}` | `face_name` | `{"status": "ok"}` | Rename a face |
| DELETE | `/api/faces/{id}` | — | `{"status": "ok"}` | Delete a face (fails if last) |

### Security & Monitoring

| Method | Path | Response | Description |
|--------|------|----------|-------------|
| GET | `/api/notifications` | `{"notifications": [...]}` | Unread failed login attempts |
| POST | `/api/notifications/dismiss` | `{"status": "ok"}` | Mark all as read |
| GET | `/api/history` | `{"history": [...]}` | Full event timeline |
| GET | `/api/network-info` | `{"ip": "...", "user_agent": "..."}` | Client network info |

---

## Installation

### Prerequisites

- **Python 3.13+** with `uv` package manager (or pip)
- **Node.js 20+** with npm
- **cmake** (required to build dlib)

Check cmake:
```bash
cmake --version   # Should be 3.x+
```

If missing on macOS:
```bash
brew install cmake
```

### 1. Clone & Set Up Backend

```bash
git clone <repo-url> shan
cd shan

# Create venv and install deps (uv is already used by this project)
uv venv
uv pip install -r requirements.txt

# If using pip instead:
# python -m venv .venv
# source .venv/bin/activate
# pip install -r requirements.txt
```

The `face_recognition` library will compile `dlib` during installation — this takes 2-5 minutes on first install. The `setuptools<70` pin in `requirements.txt` is required because newer versions removed `pkg_resources` which `face_recognition_models` depends on.

### 2. Set Up Frontend

```bash
cd frontend
npm install
```

### 3. Run

**Terminal 1 — Backend:**
```bash
cd shan
uv run uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd shan/frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

The Vite dev server proxies `/api/*` requests to `http://localhost:8000`, so CORS is handled transparently during development.

---

## Usage Walkthrough

### Register an Account

1. Open http://localhost:5173
2. Click "Register" at the bottom
3. Enter a **username** (e.g. `john`)
4. Enter a **face name** (e.g. `Face 1` — this can be changed later)
5. Position your face in the **oval overlay** (turns green when the browser detects a face)
6. Click **Capture**, then **Register**
7. You'll see "Registered! You can now log in."

### Log In

1. Enter your username
2. Capture your face
3. Click **Login**
4. If the face matches any of your registered faces, you're logged in and redirected to the dashboard

### Dashboard

The dashboard has a sidebar with these tabs:

| Tab | What it shows |
|-----|---------------|
| **Home** | Security status badge, account age, failed attempt count, last login, recent activity (last 5 events), current session info (IP, connection, browser) |
| **Security** | All unread failed login attempts with timestamps; "Dismiss All" clears them |
| **Network** | Live-updating network info: IP, connection type (4G/3G/etc), downlink speed, RTT latency, online status (polls every 3 seconds) |
| **History** | Full chronological event timeline — registration, logins, and failed attempts |
| **Face ID** | Manage your registered faces: rename inline, delete, or add new faces |

### Managing Faces

1. Go to the **Face ID** tab
2. Each face shows its name and the date it was added
3. Click ✏️ to rename → the name becomes editable → click ✓ to save or ✕ to cancel
4. Click 🗑️ to delete a face (you'll be prompted to confirm)
   - The delete button is **disabled** if you only have one face — you must add another first
5. Click **▶ Add New Face** to expand the camera and register a new face with a name

---

## Browser Compatibility

| Feature | Chrome/Edge | Firefox | Safari |
|---------|-------------|---------|--------|
| Camera (getUserMedia) | ✅ | ✅ | ✅ |
| FaceDetector API | ✅ | ❌ | ❌ |
| Network Information API | ✅ | ❌ | ❌ |

When the `FaceDetector` API is unavailable (Firefox, Safari), the oval overlay defaults to an indigo "Position face in oval" guide. Face detection still works — it happens server-side via `face_recognition`.

---

## Security Considerations

### What This Project Is
- A **demonstration** of biometric authentication
- Great for learning, portfolio projects, and internal tools
- Uses industry-standard face recognition (dlib ResNet-34)

### What This Project Is NOT
- **Not production-ready** for banking, healthcare, or high-security systems
- **No liveness detection** — a printed photo or video playback can fool the system (spoofing attack)
- **No encryption at rest** — face encodings are stored as pickle BLOBs in SQLite
- **No rate limiting** — an attacker could brute-force face attempts
- **Static session secret** — the `SessionMiddleware` secret key is hardcoded for development

### To Improve Security
- Add liveness detection (blink detection, depth sensor, or challenge-response)
- Replace the static session secret with `os.urandom(32)` read from an environment variable
- Enforce HTTPS in production
- Add rate limiting (e.g., `slowapi` or Cloudflare)
- Store face encodings with application-level encryption (e.g., `cryptography.fernet`)
- Switch from pickle to a safer serialization format (pickle is vulnerable to deserialization attacks if the DB is tampered with)

---

## Database Schema

```sql
-- Account metadata
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Face encodings (one user can have many)
CREATE TABLE faces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    face_name TEXT NOT NULL DEFAULT 'Face 1',
    face_encoding BLOB NOT NULL,   -- pickled numpy array (128 floats)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event log (REGISTER, LOGIN, FAILED_LOGIN)
CREATE TABLE security_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    attempt_type TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read INTEGER DEFAULT 0         -- 0 = unread, 1 = dismissed
);
```

---

## Troubleshooting

### `dlib` fails to compile
```bash
# macOS: install cmake and Xcode Command Line Tools
brew install cmake
xcode-select --install
```

### `ModuleNotFoundError: No module named 'pkg_resources'`
This happens with setuptools ≥ 70. The requirements.txt pins it below 70.
```bash
uv pip install "setuptools<70"
```

### `face_recognition_models` import error
```bash
uv pip install git+https://github.com/ageitgey/face_recognition_models
```

### Camera not working in browser
- Ensure you're on **localhost** (HTTPS is required for `getUserMedia` on non-localhost origins)
- Grant camera permission when prompted
- On macOS, check System Settings → Privacy & Security → Camera
- Close other apps using the camera (Zoom, Slack, etc.)

### No face detected (server returning 400)
- Ensure good lighting — face needs to be well-lit and clearly visible
- Position face directly facing the camera
- Remove sunglasses or heavy face coverings
