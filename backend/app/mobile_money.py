from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    status: str
    external_reference: str
    message: str


def normalize_provider(provider: str) -> str:
    value = provider.strip().lower().replace(" ", "_")
    aliases = {
        "orange": "orange_money",
        "orange_money": "orange_money",
        "mtn": "mtn_money",
        "mtn_money": "mtn_money",
        "sandbox": "sandbox",
    }
    return aliases.get(value, "sandbox")


def simulate_mobile_money_payment(provider: str, phone: str, amount_gnf: int) -> ProviderResult:
    normalized = normalize_provider(provider)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = phone[-4:] if len(phone) >= 4 else "0000"
    return ProviderResult(
        provider=normalized,
        status="paid",
        external_reference=f"{normalized.upper()}-{timestamp}-{suffix}",
        message=f"Sandbox payment accepted for {amount_gnf} GNF",
    )
