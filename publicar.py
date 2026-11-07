"""Publica/agenda os Shorts do Manual do Burro no Zernio a partir de posts.json.
Uso: ZERNIO_API_KEY=... python publicar.py [--dry-run] [--so ID]"""
import json, os, sys, uuid, urllib.request

API = "https://zernio.com/api/v1"
RAW = "https://raw.githubusercontent.com/TonyWatanabe-dev/manualdoburro-midia/main/"
KEY = os.environ["ZERNIO_API_KEY"]
DRY = "--dry-run" in sys.argv or os.environ.get("TESTE") == "true"
SO = sys.argv[sys.argv.index("--so") + 1] if "--so" in sys.argv else os.environ.get("SO", "")

def call(method, path, body=None, headers=None):
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:800]

st, data = call("GET", "/accounts")
accounts = data.get("accounts", []) if isinstance(data, dict) else []
print("Contas encontradas:", [(a.get("platform"), a.get("username") or a.get("displayName")) for a in accounts])
alvo = {}
for a in accounts:
    nome = f'{a.get("username","")} {a.get("displayName","")}'.lower().replace(" ", "").replace(".", "").replace("_", "")
    if "manualdoburro" in nome and a.get("platform") in ("youtube", "tiktok", "instagram"):
        alvo[a["platform"]] = a.get("_id") or a.get("id")
if not alvo: sys.exit("Nenhuma conta do Manual do Burro encontrada nesta chave do Zernio.")
print("Publicando em:", sorted(alvo))

for p in json.load(open("posts.json", encoding="utf-8")):
    if SO and p["id"] != SO: continue
    plats = []
    for plat, acc in alvo.items():
        e = {"platform": plat, "accountId": acc}
        if plat == "youtube": e["platformSpecificData"] = {"title": p["titulo_youtube"], "visibility": "public"}
        if plat == "instagram": e["platformSpecificData"] = {"firstComment": p["comentario_fixado"]}
        plats.append(e)
    media = {"type": "video", "url": RAW + p["video"], "thumbnail": RAW + p["capa"], "instagramThumbnail": RAW + p["capa"]}
    body = {"content": p["legenda"], "mediaItems": [media], "platforms": plats}
    if "tiktok" in alvo:
        body["tiktokSettings"] = {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": True,
                                  "allow_stitch": True, "content_preview_confirmed": True, "express_consent_given": True}
    if p["quando"] == "agora": body["publishNow"] = True
    else: body["scheduledFor"], body["timezone"] = p["quando"], "America/Sao_Paulo"
    if DRY:
        print(f'[teste] {p["id"]} -> {p["quando"]} em {sorted(alvo)}'); continue
    chave = str(uuid.uuid5(uuid.NAMESPACE_URL, RAW + p["video"]))
    st, r = call("POST", "/posts", body, {"Idempotency-Key": chave})
    print(p["id"], st, (r.get("post", {}).get("status") if isinstance(r, dict) else r))
