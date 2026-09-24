from dataclasses import dataclass


@dataclass(frozen=True)
class MarketUniverseEntry:
    company_id: str
    company_name: str
    market_data_ticker: str
    benchmark_ticker: str
    trade_currency: str
    primary_listing_exchange: str
    analysis_tier: str
    role_category: str
    is_confirmatory: bool
