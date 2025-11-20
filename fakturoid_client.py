import os
from typing import List, Dict, Optional
import requests


class FakturoidClient:
    """Minimal Fakturoid API v3 client for creating invoices.

    Expects credentials from environment variables:
    - FAKTUROID_ACCOUNT: account slug
    - FAKTUROID_EMAIL: login email used for API access
    - FAKTUROID_API_KEY: API token
    - FAKTUROID_USER_AGENT: custom user agent (required by Fakturoid)
    """

    def __init__(
        self,
        account_slug: str,
        email: str,
        api_key: str,
        user_agent: str,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.account_slug = account_slug
        self.email = email
        self.api_key = api_key
        self.user_agent = user_agent
        self.base_url = f"https://app.fakturoid.cz/api/v3/accounts/{account_slug}"
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls) -> "FakturoidClient":
        account = os.getenv("FAKTUROID_ACCOUNT")
        email = os.getenv("FAKTUROID_EMAIL")
        api_key = os.getenv("FAKTUROID_API_KEY")
        user_agent = os.getenv("FAKTUROID_USER_AGENT")

        missing = [
            key
            for key, value in {
                "FAKTUROID_ACCOUNT": account,
                "FAKTUROID_EMAIL": email,
                "FAKTUROID_API_KEY": api_key,
                "FAKTUROID_USER_AGENT": user_agent,
            }.items()
            if not value
        ]

        if missing:
            raise ValueError(f"Chybí environment proměnky pro Fakturoid: {', '.join(missing)}")

        return cls(account, email, api_key, user_agent)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }

    def create_invoice(self, payload: Dict) -> Dict:
        """Send invoice payload to Fakturoid and return JSON response."""
        url = f"{self.base_url}/invoices.json"
        response = self.session.post(
            url, headers=self._headers(), auth=(self.email, self.api_key), json=payload
        )
        response.raise_for_status()
        return response.json()

    def build_lines_from_hours(
        self, *, description: str, total_hours: float, rate_per_hour: float, vat_rate: int
    ) -> List[Dict]:
        return [
            {
                "name": description,
                "quantity": round(total_hours, 2),
                "unit_name": "hod",
                "unit_price": rate_per_hour,
                "vat_rate": vat_rate,
            }
        ]
