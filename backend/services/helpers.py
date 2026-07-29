import calendar
from datetime import date, datetime, timedelta
import httpx

from models import RatesResponse


def advance_date(date_str: str, frequency: str) -> str:
    y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
    if frequency == "monthly":
        m += 1
        if m > 12:
            m = 1
            y += 1
        last_day = calendar.monthrange(y, m)[1]
        d = min(d, last_day)
    else:
        y += 1
    return f"{y}-{m:02d}-{d:02d}"


_rates_cache: RatesResponse | None = None
_rates_cache_time: datetime | None = None


def fetch_rates() -> RatesResponse:
    global _rates_cache, _rates_cache_time

    if _rates_cache and _rates_cache_time:
        if datetime.now() - _rates_cache_time < timedelta(hours=12):
            return _rates_cache

    apis = [
        'https://open.er-api.com/v6/latest/USD',
        'https://api.exchangerate-api.com/v4/latest/USD',
    ]

    with httpx.Client(timeout=10) as client:
        for api_url in apis:
            try:
                res = client.get(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                data = res.json()
                rates = data.get('rates', {})
                php_rate = rates.get("PHP")
                if php_rate:
                    result = RatesResponse(
                        base="USD",
                        rates={
                            "USD": 1.0,
                            "PHP": php_rate,
                            "EUR": rates.get("EUR", 0.92),
                            "GBP": rates.get("GBP", 0.79),
                            "JPY": rates.get("JPY", 149.5),
                        }
                    )
                    _rates_cache = result
                    _rates_cache_time = datetime.now()
                    return result
            except Exception:
                continue

    if _rates_cache:
        return _rates_cache
    return RatesResponse(base="USD", rates={"USD": 1.0, "PHP": 56.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5})
