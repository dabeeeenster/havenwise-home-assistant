"""Havenwise API client for Home Assistant."""

import logging

import requests

_LOGGER = logging.getLogger(__name__)

FIREBASE_API_KEY = "AIzaSyApHd6ipDCoYkEhXRQaqvT6onJ7lshchnw"
FIREBASE_PROJECT_ID = "haven-wise-beta-3mqxzn"
FIREBASE_SIGN_IN_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={FIREBASE_API_KEY}"
)
FIREBASE_REFRESH_URL = (
    f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
)
FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
)
API_BASE = "https://api.havenwise.co.uk"


class HavenwiseAuthError(Exception):
    """Raised when authentication fails."""


class HavenwiseConnectionError(Exception):
    """Raised when unable to connect."""


class HavenwiseClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.id_token: str | None = None
        self.refresh_token: str | None = None
        self.user_id: str | None = None

    def login(self):
        """Sign in with Firebase email/password auth."""
        try:
            resp = requests.post(
                FIREBASE_SIGN_IN_URL,
                json={
                    "email": self.email,
                    "password": self.password,
                    "returnSecureToken": True,
                },
                timeout=15,
            )
        except requests.ConnectionError as err:
            raise HavenwiseConnectionError("Cannot connect to Firebase") from err

        if resp.status_code == 400:
            raise HavenwiseAuthError("Invalid email or password")
        resp.raise_for_status()

        data = resp.json()
        self.id_token = data["idToken"]
        self.refresh_token = data["refreshToken"]
        self.user_id = data["localId"]
        return data

    def refresh_auth(self):
        """Refresh the ID token using the refresh token."""
        try:
            resp = requests.post(
                FIREBASE_REFRESH_URL,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=15,
            )
        except requests.ConnectionError as err:
            raise HavenwiseConnectionError("Cannot connect to Firebase") from err

        if resp.status_code == 400:
            raise HavenwiseAuthError("Token refresh failed, re-login required")
        resp.raise_for_status()

        data = resp.json()
        self.id_token = data["id_token"]
        self.refresh_token = data["refresh_token"]
        return data

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.id_token}",
        }

    def _request(self, method: str, url: str, **kwargs):
        """Make an HTTP request with automatic token refresh on 401."""
        kwargs.setdefault("timeout", 15)
        _LOGGER.debug("API request: %s %s", method, url)
        resp = requests.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            _LOGGER.warning("Got 401 for %s %s, refreshing token and retrying", method, url)
            self.refresh_auth()
            resp = requests.request(method, url, headers=self._headers(), **kwargs)
        if not resp.ok:
            _LOGGER.error("API error %s for %s %s: %s", resp.status_code, method, url, resp.text[:500])
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str):
        return self._request("GET", f"{API_BASE}{path}")

    def _post(self, path: str, json_data: dict | list | None = None):
        return self._request("POST", f"{API_BASE}{path}", json=json_data)

    def _delete(self, path: str):
        return self._request("DELETE", f"{API_BASE}{path}")

    # ── Profile & Status ──────────────────────────────────────────────
    def get_profile(self):
        return self._get("/profile")

    def get_system_status(self):
        return self._get("/system/status")

    def get_alerts(self):
        return self._get("/alerts")

    # ── Heating ───────────────────────────────────────────────────────
    def get_heating_schedules(self):
        return self._get("/heating/schedules")

    def update_heating_schedules(self, schedules: list):
        return self._post("/heating/schedules", schedules)

    def get_heating_settings(self):
        return self._get("/heating/settings")

    def update_heating_settings(self, settings: dict):
        return self._post("/heating/settings", settings)

    def get_heating_override(self):
        return self._get("/heating/setpoint/override")

    def start_heating_override(self, override: dict):
        return self._post("/heating/setpoint/override", override)

    def stop_heating_override(self):
        return self._delete("/heating/setpoint/override")

    # ── Hot Water ─────────────────────────────────────────────────────
    def get_hot_water_schedules(self):
        return self._get("/hot-water/schedules")

    def update_hot_water_schedules(self, schedules: list):
        return self._post("/hot-water/schedules", schedules)

    def start_hot_water_boost(self):
        return self._post("/hot-water/boost")

    def stop_hot_water_boost(self):
        return self._delete("/hot-water/boost")

    # ── Performance & Energy ──────────────────────────────────────────
    def get_performance_stats(self, week: int = 1):
        return self._get(f"/performance/daily?week={week}")

    # ── Tariff ────────────────────────────────────────────────────────
    def get_tariff_details(self):
        return self._get("/tariff")

    # ── Schedule Push ─────────────────────────────────────────────────
    def update_schedule(self):
        return self._post("/update-schedule")

    # ── Firestore (systemTemps) ───────────────────────────────────────
    def _firestore_query(self, collection: str, field: str, value: str):
        resp = self._request(
            "POST",
            f"{FIRESTORE_BASE}:runQuery",
            json={
                "structuredQuery": {
                    "from": [{"collectionId": collection}],
                    "where": {
                        "fieldFilter": {
                            "field": {"fieldPath": field},
                            "op": "EQUAL",
                            "value": {"stringValue": value},
                        }
                    },
                }
            },
        )
        return resp

    def _firestore_patch(self, doc_path: str, fields: dict):
        firestore_fields = {}
        for k, v in fields.items():
            if isinstance(v, bool):
                firestore_fields[k] = {"booleanValue": v}
            elif isinstance(v, str):
                firestore_fields[k] = {"stringValue": v}
            elif isinstance(v, (int, float)):
                firestore_fields[k] = {"doubleValue": v}

        params = "&".join(f"updateMask.fieldPaths={k}" for k in fields)
        url = f"https://firestore.googleapis.com/v1/{doc_path}?{params}"
        return self._request("PATCH", url, json={"fields": firestore_fields})

    def _get_system_temps_doc(self):
        results = self._firestore_query("systemTemps", "createdBy", self.user_id)
        for r in results:
            if "document" in r:
                return r["document"]
        return None

    def get_system_temps(self):
        doc = self._get_system_temps_doc()
        if not doc:
            _LOGGER.warning("No systemTemps document found in Firestore")
            return None
        out = {}
        for k, v in doc["fields"].items():
            val = list(v.values())[0]
            out[k] = val
        _LOGGER.debug("Parsed system_temps: %s", out)
        return out

    def _update_system_temps(self, fields: dict):
        doc = self._get_system_temps_doc()
        if not doc:
            raise RuntimeError("No systemTemps document found for this user")
        return self._firestore_patch(doc["name"], fields)

    def enable_holiday_mode(self, heating: bool = True, hot_water: bool = True):
        fields = {}
        if heating:
            fields["isHeatingOn"] = False
        if hot_water:
            fields["isDhwOn"] = False
        self._update_system_temps(fields)
        self.update_schedule()
        return fields

    def disable_holiday_mode(self, heating: bool = True, hot_water: bool = True):
        fields = {}
        if heating:
            fields["isHeatingOn"] = True
        if hot_water:
            fields["isDhwOn"] = True
        self._update_system_temps(fields)
        self.update_schedule()
        return fields
