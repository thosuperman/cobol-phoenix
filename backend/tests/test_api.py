import io
import zipfile


def test_health(api_client):
    r = api_client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_sample_import_analysis_rules_generation_download(api_client):
    p = api_client.post("/api/projects/sample").json()
    pid = p["id"]
    assert p["overview"]["programs"] == 3
    a = api_client.get(f"/api/projects/{pid}/analysis").json()
    assert {x["program_id"] for x in a["programs"]} == {"PREMCALC", "RATEENG", "AUDITLOG"}
    assert api_client.get(f"/api/projects/{pid}/graph").json()["nodes"]
    src = api_client.get(f"/api/projects/{pid}/files/content", params={"path": "cobol/RATEENG.cbl"}).json()
    assert "PROGRAM-ID. RATEENG." in src["text"]
    rules = api_client.get(f"/api/projects/{pid}/rules").json()
    assert rules and all(r["verification"]["status"] in ("NOT_RUN", "UNSUPPORTED") for r in rules)
    exp = api_client.post(f"/api/projects/{pid}/rules/{rules[1]['id']}/explain").json()
    assert exp["provider"] == "deterministic" and not exp["advisory"]
    g = api_client.post(f"/api/projects/{pid}/generations", json={"entry": "RATEENG"})
    assert g.status_code == 201
    gid = g.json()["id"]
    detail = api_client.get(f"/api/generations/{gid}").json()
    assert detail["interface"]["mode"] == "linkage" and "class RateengRequest" in detail["schemas"]
    f = api_client.get(f"/api/generations/{gid}/file", params={"path": "app/programs/rateeng.py"}).json()
    assert "class ProgramRateeng" in f["text"]
    z = api_client.get(f"/api/generations/{gid}/download")
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "rateeng-service/app/main.py" in names and "rateeng-service/traceability.json" in names
    for kind in ("rules.md", "rules.json", "graph.json", "migration-report.md", "traceability.json"):
        assert api_client.get(f"/api/projects/{pid}/export/{kind}").status_code == 200
    assert api_client.get(f"/api/projects/{pid}/export/verification-report.md").status_code == 404


def test_errors_and_validation(api_client):
    assert api_client.get("/api/projects/nope").status_code == 404
    pid = api_client.post("/api/projects/sample").json()["id"]
    assert api_client.post(f"/api/projects/{pid}/generations", json={"entry": "NOPE"}).status_code == 404
    assert api_client.post(f"/api/projects/{pid}/generations", json={"entry": "bad name!"}).status_code == 422
    assert api_client.put(f"/api/projects/{pid}/fixtures", json={"RATEENG": [{"x": 1}]}).status_code == 400
    assert api_client.get(f"/api/projects/{pid}/files/content", params={"path": "../../etc/passwd"}).status_code == 404


def test_upload_files(api_client):
    files = [
        (
            "files",
            (
                "A.cob",
                b"       IDENTIFICATION DIVISION.\n       PROGRAM-ID. A.\n       PROCEDURE DIVISION.\n           DISPLAY 'HI'\n           STOP RUN.\n",
                "text/plain",
            ),
        )
    ]
    r = api_client.post("/api/projects/upload", files=files, data={"name": "tiny"})
    assert r.status_code == 201, r.text
    assert r.json()["overview"]["programs"] == 1


def test_deleting_a_project(api_client):
    pid = api_client.post("/api/projects/sample").json()["id"]
    assert api_client.delete(f"/api/projects/{pid}").status_code == 204
    assert api_client.get(f"/api/projects/{pid}").status_code == 404
