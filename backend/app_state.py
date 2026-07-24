import os

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

if GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON:
    from services.sheets import SheetsBackend
    backend = SheetsBackend()
else:
    from services.mock import MockBackend
    backend = MockBackend()
