import os, sqlite3, hashlib, secrets, json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import nlp
BASE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(BASE, "..", "database", "newssense.db"); UP = os.path.join(BASE, "uploads")
ALLOWED = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}; MAX_MB = 50
app = FastAPI(title="NewsSense")
def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
with db() as c:
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password_hash TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INT);
    CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY,user_id INT,title TEXT,text TEXT,source TEXT,analysis TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
def hp(pw, salt=None):
    salt = salt or secrets.token_hex(8); return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120000).hex()
def user(authorization: str = Header(None)):
    r = db().execute("SELECT user_id FROM sessions WHERE token=?", ((authorization or "").replace("Bearer ", ""),)).fetchone()
    if not r: raise HTTPException(401, "Please log in to continue.")
    return r[0]
class Reg(BaseModel): name: str; email: EmailStr; password: str
class Log(BaseModel): email: EmailStr; password: str

@app.post("/api/auth/register")
def register(b: Reg):
    if len(b.password) < 8: raise HTTPException(400, "Password must be at least 8 characters.")
    try:
        with db() as c: c.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (b.name.strip(), b.email.lower(), hp(b.password)))
    except sqlite3.IntegrityError: raise HTTPException(400, "An account with this email already exists.")
    return {"ok": True}
@app.post("/api/auth/login")
def login(b: Log):
    r = db().execute("SELECT * FROM users WHERE email=?", (b.email.lower(),)).fetchone()
    if not r or hp(b.password, r["password_hash"].split("$")[0]) != r["password_hash"]: raise HTTPException(401, "Incorrect email or password.")
    t = secrets.token_urlsafe(32)
    with db() as c: c.execute("INSERT INTO sessions VALUES(?,?)", (t, r["id"]))
    return {"token": t, "name": r["name"]}
@app.post("/api/auth/logout")
def logout(authorization: str = Header(None)):
    with db() as c: c.execute("DELETE FROM sessions WHERE token=?", ((authorization or "").replace("Bearer ", ""),))
    return {"ok": True}

SAMPLE = """Government announces record investment in renewable energy. The finance minister said on Monday that the government will invest 2.5 billion dollars in solar and wind projects over the next five years. Officials said the plan will create more than 40,000 jobs and cut carbon emissions by 20 percent by 2030. Opposition leaders criticised the plan, warning that rising costs could increase pressure on taxpayers. Industry groups welcomed the move, saying it will boost growth and attract foreign investors. Analysts at the Reserve Bank noted that the announcement lifted energy shares, which gained 3 percent in early trading. The minister added that work on the first solar park will begin in March."""
def recognize(path):
    try: from faster_whisper import WhisperModel
    except ImportError: return None
    segs, _ = WhisperModel("base", compute_type="int8").transcribe(path)
    return " ".join(s.text for s in segs).strip()

@app.post("/api/analyze")
async def analyze(title: str = Form(""), text: str = Form(""), file: UploadFile | None = File(None), uid: int = Depends(user)):
    src = "text"
    if not text.strip():
        if not file: raise HTTPException(400, "Paste a news article or upload a news audio clip.")
        ext = os.path.splitext(file.filename or "")[1].lower(); data = await file.read()
        if ext not in ALLOWED: raise HTTPException(400, "Unable to process the audio file. Please upload MP3, WAV, M4A, OGG or WEBM.")
        if not data: raise HTTPException(400, "The audio file is empty.")
        if len(data) > MAX_MB * 1048576: raise HTTPException(400, f"File is too large (max {MAX_MB} MB).")
        path = os.path.join(UP, secrets.token_hex(8) + ext); open(path, "wb").write(data)
        try:
            text = recognize(path); src = "whisper"
            if text is None: text, src = SAMPLE, "demo"
        except Exception: raise HTTPException(500, "Speech could not be detected clearly. Please try a recording with better audio quality.")
        finally:
            try: os.remove(path)
            except OSError: pass
    if len(text.split()) < 30: raise HTTPException(400, "The text is too short to analyze. Please provide at least a few sentences (30+ words).")
    a = nlp.analyze(text)
    with db() as c:
        aid = c.execute("INSERT INTO articles(user_id,title,text,source,analysis) VALUES(?,?,?,?,?)", (uid, (title or a["headline"])[:200], text, src, json.dumps(a))).lastrowid
    return {"id": aid, "title": title or a["headline"], "text": text, "source": src, "analysis": a}
@app.get("/api/articles")
def lst(uid: int = Depends(user)):
    rows = db().execute("SELECT * FROM articles WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall(); items = []; topics = {}; sent = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for r in rows:
        a = json.loads(r["analysis"]); top = a["topics"][0]["topic"]; topics[top] = topics.get(top, 0) + 1; sent[a["sentiment"]["label"]] += 1
        items.append({"id": r["id"], "title": r["title"], "source": r["source"], "created_at": r["created_at"], "topic": top, "sentiment": a["sentiment"]["label"]})
    return {"items": items, "topics": topics, "sentiment": sent}
@app.get("/api/articles/{aid}")
def get(aid: int, uid: int = Depends(user)):
    r = db().execute("SELECT * FROM articles WHERE id=? AND user_id=?", (aid, uid)).fetchone()
    if not r: raise HTTPException(404, "Article not found.")
    return {"id": aid, "title": r["title"], "text": r["text"], "source": r["source"], "analysis": json.loads(r["analysis"])}
@app.delete("/api/articles/{aid}")
def delete(aid: int, uid: int = Depends(user)):
    with db() as c: c.execute("DELETE FROM articles WHERE id=? AND user_id=?", (aid, uid))
    return {"ok": True}
@app.get("/api/sample")
def sample(): return {"text": SAMPLE}
app.mount("/", StaticFiles(directory=os.path.join(BASE, "..", "frontend"), html=True))
