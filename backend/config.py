from pydantic import BaseModel


class Settings(BaseModel):
    backend_type: str = "mock"  # "mock" or "sheets"
    google_sheet_id: str = ""
    google_service_account_path: str = ""
    display_currency: str = "USD"
    exchange_rate_api_url: str = "https://open.er-api.com/v6/latest/USD"


settings = Settings()
