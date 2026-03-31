"""Script de teste do fluxo JWT: login → /auth/me/ → endpoint protegido."""
import urllib.request
import json
import urllib.error

BASE = "http://127.0.0.1:8000"

def post_json(url, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def get_json(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

if __name__ == "__main__":
    print("=" * 50)
    print("TESTE DO SISTEMA JWT")
    print("=" * 50)

    # 1. Login
    try:
        data = post_json(BASE + "/api/auth/login/", {"username": "admin", "password": "admin123"})
        access = data["access"]
        refresh = data["refresh"]
        print("[OK] POST /api/auth/login/")
        print(f"     access : {access[:40]}...")
        print(f"     refresh: {refresh[:40]}...")
    except urllib.error.HTTPError as e:
        print(f"[ERRO] Login falhou: {e.code} {e.read().decode()}")
        exit(1)

    # 2. /auth/me/
    try:
        me = get_json(BASE + "/api/auth/me/", token=access)
        print("[OK] GET /api/auth/me/")
        print(json.dumps(me, indent=4, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"[ERRO] /auth/me/ falhou: {e.code} {e.read().decode()}")

    # 3. Endpoint protegido SEM token (deve retornar 401)
    try:
        get_json(BASE + "/api/empresas/")
        print("[FALHA] /api/empresas/ deveria exigir token!")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("[OK] GET /api/empresas/ sem token → 401 Unauthorized (protegido!)")
        else:
            print(f"[INESPERADO] Código {e.code}")

    # 4. Endpoint protegido COM token (deve retornar 200)
    try:
        empresas_resp = get_json(BASE + "/api/empresas/", token=access)
        if isinstance(empresas_resp, list):
            count = len(empresas_resp)
        else:
            count = empresas_resp.get("count", len(empresas_resp.get("results", [])))
        print(f"[OK] GET /api/empresas/ com token → 200 OK ({count} empresas)")
    except urllib.error.HTTPError as e:
        print(f"[ERRO] /api/empresas/ com token falhou: {e.code} {e.read().decode()}")

    print("=" * 50)
    print("TODOS OS TESTES CONCLUIDOS")
    print("=" * 50)
