import requests
from datetime import datetime, timedelta
import base64

class IDokladAPI:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = 'https://api.idoklad.cz/v3'
        self.token = None
        self.get_access_token()
    
    def get_access_token(self):
        """Získá access token pomocí OAuth2"""
        auth_url = 'https://identity.idoklad.cz/server/connect/token'
        
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'scope': 'idoklad_api'
        }
        
        response = requests.post(auth_url, headers=headers, data=data)
        if response.status_code == 200:
            self.token = response.json()['access_token']
            return True
        return False
    
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def get_contacts(self, search=None):
        """Načte seznam kontaktů"""
        params = {}
        if search:
            params['filter'] = f"CompanyName~cn~{search}"
        
        response = requests.get(
            f'{self.base_url}/Contacts',
            headers=self.get_headers(),
            params=params
        )
        return response.json()
    
    def create_invoice(self, contact_id, items, description=""):
        """Vytvoří fakturu"""
        today = datetime.now()
        maturity = today + timedelta(days=14)
        
        invoice_data = {
            'ContactId': contact_id,
            'DateOfIssue': today.strftime('%Y-%m-%d'),
            'DateOfMaturity': maturity.strftime('%Y-%m-%d'),
            'DateOfTaxableSupply': today.strftime('%Y-%m-%d'),
            'Description': description,
            'IssuedInvoiceItems': items,
            'CurrencyId': 1,  # CZK
            'PaymentOptionId': 1  # Bankovní převod
        }
        
        response = requests.post(
            f'{self.base_url}/IssuedInvoices',
            json=invoice_data,
            headers=self.get_headers()
        )
        return response.json()