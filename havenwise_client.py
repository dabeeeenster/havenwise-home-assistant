"""
Havenwise API Client

Authenticates via Firebase Auth and calls the Havenwise REST API.
Holiday mode and other real-time state uses Firestore directly.
"""

import requests

FIREBASE_API_KEY = "AIzaSyApHd6ipDCoYkEhXRQaqvT6onJ7lshchnw"
FIREBASE_PROJECT_ID = "haven-wise-beta-3mqxzn"
FIREBASE_SIGN_IN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
FIRESTORE_BASE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
API_BASE = "https://api.havenwise.co.uk"


class HavenwiseClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.id_token = None
        self.refresh_token = None
        self.user_id = None
        self.login()

    def login(self):
        """Sign in with Firebase email/password auth."""
        resp = requests.post(FIREBASE_SIGN_IN_URL, json={
            "email": self.email,
            "password": self.password,
            "returnSecureToken": True,
        })
        resp.raise_for_status()
        data = resp.json()
        self.id_token = data["idToken"]
        self.refresh_token = data["refreshToken"]
        self.user_id = data["localId"]
        return data

    def refresh(self):
        """Refresh the ID token using the refresh token."""
        resp = requests.post(FIREBASE_REFRESH_URL, json={
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        })
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

    def _get(self, path: str, params: dict = None):
        resp = requests.get(f"{API_BASE}{path}", headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: dict = None):
        resp = requests.post(f"{API_BASE}{path}", headers=self._headers(), json=json_data)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str):
        resp = requests.delete(f"{API_BASE}{path}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── Profile & Status ──────────────────────────────────────────────
    def get_profile(self):
        return self._get("/profile")

    def get_system_status(self):
        return self._get("/system/status")

    def get_model_status(self):
        return self._get("/model/status")

    def get_features(self):
        return self._get("/system/features")

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
        """Start a heating boost/override. Example: {"flow_temperature": 45, "duration_minutes": 60}"""
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

    def get_tariffs_list(self):
        return self._get("/tariff/list")

    def get_tariff_token(self):
        return self._post("/tariff/token")

    # ── Billing ───────────────────────────────────────────────────────
    def get_subscription_status(self):
        return self._get("/billing/subscriptions")

    def get_payment_link(self):
        return self._get("/billing/subscriptions/payment_link")

    # ── User / Account ────────────────────────────────────────────────
    def update_user(self, data: dict):
        return self._post("/update-user", data)

    def get_account_updates(self, status: str = "open"):
        return self._get(f"/users/account-updates?status={status}")

    def get_referral_reward(self):
        return self._get("/users/referral-reward")

    # ── Device / Building ─────────────────────────────────────────────
    def update_building_info(self, data: dict):
        return self._post("/update-building-info", data)

    def request_control(self):
        return self._post("/request-control")

    def update_schedule(self):
        """Trigger a schedule update push to the heat pump."""
        return self._post("/update-schedule")

    # ── Firestore (systemTemps) ───────────────────────────────────────
    def _firestore_query(self, collection: str, field: str, value: str):
        """Run a Firestore structured query to find docs where field == value."""
        resp = requests.post(
            f"{FIRESTORE_BASE}:runQuery",
            headers=self._headers(),
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
        resp.raise_for_status()
        return resp.json()

    def _firestore_patch(self, doc_path: str, fields: dict):
        """Patch specific fields on a Firestore document."""
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
        resp = requests.patch(url, headers=self._headers(), json={"fields": firestore_fields})
        resp.raise_for_status()
        return resp.json()

    def _get_system_temps_doc(self):
        """Find the systemTemps Firestore doc for the current user."""
        results = self._firestore_query("systemTemps", "createdBy", self.user_id)
        for r in results:
            if "document" in r:
                return r["document"]
        return None

    def get_system_temps(self):
        """Get current system temps/state from Firestore (includes isHeatingOn, isDhwOn, etc.)."""
        doc = self._get_system_temps_doc()
        if not doc:
            return None
        out = {}
        for k, v in doc["fields"].items():
            val = list(v.values())[0]
            out[k] = val
        return out

    def _update_system_temps(self, fields: dict):
        """Update fields on the systemTemps Firestore doc, then trigger schedule update."""
        doc = self._get_system_temps_doc()
        if not doc:
            raise RuntimeError("No systemTemps document found for this user")
        return self._firestore_patch(doc["name"], fields)

    def enable_holiday_mode(self, heating: bool = True, hot_water: bool = True):
        """Turn on holiday mode (turns OFF heating and/or hot water, then pushes to heat pump)."""
        fields = {}
        if heating:
            fields["isHeatingOn"] = False
        if hot_water:
            fields["isDhwOn"] = False
        self._update_system_temps(fields)
        self.update_schedule()
        return fields

    def disable_holiday_mode(self, heating: bool = True, hot_water: bool = True):
        """Turn off holiday mode (turns ON heating and/or hot water, then pushes to heat pump)."""
        fields = {}
        if heating:
            fields["isHeatingOn"] = True
        if hot_water:
            fields["isDhwOn"] = True
        self._update_system_temps(fields)
        self.update_schedule()
        return fields


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Havenwise API Client")
    parser.add_argument("email", help="Havenwise account email")
    parser.add_argument("password", help="Havenwise account password")
    args = parser.parse_args()

    client = HavenwiseClient(args.email, args.password)

    print("=== Profile ===")
    print(client.get_profile())

    print("\n=== System Temps (Firestore) ===")
    print(client.get_system_temps())

    print("\n=== Heating Schedules ===")
    print(client.get_heating_schedules())

    print("\n=== Hot Water Schedules ===")
    print(client.get_hot_water_schedules())

    print("\n=== Performance (this week) ===")
    print(client.get_performance_stats(week=1))

    print("\n=== Tariff ===")
    print(client.get_tariff_details())
