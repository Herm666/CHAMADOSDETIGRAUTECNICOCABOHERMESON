#!/usr/bin/env python3
"""
TI Suporte — Backend API com Autenticação
Banco: PostgreSQL (Railway) ou SQLite (local)
Porta: env PORT ou 5000
"""
import json, os, sys, hashlib, secrets
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 5000))
DATABASE_URL = os.environ.get("DATABASE_URL", "")  # Railway injeta isso automaticamente
USE_PG = bool(DATABASE_URL)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
sessions = {}  # token -> {id, nome, username, role}

DEFAULT_USERS = [
    {"nome": "HermesonTI",         "username": "hermeson", "senha": "admin123",    "role": "gestor"},
    {"nome": "Emanoel Estagiário",  "username": "emanoel",  "senha": "emanoel123",  "role": "tecnico"},
    {"nome": "Ghabriel Estagiário", "username": "ghabriel", "senha": "ghabriel123", "role": "tecnico"},
]

def sha(s): return hashlib.sha256(s.encode()).hexdigest()


# ── Camada de banco dual (PostgreSQL / SQLite) ─────────────────

class DB:
    """
    Abstrai diferenças entre psycopg2 (pg) e sqlite3.
    - placeholder: %s (pg) vs ? (sqlite)
    - SERIAL vs AUTOINCREMENT
    - row como dict
    """
    def __init__(self):
        if USE_PG:
            import psycopg2
            import psycopg2.extras
            self._pg  = psycopg2
            self._ext = psycopg2.extras
            self.ph   = "%s"          # placeholder
            self._conn = None
        else:
            import sqlite3
            self._sq = sqlite3
            self.ph  = "?"
            _base = os.path.join(os.path.dirname(__file__), "data")
            os.makedirs(_base, exist_ok=True)
            self._path = os.path.join(_base, "chamados.db")

    def conn(self):
        if USE_PG:
            c = self._pg.connect(DATABASE_URL, cursor_factory=self._ext.RealDictCursor)
            c.autocommit = False
            return c
        else:
            import sqlite3
            c = sqlite3.connect(self._path)
            c.row_factory = sqlite3.Row
            return c

    def fetchall(self, conn, sql, params=()):
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def fetchone(self, conn, sql, params=()):
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def execute(self, conn, sql, params=()):
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur

    def lastrowid(self, cur, table="chamados"):
        if USE_PG:
            return cur.fetchone()["id"]
        return cur.lastrowid

db = DB()
ph = db.ph   # shortcut


def init_db():
    if USE_PG:
        serial  = "SERIAL PRIMARY KEY"
        autostr = ""
    else:
        serial  = "INTEGER PRIMARY KEY AUTOINCREMENT"
        autostr = ""

    conn = db.conn()
    c = conn.cursor()

    c.execute(f"""CREATE TABLE IF NOT EXISTS usuarios (
        id        {serial},
        nome      TEXT NOT NULL,
        username  TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        role      TEXT NOT NULL DEFAULT 'tecnico'
    )""")

    c.execute(f"""CREATE TABLE IF NOT EXISTS chamados (
        id         {serial},
        nome       TEXT NOT NULL,
        setor      TEXT NOT NULL,
        assunto    TEXT NOT NULL,
        descricao  TEXT DEFAULT '',
        prioridade TEXT NOT NULL DEFAULT 'Baixa',
        status     TEXT NOT NULL DEFAULT 'Aberto',
        tecnico    TEXT DEFAULT '',
        data       TEXT NOT NULL,
        data_iso   TEXT NOT NULL,
        updated_at TEXT
    )""")

    conn.commit()

    # Seed usuários padrão
    for u in DEFAULT_USERS:
        row = db.fetchone(conn, f"SELECT id FROM usuarios WHERE username={ph}", (u["username"],))
        if not row:
            db.execute(conn, f"INSERT INTO usuarios (nome,username,senha_hash,role) VALUES ({ph},{ph},{ph},{ph})",
                       (u["nome"], u["username"], sha(u["senha"]), u["role"]))
    conn.commit()
    conn.close()
    print(f"[DB] {'PostgreSQL' if USE_PG else 'SQLite'} inicializado")


def row_to_dict(row):
    d = dict(row)
    d["dataISO"]   = d.pop("data_iso",   "") or ""
    d["updatedAt"] = d.pop("updated_at", "") or ""
    # Garante que id é int
    if "id" in d: d["id"] = int(d["id"])
    return d


def require_auth(handler):
    h = handler.headers.get("Authorization", "")
    return sessions.get(h[7:]) if h.startswith("Bearer ") else None


# ── HTTP Handler ───────────────────────────────────────────────

class APIHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} {fmt%args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()
        self.wfile.write(body)

    def err(self, s, m): self.send_json({"error": m}, s)

    def body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_OPTIONS(self): self.send_json({})

    # ── POST ──────────────────────────────────────────────────
    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "/api/auth/login":
            d = self.body()
            username = d.get("username", "").strip().lower()
            senha    = d.get("senha", "")
            if not username or not senha:
                return self.err(400, "Informe usuário e senha")
            conn = db.conn()
            row = db.fetchone(conn, f"SELECT * FROM usuarios WHERE username={ph} AND senha_hash={ph}",
                              (username, sha(senha)))
            conn.close()
            if not row: return self.err(401, "Usuário ou senha incorretos")
            token = secrets.token_hex(32)
            sess  = {"id": int(row["id"]), "nome": row["nome"],
                     "username": row["username"], "role": row["role"]}
            sessions[token] = sess
            print(f"[AUTH] Login: {row['nome']} ({row['role']})")
            return self.send_json({"token": token, **sess})

        if path == "/api/auth/logout":
            h = self.headers.get("Authorization", "")
            if h.startswith("Bearer "): sessions.pop(h[7:], None)
            return self.send_json({"ok": True})

        # Criar chamado — público
        if path == "/api/chamados":
            d = self.body()
            for f in ["nome", "setor", "assunto"]:
                if not d.get(f, "").strip(): return self.err(400, f"Campo obrigatório: {f}")
            now = datetime.now()
            conn = db.conn()
            if USE_PG:
                cur = db.execute(conn, f"""
                    INSERT INTO chamados (nome,setor,assunto,descricao,prioridade,status,tecnico,data,data_iso)
                    VALUES ({ph},{ph},{ph},{ph},{ph},'Aberto','',{ph},{ph}) RETURNING id""",
                    (d["nome"].strip(), d["setor"].strip(), d["assunto"].strip(),
                     d.get("descricao","").strip(), d.get("prioridade","Baixa"),
                     now.strftime("%d/%m/%Y %H:%M"), now.isoformat()))
                new_id = db.lastrowid(cur)
            else:
                cur = db.execute(conn, f"""
                    INSERT INTO chamados (nome,setor,assunto,descricao,prioridade,status,tecnico,data,data_iso)
                    VALUES ({ph},{ph},{ph},{ph},{ph},'Aberto','',{ph},{ph})""",
                    (d["nome"].strip(), d["setor"].strip(), d["assunto"].strip(),
                     d.get("descricao","").strip(), d.get("prioridade","Baixa"),
                     now.strftime("%d/%m/%Y %H:%M"), now.isoformat()))
                new_id = cur.lastrowid
            conn.commit()
            row = db.fetchone(conn, f"SELECT * FROM chamados WHERE id={ph}", (new_id,))
            conn.close()
            print(f"[API] Novo chamado #{new_id}: {d['assunto']}")
            return self.send_json(row_to_dict(row), 201)

        self.err(404, "Rota não encontrada")

    # ── GET ───────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        qs     = parse_qs(parsed.query)

        # Arquivos estáticos (frontend)
        if path == "" or path == "/" or not path.startswith("/api"):
            fname = "login.html" if path in ("", "/") else path.lstrip("/")
            fpath = os.path.join(FRONTEND_DIR, fname)
            if os.path.isfile(fpath):
                ext  = fname.rsplit(".", 1)[-1]
                mime = {"html":"text/html","css":"text/css","js":"application/javascript"}.get(ext,"text/plain")
                with open(fpath, "rb") as f: body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime+"; charset=utf-8")
                self.send_header("Content-Length", len(body))
                self.end_headers()
                self.wfile.write(body)
                return
            return self.err(404, "Arquivo não encontrado")

        if path == "/api/auth/me":
            sess = require_auth(self)
            return self.send_json(sess) if sess else self.err(401, "Não autenticado")

        sess = require_auth(self)
        if not sess: return self.err(401, "Não autenticado")

        if path == "/api/chamados":
            conn = db.conn()
            q, p = "SELECT * FROM chamados WHERE 1=1", []
            if "status"    in qs: q+=f" AND status={ph}";     p.append(qs["status"][0])
            if "prioridade"in qs: q+=f" AND prioridade={ph}"; p.append(qs["prioridade"][0])
            if "tecnico"   in qs: q+=f" AND tecnico={ph}";    p.append(qs["tecnico"][0])
            if "setor"     in qs: q+=f" AND setor={ph}";      p.append(qs["setor"][0])
            if "q" in qs:
                t = f"%{qs['q'][0]}%"
                q += f" AND (nome LIKE {ph} OR assunto LIKE {ph} OR descricao LIKE {ph})"
                p += [t, t, t]
            q += " ORDER BY id DESC"
            if "limit" in qs: q+=f" LIMIT {ph}"; p.append(int(qs["limit"][0]))
            rows = db.fetchall(conn, q, p)
            conn.close()
            return self.send_json([row_to_dict(r) for r in rows])

        if path == "/api/chamados/stats":
            if sess["role"] != "gestor": return self.err(403, "Acesso restrito ao gestor")
            conn = db.conn()
            stats = {"total": db.fetchone(conn, "SELECT COUNT(*) AS n FROM chamados")["n"]}
            for r in db.fetchall(conn, "SELECT status, COUNT(*) AS n FROM chamados GROUP BY status"):
                stats[r["status"]] = r["n"]
            stats["porPrioridade"] = {r["prioridade"]: r["n"] for r in
                db.fetchall(conn, "SELECT prioridade, COUNT(*) AS n FROM chamados GROUP BY prioridade")}
            stats["porSetor"] = {r["setor"]: r["n"] for r in
                db.fetchall(conn, "SELECT setor, COUNT(*) AS n FROM chamados GROUP BY setor")}
            stats["porTecnico"] = {r["tecnico"]: r["n"] for r in
                db.fetchall(conn, f"SELECT tecnico, COUNT(*) AS n FROM chamados WHERE tecnico!={ph} GROUP BY tecnico", ("",))}
            conn.close()
            return self.send_json(stats)

        if path.startswith("/api/chamados/"):
            try: cid = int(path.split("/")[-1])
            except: return self.err(400, "ID inválido")
            conn = db.conn()
            row  = db.fetchone(conn, f"SELECT * FROM chamados WHERE id={ph}", (cid,))
            conn.close()
            return self.send_json(row_to_dict(row)) if row else self.err(404, "Não encontrado")

        if path == "/api/usuarios":
            if sess["role"] != "gestor": return self.err(403, "Acesso restrito")
            conn = db.conn()
            rows = db.fetchall(conn, "SELECT id,nome,username,role FROM usuarios")
            conn.close()
            return self.send_json(rows)

        self.err(404, "Rota não encontrada")

    # ── PUT ───────────────────────────────────────────────────
    def do_PUT(self):
        path = urlparse(self.path).path.rstrip("/")
        sess = require_auth(self)
        if not sess: return self.err(401, "Não autenticado")

        if path.startswith("/api/chamados/"):
            try: cid = int(path.split("/")[-1])
            except: return self.err(400, "ID inválido")
            d = self.body()
            conn = db.conn()
            row = db.fetchone(conn, f"SELECT * FROM chamados WHERE id={ph}", (cid,))
            if not row:
                conn.close(); return self.err(404, "Não encontrado")
            if sess["role"] == "tecnico":
                dono = row.get("tecnico") or ""
                if dono and dono != sess["nome"]:
                    conn.close()
                    return self.err(403, "Este chamado pertence a outro técnico")
            allowed = {"tecnico","status","assunto","descricao","prioridade"}
            updates = {k: v for k, v in d.items() if k in allowed}
            if not updates:
                conn.close(); return self.err(400, "Nenhum campo válido")
            updates["updated_at"] = datetime.now().isoformat()
            set_cl = ", ".join(f"{k}={ph}" for k in updates)
            db.execute(conn, f"UPDATE chamados SET {set_cl} WHERE id={ph}",
                       list(updates.values()) + [cid])
            conn.commit()
            updated = db.fetchone(conn, f"SELECT * FROM chamados WHERE id={ph}", (cid,))
            conn.close()
            print(f"[API] #{cid} atualizado por {sess['nome']}: {updates}")
            return self.send_json(row_to_dict(updated))

        self.err(404, "Rota não encontrada")

    # ── DELETE ────────────────────────────────────────────────
    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        sess = require_auth(self)
        if not sess or sess["role"] != "gestor":
            return self.err(403, "Acesso restrito ao gestor")
        if path.startswith("/api/chamados/"):
            try: cid = int(path.split("/")[-1])
            except: return self.err(400, "ID inválido")
            conn = db.conn()
            if not db.fetchone(conn, f"SELECT id FROM chamados WHERE id={ph}", (cid,)):
                conn.close(); return self.err(404, "Não encontrado")
            db.execute(conn, f"DELETE FROM chamados WHERE id={ph}", (cid,))
            conn.commit(); conn.close()
            print(f"[API] #{cid} deletado por {sess['nome']}")
            return self.send_json({"deleted": cid})
        self.err(404, "Rota não encontrada")


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    modo = "PostgreSQL (Railway)" if USE_PG else "SQLite (local)"
    print(f"""
  ╔══════════════════════════════════════════╗
  ║   TI Suporte — Backend com Auth          ║
  ║   http://localhost:{PORT}                 ║
  ║   Banco: {modo:<32}║
  ╚══════════════════════════════════════════╝

  Credenciais padrão:
    gestor:  hermeson  / admin123
    técnico: emanoel   / emanoel123
    técnico: ghabriel  / ghabriel123

  Aguardando... (Ctrl+C para parar)
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Encerrado.")
        sys.exit(0)
