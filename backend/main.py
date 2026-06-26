import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse

from database import (
    add_blocked_domain,
    add_blocked_ip,
    delete_face,
    dismiss_notifications,
    get_blocked_domains,
    get_blocked_ips,
    get_face_by_id,
    get_face_encodings,
    get_faces,
    get_notifications,
    get_user,
    get_user_history,
    init_db,
    log_attempt,
    log_registration,
    log_successful_login,
    remove_blocked_domain_by_id,
    remove_blocked_ip_by_id,
    save_face,
    save_user,
    update_face_name,
    username_exists,
)
from face_utils import compare_faces, encode_face
from firewall import (
    apply_domain_block,
    apply_ip_block,
    get_firewall_status,
    remove_domain_block,
    remove_ip_block,
)

app = FastAPI()

SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), "snapshots")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key="shan-face-auth-secret-change-in-prod")


@app.on_event("startup")
def startup():
    init_db()
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


@app.post("/api/register")
async def register(username: str = Form(...), face_name: str = Form("Face 1"), face: UploadFile = None):
    if not face:
        raise HTTPException(400, "No face image provided")
    if not username.strip():
        raise HTTPException(400, "Username is required")
    if username_exists(username.strip()):
        raise HTTPException(409, "Username already exists")

    image_bytes = await face.read()
    try:
        encoding = encode_face(image_bytes)
    except ValueError as e:
        raise HTTPException(400, str(e))

    save_user(username.strip())
    save_face(username.strip(), face_name.strip() or "Face 1", encoding)
    log_registration(username.strip())
    return {"status": "ok"}


@app.post("/api/login")
async def login(request: Request, username: str = Form(...), face: UploadFile = None):
    if not face:
        raise HTTPException(400, "No face image provided")
    if not username.strip():
        raise HTTPException(400, "Username is required")

    user = get_user(username.strip())
    if not user:
        raise HTTPException(404, "User not found")

    encodings = get_face_encodings(username.strip())
    if not encodings:
        raise HTTPException(400, "No faces registered for this user")

    image_bytes = await face.read()
    matched = None
    for entry in encodings:
        try:
            if compare_faces(entry["face_encoding"], image_bytes):
                matched = {"id": entry["id"], "face_name": entry["face_name"]}
                break
        except ValueError:
            continue

    if not matched:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snap_dir = os.path.join(SNAPSHOTS_DIR, username.strip())
        os.makedirs(snap_dir, exist_ok=True)
        snap_filename = f"{ts}.jpg"
        snap_path = os.path.join(snap_dir, snap_filename)
        with open(snap_path, "wb") as f:
            f.write(image_bytes)
        relative_path = os.path.join("snapshots", username.strip(), snap_filename)
        log_attempt(username.strip(), relative_path)
        raise HTTPException(401, "Face does not match")

    log_successful_login(username.strip())
    request.session["user"] = username.strip()
    request.session["face_id"] = matched["id"]
    request.session["face_name"] = matched["face_name"]
    return {"status": "ok", "face_name": matched["face_name"]}


@app.get("/api/snapshots/{log_id}")
async def serve_snapshot(log_id: int, request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    from database import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT snapshot_path FROM security_logs WHERE id = ? AND username = ?",
        (log_id, username),
    ).fetchone()
    conn.close()
    if not row or not row["snapshot_path"]:
        raise HTTPException(404, "Snapshot not found")
    filepath = os.path.join(os.path.dirname(__file__), row["snapshot_path"])
    if not os.path.exists(filepath):
        raise HTTPException(404, "Snapshot file not found")
    return FileResponse(filepath, media_type="image/jpeg")


@app.get("/api/me")
async def get_me(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {
        "username": username,
        "face_id": request.session.get("face_id"),
        "face_name": request.session.get("face_name"),
    }


@app.get("/api/notifications")
async def notifications(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {"notifications": get_notifications(username)}


@app.post("/api/notifications/dismiss")
async def dismiss(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    dismiss_notifications(username)
    return {"status": "ok"}


@app.get("/api/history")
async def history(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {"history": get_user_history(username)}


@app.get("/api/faces")
async def list_faces(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {"faces": get_faces(username)}


@app.post("/api/faces")
async def add_face(request: Request, face_name: str = Form("Face 1"), face: UploadFile = None):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    if not face:
        raise HTTPException(400, "No face image provided")

    image_bytes = await face.read()
    try:
        encoding = encode_face(image_bytes)
    except ValueError as e:
        raise HTTPException(400, str(e))

    face_id = save_face(username, face_name.strip() or "Face 1", encoding)
    return {"status": "ok", "id": face_id}


@app.put("/api/faces/{face_id}")
async def rename_face(face_id: int, request: Request, face_name: str = Form(...)):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    if not get_face_by_id(face_id, username):
        raise HTTPException(404, "Face not found")
    update_face_name(face_id, username, face_name.strip())
    return {"status": "ok"}


@app.delete("/api/faces/{face_id}")
async def remove_face(face_id: int, request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    if not get_face_by_id(face_id, username):
        raise HTTPException(404, "Face not found")
    all_faces = get_faces(username)
    if len(all_faces) <= 1:
        raise HTTPException(400, "Cannot delete the last face. Register another face first.")
    delete_face(face_id, username)
    return {"status": "ok"}


@app.get("/api/network-info")
async def network_info(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
    }


@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


@app.get("/api/block/domains")
async def list_blocked_domains(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {"domains": get_blocked_domains()}


@app.post("/api/block/domains")
async def block_domain(request: Request, domain: str = Form(...)):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    if not domain.strip():
        raise HTTPException(400, "Domain is required")
    db_id = add_blocked_domain(domain.strip())
    if not db_id:
        raise HTTPException(409, "Domain already blocked")
    ok, msg = apply_domain_block(domain.strip())
    return {"status": "ok" if ok else "partial", "message": msg, "id": db_id}


@app.delete("/api/block/domains/{domain_id}")
async def unblock_domain(domain_id: int, request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    domains = get_blocked_domains()
    target = next((d for d in domains if d["id"] == domain_id), None)
    if not target:
        raise HTTPException(404, "Domain not found")
    remove_blocked_domain_by_id(domain_id)
    ok, msg = remove_domain_block(target["domain"])
    return {"status": "ok", "message": msg}


@app.get("/api/block/ips")
async def list_blocked_ips(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return {"ips": get_blocked_ips()}


@app.post("/api/block/ips")
async def block_ip(request: Request, ip: str = Form(...), port: int = Form(None), protocol: str = Form("tcp")):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    if not ip.strip():
        raise HTTPException(400, "IP address is required")
    db_id = add_blocked_ip(ip.strip(), port, protocol)
    ok, msg = apply_ip_block(ip.strip(), port, protocol)
    return {"status": "ok" if ok else "partial", "message": msg, "id": db_id}


@app.delete("/api/block/ips/{ip_id}")
async def unblock_ip(ip_id: int, request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    ips = get_blocked_ips()
    target = next((i for i in ips if i["id"] == ip_id), None)
    if not target:
        raise HTTPException(404, "IP rule not found")
    remove_blocked_ip_by_id(ip_id)
    ok, msg = remove_ip_block(target["ip"], target["port"], target["protocol"])
    return {"status": "ok", "message": msg}


@app.get("/api/firewall/status")
async def firewall_status(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not logged in")
    return get_firewall_status()
