"""Claude (Anthropic) motoru - ham bulgulari triyaj eder (modulden bagimsiz).

Tum moduller bu paylasilan motoru kullanir. Her modul KENDI sistem promptunu ve
anahtar yoksa devreye girecek sezgisel (heuristic) fallback'ini saglar; motor sadece
Claude cagrisini ve yapilandirilmis cikti (tool-use) isini yapar.

- Sistem talimati `cache_control` ile prompt cache'e alinir (tekrarli triyajda ucuz).
- ANTHROPIC_API_KEY bos ise modulun heuristic'i kullanilir; demo/test anahtarsiz calisir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.core.config import settings


@dataclass
class TriageResult:
    title: str
    severity: str  # info | low | medium | high | critical
    summary: str
    recommendation: str


# Tum moduller icin ortak yapilandirilmis cikti araci
TRIAGE_TOOL = {
    "name": "rapor_triyaj",
    "description": "Bir bulgunun triyaj sonucunu yapilandirilmis sekilde dondurur.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Kisa bulgu basligi (Turkce)"},
            "severity": {
                "type": "string",
                "enum": ["info", "low", "medium", "high", "critical"],
            },
            "summary": {"type": "string", "description": "Turkce 2-3 cumlelik ozet"},
            "recommendation": {"type": "string", "description": "Turkce onerilen aksiyon"},
        },
        "required": ["title", "severity", "summary", "recommendation"],
    },
}

# (raw, asset_value, asset_type) -> TriageResult
HeuristicFn = Callable[[dict, str, str], TriageResult]


def triage(
    raw: dict,
    asset_value: str,
    asset_type: str,
    *,
    system_prompt: str,
    heuristic: HeuristicFn,
) -> TriageResult:
    """Ham bulguyu, modulun sistem promptu ve heuristic'i ile triyaj eder."""
    if not settings.anthropic_api_key:
        return heuristic(raw, asset_value, asset_type)

    # Geç import: anahtar yoksa anthropic'i hic yuklemeyelim
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    user_content = (
        f"Varlik tipi: {asset_type}\n"
        f"Varlik degeri: {asset_value}\n"
        f"Ham bulgu verisi (JSON):\n{raw}"
    )
    try:
        resp = client.messages.create(
            model=settings.claude_triage_model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "rapor_triyaj"},
            messages=[{"role": "user", "content": user_content}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "rapor_triyaj":
                data = block.input
                return TriageResult(
                    title=str(data.get("title", "")),
                    severity=str(data.get("severity", "medium")),
                    summary=str(data.get("summary", "")),
                    recommendation=str(data.get("recommendation", "")),
                )
    except Exception:
        # API hatasinda demo akisini bozma - heuristic'e dus
        return heuristic(raw, asset_value, asset_type)

    return heuristic(raw, asset_value, asset_type)
