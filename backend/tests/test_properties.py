class TestPropertiesAPI:
    async def test_create_property(self, client, auth_headers):
        resp = await client.post("/api/properties", json={
            "address": "г. Москва, ул. Тверская, д. 1",
            "name": "Дом на Тверской",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Дом на Тверской"
        assert data["address"] == "г. Москва, ул. Тверская, д. 1"

    async def test_create_duplicate_exact(self, client, auth_headers):
        props = {"address": "г. Москва, ул. Ленина, д. 1", "name": "Дом 1"}
        await client.post("/api/properties", json=props, headers=auth_headers)
        resp = await client.post("/api/properties", json=props, headers=auth_headers)
        assert resp.status_code == 409

    async def test_create_duplicate_fuzzy(self, client, auth_headers):
        await client.post("/api/properties", json={
            "address": "г. Москва, ул. Тверская, д. 1",
            "name": "Дом на Тверской",
        }, headers=auth_headers)
        resp = await client.post("/api/properties", json={
            "address": "г. Москва, улица Тверская, дом 1",
            "name": "Тот же дом",
        }, headers=auth_headers)
        assert resp.status_code == 409

    async def test_create_requires_auth(self, client):
        resp = await client.post("/api/properties", json={
            "address": "г. Москва, ул. Арбат, д. 1",
            "name": "Дом на Арбате",
        })
        assert resp.status_code == 401

    async def test_list_properties(self, client, auth_headers):
        await client.post("/api/properties", json={
            "address": "г. Москва, ул. Пушкина, д. 1",
            "name": "Дом Пушкина",
        }, headers=auth_headers)
        resp = await client.get("/api/properties")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_list_with_search(self, client, auth_headers):
        await client.post("/api/properties", json={
            "address": "г. Москва, ул. Уникальная, д. 999",
            "name": "Уникальный дом",
        }, headers=auth_headers)
        resp = await client.get("/api/properties?search=Уникальный")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_search_no_results(self, client, auth_headers):
        resp = await client.get("/api/properties?search=несуществующий12345")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    async def test_update_own_property(self, client, auth_headers):
        create_resp = await client.post("/api/properties", json={
            "address": "г. Москва, ул. Садовая, д. 1",
            "name": "Старое название",
        }, headers=auth_headers)
        prop_id = create_resp.json()["id"]
        resp = await client.put(f"/api/properties/{prop_id}", json={
            "name": "Новое название",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Новое название"

    async def test_delete_own_property(self, client, auth_headers):
        create_resp = await client.post("/api/properties", json={
            "address": "г. Москва, ул. Лесная, д. 1",
            "name": "Лесной дом",
        }, headers=auth_headers)
        prop_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/properties/{prop_id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_cannot_update_others_property(self, client, auth_headers):
        create_resp = await client.post("/api/properties", json={
            "address": "г. Москва, ул. Чужая, д. 1",
            "name": "Чужой дом",
        }, headers=auth_headers)
        prop_id = create_resp.json()["id"]

        reg_resp = await client.post("/api/auth/register", json={
            "email": "other@test.com",
            "password": "OtherUser1",
            "nickname": "otheruser",
        })
        other_token = reg_resp.json()["access_token"]

        resp = await client.put(f"/api/properties/{prop_id}", json={
            "name": "Взлом",
        }, headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403

    async def test_get_my_properties(self, client, auth_headers):
        await client.post("/api/properties", json={
            "address": "г. Москва, ул. Моя, д. 1",
            "name": "Мой дом",
        }, headers=auth_headers)
        resp = await client.get("/api/users/me/properties", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


class TestLeaderboardAPI:
    async def test_leaderboard(self, client, auth_headers):
        await client.post("/api/properties", json={
            "address": "г. Москва, ул. Рейтинговая, д. 1",
            "name": "Рейтинговый дом",
        }, headers=auth_headers)
        resp = await client.get("/api/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1


class TestExportAPI:
    async def test_export_csv(self, client, auth_headers):
        await client.post("/api/properties", json={
            "address": "г. Москва, ул. Экспортная, д. 1",
            "name": "Экспортный дом",
        }, headers=auth_headers)
        resp = await client.get("/api/export/properties/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")


class TestAdminAPI:
    async def test_admin_list_users(self, client, admin_headers):
        resp = await client.get("/api/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_admin_block_user(self, client, admin_headers):
        resp = await client.get("/api/admin/users", headers=admin_headers)
        users = resp.json()["items"]
        non_admin = [u for u in users if u["nickname"] != "admintest"]
        if non_admin:
            user_id = non_admin[0]["id"]
            resp2 = await client.put(f"/api/admin/users/{user_id}", json={
                "is_active": False,
            }, headers=admin_headers)
            assert resp2.status_code == 200

    async def test_admin_delete_property(self, client, auth_headers, admin_headers):
        create_resp = await client.post("/api/properties", json={
            "address": "г. Москва, ул. Удаляемая, д. 1",
            "name": "Дом для удаления",
        }, headers=auth_headers)
        prop_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/admin/properties/{prop_id}", headers=admin_headers)
        assert resp.status_code == 204

    async def test_non_admin_cannot_access_admin(self, client, auth_headers):
        resp = await client.get("/api/admin/users", headers=auth_headers)
        assert resp.status_code == 403


class TestHealthCheck:
    async def test_health(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
