MOVIE = {"title": "Dune", "genre": "Sci-Fi", "release_date": "2024-03-01", "budget_usd": 1000}


def create_movie(client, **overrides):
    resp = client.post("/movies", json={**MOVIE, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


def report(day="2024-03-05", region="US", revenue=500, tickets=50):
    return {"report_date": day, "region": region, "revenue_usd": revenue, "tickets_sold": tickets}


def test_register_and_login(client):
    creds = {"email": "a@b.com", "password": "password1"}
    assert client.post("/auth/register", json=creds).status_code == 201
    resp = client.post("/auth/login", json=creds)
    assert resp.status_code == 200 and resp.json()["access_token"]


def test_register_duplicate_email_conflict(client):
    creds = {"email": "a@b.com", "password": "password1"}
    client.post("/auth/register", json=creds)
    assert client.post("/auth/register", json=creds).status_code == 409


def test_register_invalid_email_400(client):
    assert client.post("/auth/register", json={"email": "bad", "password": "password1"}).status_code == 400


def test_login_wrong_password_401(client):
    client.post("/auth/register", json={"email": "a@b.com", "password": "password1"})
    assert client.post("/auth/login", json={"email": "a@b.com", "password": "nope-nope"}).status_code == 401


def test_protected_endpoints_require_token(client):
    for method, url in [("get", "/movies"), ("post", "/movies"), ("get", "/analytics/top"),
                        ("delete", "/reports/1"), ("get", "/movies/1/summary")]:
        assert getattr(client, method)(url).status_code == 401, url


def test_garbage_token_401(client):
    assert client.get("/movies", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_movie_crud(auth_client):
    movie = create_movie(auth_client)
    assert auth_client.get(f"/movies/{movie['id']}").json()["title"] == "Dune"
    upd = auth_client.put(f"/movies/{movie['id']}", json={**MOVIE, "title": "Dune: Part Two"})
    assert upd.status_code == 200 and upd.json()["title"] == "Dune: Part Two"
    assert auth_client.delete(f"/movies/{movie['id']}").status_code == 204
    assert auth_client.get(f"/movies/{movie['id']}").status_code == 404


def test_movie_invalid_data_400(auth_client):
    assert auth_client.post("/movies", json={**MOVIE, "budget_usd": 0}).status_code == 400
    assert auth_client.post("/movies", json={**MOVIE, "title": "  "}).status_code == 400
    assert auth_client.post("/movies", json={"title": "x"}).status_code == 400


def test_movie_duplicate_409(auth_client):
    create_movie(auth_client)
    assert auth_client.post("/movies", json=MOVIE).status_code == 409


def test_movie_not_found_404(auth_client):
    assert auth_client.get("/movies/999").status_code == 404
    assert auth_client.put("/movies/999", json=MOVIE).status_code == 404
    assert auth_client.delete("/movies/999").status_code == 404


def test_movie_filters(auth_client):
    create_movie(auth_client)
    create_movie(auth_client, title="Barbie", genre="Comedy", release_date="2023-07-21")
    assert len(auth_client.get("/movies", params={"genre": "Comedy"}).json()) == 1
    assert len(auth_client.get("/movies", params={"year": 2024}).json()) == 1
    assert auth_client.get("/movies", params={"limit": 0}).status_code == 400


def test_report_lifecycle(auth_client):
    mid = create_movie(auth_client)["id"]
    created = auth_client.post(f"/movies/{mid}/reports", json=report(region="us"))
    assert created.status_code == 201 and created.json()["region"] == "US"
    rid = created.json()["id"]
    upd = auth_client.put(f"/reports/{rid}", json={"revenue_usd": 700, "tickets_sold": 70})
    assert upd.json()["revenue_usd"] == 700
    assert len(auth_client.get(f"/movies/{mid}/reports").json()) == 1
    assert auth_client.delete(f"/reports/{rid}").status_code == 204
    assert auth_client.get(f"/movies/{mid}/reports").json() == []


def test_report_invariants(auth_client):
    mid = create_movie(auth_client)["id"]
    url = f"/movies/{mid}/reports"
    assert auth_client.post(url, json=report(day="2024-02-01")).status_code == 400
    assert auth_client.post(url, json=report(day="2999-01-01")).status_code == 400
    assert auth_client.post(url, json=report(revenue=-5)).status_code == 400
    assert auth_client.post(url, json=report(region="USA")).status_code == 400


def test_report_duplicate_409_and_missing_movie_404(auth_client):
    mid = create_movie(auth_client)["id"]
    assert auth_client.post(f"/movies/{mid}/reports", json=report()).status_code == 201
    assert auth_client.post(f"/movies/{mid}/reports", json=report()).status_code == 409
    assert auth_client.post("/movies/999/reports", json=report()).status_code == 404


def test_report_filters(auth_client):
    mid = create_movie(auth_client)["id"]
    for day, region in [("2024-03-05", "US"), ("2024-03-06", "US"), ("2024-03-06", "UA")]:
        auth_client.post(f"/movies/{mid}/reports", json=report(day=day, region=region))
    url = f"/movies/{mid}/reports"
    assert len(auth_client.get(url, params={"region": "ua"}).json()) == 1
    assert len(auth_client.get(url, params={"date_from": "2024-03-06"}).json()) == 2


def test_summary_and_top(auth_client):
    a = create_movie(auth_client)["id"]
    b = create_movie(auth_client, title="Barbie", release_date="2024-01-01", budget_usd=200)["id"]
    auth_client.post(f"/movies/{a}/reports", json=report(day="2024-03-05", region="US", revenue=1500, tickets=100))
    auth_client.post(f"/movies/{a}/reports", json=report(day="2024-03-05", region="UA", revenue=500, tickets=50))
    auth_client.post(f"/movies/{b}/reports", json=report(day="2024-02-01", region="US", revenue=300, tickets=30))

    summary = auth_client.get(f"/movies/{a}/summary").json()
    assert summary["total_revenue_usd"] == 2000
    assert summary["total_tickets"] == 150
    assert summary["avg_ticket_price_usd"] == 13.33
    assert summary["roi"] == 1.0
    assert summary["revenue_by_region"][0] == {"region": "US", "revenue_usd": 1500}

    top = auth_client.get("/analytics/top", params={"limit": 1}).json()
    assert [t["title"] for t in top] == ["Dune"]

    regions = auth_client.get("/analytics/regions").json()
    assert regions == [{"region": "US", "revenue_usd": 1800}, {"region": "UA", "revenue_usd": 500}]


def test_summary_without_reports(auth_client):
    mid = create_movie(auth_client)["id"]
    s = auth_client.get(f"/movies/{mid}/summary").json()
    assert s["total_revenue_usd"] == 0 and s["avg_ticket_price_usd"] is None and s["roi"] == -1.0
    assert auth_client.get("/movies/999/summary").status_code == 404
