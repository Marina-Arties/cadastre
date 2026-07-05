class TestAuthAPI:
    async def test_register(self, client):
        resp = await client.post("/api/auth/register", json={
            "email": "newuser@test.com",
            "password": "Password1",
            "nickname": "newuser",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["nickname"] == "newuser"

    async def test_register_duplicate_email(self, client):
        await client.post("/api/auth/register", json={
            "email": "dup@test.com",
            "password": "Password1",
            "nickname": "user1",
        })
        resp = await client.post("/api/auth/register", json={
            "email": "dup@test.com",
            "password": "Password1",
            "nickname": "user2",
        })
        assert resp.status_code == 400

    async def test_register_duplicate_nickname(self, client):
        await client.post("/api/auth/register", json={
            "email": "one@test.com",
            "password": "Password1",
            "nickname": "dupnick",
        })
        resp = await client.post("/api/auth/register", json={
            "email": "two@test.com",
            "password": "Password1",
            "nickname": "dupnick",
        })
        assert resp.status_code == 400

    async def test_register_weak_password(self, client):
        resp = await client.post("/api/auth/register", json={
            "email": "weak@test.com",
            "password": "alllowercase",
            "nickname": "weakpw",
        })
        assert resp.status_code == 400

    async def test_login_success(self, client):
        await client.post("/api/auth/register", json={
            "email": "login@test.com",
            "password": "Login123",
            "nickname": "logintest",
        })
        resp = await client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "Login123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "email": "wrongpw@test.com",
            "password": "Right123",
            "nickname": "wrongpwuser",
        })
        resp = await client.post("/api/auth/login", json={
            "email": "wrongpw@test.com",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    async def test_get_me(self, client, auth_headers):
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@test.com"
        assert data["nickname"] == "testuser"

    async def test_get_me_unauthorized(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401


class TestProfileAPI:
    async def test_get_profile(self, client, auth_headers):
        resp = await client.get("/api/users/me/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "properties_count" in data
        assert "rating" in data

    async def test_update_profile(self, client, auth_headers):
        resp = await client.put("/api/users/me/profile", json={
            "full_name": "Test User",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Test User"

    async def test_check_add_no_duplicate(self, client, auth_headers):
        resp = await client.get(
            "/api/users/me/check-add?address=уникальный адрес 12345",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() is True
