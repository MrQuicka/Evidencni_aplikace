# REST API Dokumentace pro mobilní aplikaci

## Base URL
```
http://your-cloudflare-tunnel.com/api/mobile
```

## Autentizace

Všechny endpointy kromě `/auth/login` a `/auth/register` vyžadují JWT token v Authorization headeru:

```
Authorization: Bearer <token>
```

---

## Endpointy

### 1. **POST /auth/login** - Přihlášení
Vrátí JWT token pro autentizaci.

**Request:**
```json
{
    "username": "admin",
    "password": "heslo123"
}
```

**Response (200):**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user_id": 1,
    "username": "admin"
}
```

**Response (401):**
```json
{
    "error": "Neplatné přihlašovací údaje"
}
```

---

### 2. **POST /auth/register** - Registrace
Vytvoří nového uživatele a vrátí JWT token.

**Request:**
```json
{
    "username": "novyuzivatel",
    "password": "heslo123"
}
```

**Response (201):**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user_id": 2,
    "username": "novyuzivatel"
}
```

---

### 3. **GET /projects** - Získat projekty
Vrátí všechny projekty aktuálního uživatele.

**Response (200):**
```json
{
    "projects": [
        {
            "id": 1,
            "name": "Projekt A",
            "user_id": 1
        },
        {
            "id": 2,
            "name": "Projekt B",
            "user_id": 1
        }
    ]
}
```

---

### 4. **POST /projects** - Vytvořit projekt

**Request:**
```json
{
    "name": "Nový projekt"
}
```

**Response (201):**
```json
{
    "id": 3,
    "name": "Nový projekt",
    "user_id": 1
}
```

---

### 5. **DELETE /projects/{project_id}** - Smazat projekt

**Response (200):**
```json
{
    "message": "Projekt smazán"
}
```

---

### 6. **GET /logs** - Získat záznamy docházky

**Query parametry:**
- `since` (volitelné): ISO timestamp - vrátí jen záznamy po tomto datu (pro synchronizaci)
- `project_id` (volitelné): ID projektu - filtrovat podle projektu

**Response (200):**
```json
{
    "logs": [
        {
            "id": 1,
            "project_id": 1,
            "project_name": "Projekt A",
            "start_time": "2025-10-28T08:00:00",
            "end_time": "2025-10-28T16:00:00",
            "pause_start": null,
            "pause_end": null,
            "note": "Pracovní den"
        }
    ],
    "timestamp": "2025-10-28T18:00:00"
}
```

---

### 7. **POST /logs** - Vytvořit záznam

**Request:**
```json
{
    "project_id": 1,
    "start_time": "2025-10-28T08:00:00",
    "end_time": "2025-10-28T16:00:00",
    "pause_start": null,
    "pause_end": null,
    "note": "Pracovní den"
}
```

**Response (201):**
```json
{
    "id": 1,
    "project_id": 1,
    "start_time": "2025-10-28T08:00:00",
    "end_time": "2025-10-28T16:00:00",
    "pause_start": null,
    "pause_end": null,
    "note": "Pracovní den"
}
```

---

### 8. **PUT /logs/{log_id}** - Aktualizovat záznam

**Request:** Stejný jako u POST, aktualizují se pouze pole, která jsou v requestu.

---

### 9. **DELETE /logs/{log_id}** - Smazat záznam

**Response (200):**
```json
{
    "message": "Záznam smazán"
}
```

---

### 10. **GET /logs/active** - Získat aktivní činnost

Vrátí záznam, který nemá `end_time` (právě běžící činnost).

**Response (200):**
```json
{
    "active_log": {
        "id": 5,
        "project_id": 1,
        "project_name": "Projekt A",
        "start_time": "2025-10-28T14:30:00",
        "pause_start": null,
        "pause_end": null,
        "note": null
    }
}
```

Nebo pokud žádná činnost neběží:
```json
{
    "active_log": null
}
```

---

### 11. **POST /invoices/fakturoid** - Vytvořit fakturu ve Fakturoidu

Na základě docházkových záznamů vytvoří fakturu přes API Fakturoidu v3. Je potřeba nastavit environment proměnné `FAKTUROID_ACCOUNT`, `FAKTUROID_EMAIL`, `FAKTUROID_API_KEY` a `FAKTUROID_USER_AGENT`.

**Request:**
```json
{
    "project_id": 1,
    "subject_id": 123456,
    "rate_per_hour": 1200.0,
    "vat_rate": 21,
    "from": "2024-01-01",
    "to": "2024-01-31",
    "description": "Práce leden",
    "note": "Poznámka pro klienta",
    "due_days": 14
}
```

**Response (201):**
```json
{
    "invoice": { "id": 999, "number": "2024-001", ... },
    "total_hours": 160,
    "lines": [
        {
            "name": "Práce na projektu Projekt A",
            "quantity": 160,
            "unit_name": "hod",
            "unit_price": 1200.0,
            "vat_rate": 21
        }
    ]
}
```

---

### 12. **POST /logs/start** - Rychlý start práce

**Request:**
```json
{
    "project_id": 1,
    "note": "Volitelná poznámka"
}
```

**Response (201):**
```json
{
    "id": 6,
    "project_id": 1,
    "start_time": "2025-10-28T15:00:00"
}
```

**Response (409):** Pokud už nějaká činnost běží
```json
{
    "error": "Již běží jiná činnost"
}
```

---

### 13. **POST /logs/stop** - Ukončit práci

Ukončí aktuálně běžící činnost nastavením `end_time`.

**Response (200):**
```json
{
    "id": 6,
    "end_time": "2025-10-28T17:00:00"
}
```

**Response (404):** Pokud žádná činnost neběží
```json
{
    "error": "Žádná aktivní činnost"
}
```

---

### 14. **GET /sync/status** - Kontrola spojení

Jednoduchý endpoint pro kontrolu, zda server běží.

**Response (200):**
```json
{
    "status": "ok",
    "server_time": "2025-10-28T18:00:00",
    "user_id": 1
}
```

---

## Chybové kódy

- **200** - OK
- **201** - Vytvořeno
- **400** - Chybný request (chybí povinná pole)
- **401** - Neautorizováno (chybný token nebo credentials)
- **403** - Zakázáno (nemáte oprávnění)
- **404** - Nenalezeno
- **409** - Konflikt (např. už běží jiná činnost)

---

## Poznámky k implementaci

1. **Datumy**: Všechny datumy jsou v ISO 8601 formátu (`YYYY-MM-DDTHH:MM:SS`)
2. **JWT Token**: Token je platný 7 dní, pak je potřeba se přihlásit znovu
3. **Synchronizace**: Pro synchronizaci offline změn použijte parametr `since` u `/logs` endpointu
