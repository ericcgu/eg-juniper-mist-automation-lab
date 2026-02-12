"""Integration tests for L04: Mist API Basics.

These tests run against a real Mist environment.
Requires valid .env and config/env.yml with real credentials.
"""

from mistapi.api import v1 as mist


class TestAuthentication:
    """Test authentication against the Mist API."""

    def test_requests_session_can_get_self(self, requests_session, mist_api_root):
        """Verify token-based auth works with requests."""
        response = requests_session.get(mist_api_root + "api/v1/self")
        assert response.status_code == 200
        data = response.json()
        assert "privileges" in data

    def test_mistapi_session_is_authenticated(self, mist_session):
        """Verify mistapi session is authenticated."""
        assert mist_session is not None


class TestSiteCRUD:
    """Test Create, Read, Update, Delete operations on sites."""

    def test_list_sites(self, requests_session, mist_api_root, org_id):
        """Verify we can list org sites via requests."""
        sites_uri = mist_api_root + f"api/v1/orgs/{org_id}/sites"
        response = requests_session.get(sites_uri)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_sites_mistapi(self, mist_session, org_id):
        """Verify we can list org sites via mistapi."""
        result = mist.orgs.sites.listOrgSites(mist_session, org_id=org_id)
        assert isinstance(result.data, list)

    def test_create_and_delete_site(self, requests_session, mist_api_root, org_id):
        """Verify we can create and delete a site via requests."""
        sites_uri = mist_api_root + f"api/v1/orgs/{org_id}/sites"
        site_payload = {
            "name": "pytest-test-site",
            "country_code": "US",
            "address": "123 Test St, Testville, TX 00000",
        }

        # Create
        create_resp = requests_session.post(sites_uri, json=site_payload)
        assert create_resp.status_code == 200
        site_id = create_resp.json()["id"]

        try:
            # Read
            site_uri = mist_api_root + f"api/v1/sites/{site_id}"
            read_resp = requests_session.get(site_uri)
            assert read_resp.status_code == 200
            assert read_resp.json()["name"] == "pytest-test-site"

            # Update settings
            settings_uri = mist_api_root + f"api/v1/sites/{site_id}/setting"
            settings = requests_session.get(settings_uri).json()
            settings["rogue"] = {"honeypot_enabled": True}
            update_resp = requests_session.put(settings_uri, json=settings)
            assert update_resp.status_code == 200
        finally:
            # Delete (always clean up)
            delete_resp = requests_session.delete(
                mist_api_root + f"api/v1/sites/{site_id}"
            )
            assert delete_resp.status_code == 200


class TestPythonFiltering:
    """Test Python's built-in filter with lambda for asset filtering."""

    def test_filter_single_match(self):
        assets = [{"name": "a", "id": 1}, {"name": "b", "id": 2}]
        result = list(filter(lambda x: x["name"] == "a", assets))
        assert len(result) == 1
        assert result[0] == {"name": "a", "id": 1}

    def test_filter_multiple_matches(self):
        assets = [
            {"name": "a", "type": "x"},
            {"name": "b", "type": "x"},
            {"name": "c", "type": "y"},
        ]
        result = list(filter(lambda x: x["type"] == "x", assets))
        assert len(result) == 2

    def test_filter_no_match(self):
        assets = [{"name": "a"}]
        result = list(filter(lambda x: x["name"] == "z", assets))
        assert len(result) == 0

    def test_filter_multiple_criteria(self):
        assets = [
            {"name": "a", "type": "x"},
            {"name": "b", "type": "x"},
        ]
        result = list(filter(lambda x: x["name"] == "a" and x["type"] == "x", assets))
        assert len(result) == 1
        assert result[0] == {"name": "a", "type": "x"}
