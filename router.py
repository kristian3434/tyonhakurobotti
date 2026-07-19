"""
ai/router.py — Yhteinen reititys valitulle AI-moottorille.
GitHub-demoversiossa ulkoiset AI-kutsut on poistettu käytöstä.
Oletuksena käytetään determinististä paikallista simulaatiota.
"""
from __future__ import annotations

from collections.abc import Iterator
import json
import requests

import streamlit as st

from config import (
    LOCAL_AI_BASE_URL,
    LOCAL_AI_MAX_TOKENS,
    LOCAL_AI_MODEL,
    LOCAL_AI_READ_TIMEOUT_SECONDS,
    SIMULATED_API_KEY,
)

DEFAULT_ENGINE = "demo"


def _demo_response(prompt: str) -> str:
    """Palauttaa paikallisen mallivastauksen ilman verkko- tai API-kutsua."""
    text = str(prompt or "").casefold()
    prefix = "🧪 DEMO — vastaus simuloitiin paikallisesti ilman oikeaa API-avainta.\n\n"

    if "työhakemus" in text:
        return prefix + (
            "Hei,\n\n"
            "olen kiinnostunut avoimesta tehtävästä ja haluan tuoda esiin "
            "tehtävän kannalta olennaisen osaamiseni. Täydennä tähän omat "
            "konkreettiset saavutuksesi, työkalusi ja motivaatiosi.\n\n"
            "Keskustelen mielelläni siitä, miten voisin tukea tiimin tavoitteita.\n\n"
            "Ystävällisin terveisin,\nDemo User"
        )

    if "rekrytointiprosessin" in text or "aiherivi" in text:
        return prefix + (
            "Aihe: Hakemukseni tilanne\n\n"
            "Hei,\n\n"
            "haluaisin tiedustella rekrytointiprosessin tilanteesta. Olen edelleen "
            "kiinnostunut tehtävästä ja vastaan mielelläni lisäkysymyksiin.\n\n"
            "Kiitos ajastanne.\n\nYstävällisin terveisin,\nDemo User"
        )

    if "3 kiperää kysymystä" in text:
        return prefix + (
            "1. Miten onnistumista tehtävässä mitataan ensimmäisten kuukausien aikana?\n"
            "2. Mikä on tiimin tärkein ratkaistava haaste juuri nyt?\n"
            "3. Miten rooli tekee yhteistyötä muiden toimintojen kanssa?\n\n"
            "Faktat: tarkista organisaation verkkosivut, viimeisimmät uutiset ja "
            "tehtäväkuva ennen haastattelua."
        )

    if "analy" in text or "vertaa" in text:
        return prefix + (
            "Tämä on esimerkkianalyysi. Vertaa ilmoituksen vaatimuksia omaan "
            "osaamiseesi kohta kohdalta, nimeä vahvat osumat ja merkitse puuttuvat "
            "taidot kehitettäviksi. Simulaatio ei lähetä syötettyä tekstiä ulkopuolelle."
        )

    return prefix + (
        "Simulaatio vastaanotti pyynnön onnistuneesti. Julkisessa demoversiossa "
        "oikeat pilvipalvelut ja API-avaimet on tarkoituksella poistettu käytöstä."
    )


def call_demo(prompt: str, api_key: str = SIMULATED_API_KEY) -> tuple[str, None]:
    """Simuloi avaimellisen AI-kutsun; tunniste ei kelpaa mihinkään palveluun."""
    if api_key != SIMULATED_API_KEY:
        return _demo_response(prompt), None
    return _demo_response(prompt), None


def stream_demo(prompt: str, api_key: str = SIMULATED_API_KEY) -> Iterator[str]:
    """Suoratoistaa demovastauksen ilman verkkoliikennettä."""
    response, _ = call_demo(prompt, api_key)
    yield response

# ── PAIKALLISEN AI:N ASETUKSET (LM Studio) ────────────────────────────────────
_LOCAL_OPENAI_ROOT = LOCAL_AI_BASE_URL.rstrip("/")
_LOCAL_SERVER_ROOT = (
    _LOCAL_OPENAI_ROOT[:-3] if _LOCAL_OPENAI_ROOT.endswith("/v1") else _LOCAL_OPENAI_ROOT
)
LOCAL_URL = f"{_LOCAL_OPENAI_ROOT}/chat/completions"
LOCAL_MODELS_URL = f"{_LOCAL_OPENAI_ROOT}/models"
LOCAL_NATIVE_MODELS_URL = f"{_LOCAL_SERVER_ROOT}/api/v1/models"
_LOCAL_CONNECT_TIMEOUT_SECONDS = 5


class LocalAIError(RuntimeError):
    """Käyttäjälle näytettävä paikallisen AI:n yhteys- tai vastausvirhe."""


def repair_text_encoding(text: str) -> str:
    """Korjaa tavallinen UTF-8/Latin-1-mojibake, esimerkiksi ``Ã¤`` → ``ä``."""
    value = str(text or "")
    markers = ("Ã", "Â", "â€", "ðŸ")
    if not any(marker in value for marker in markers):
        return value

    marker_count = sum(value.count(marker) for marker in markers)
    for source_encoding in ("latin-1", "cp1252"):
        try:
            repaired = value.encode(source_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        repaired_count = sum(repaired.count(marker) for marker in markers)
        if repaired_count < marker_count:
            return repaired
    return value


def local_server_status() -> tuple[bool, str | None, str]:
    """Tarkistaa LM Studion ja palauttaa oikeasti ladatun kielimallin."""
    try:
        response = requests.get(LOCAL_NATIVE_MODELS_URL, timeout=(2, 4))
        if response.status_code == 404:
            return _legacy_local_server_status()
        response.raise_for_status()
        payload = response.json()
    except requests.ConnectionError:
        return (
            False,
            None,
            "LM Studio ei vastaa portissa 1234. Käynnistä LM Studio ja "
            "Developer → Start Server.",
        )
    except requests.Timeout:
        return False, None, "LM Studion yhteystarkistus aikakatkaistiin."
    except (requests.RequestException, ValueError, TypeError):
        return False, None, "LM Studio vastasi virheellisesti. Käynnistä Local Server uudelleen."

    if not isinstance(payload, dict):
        return False, None, "LM Studio palautti tuntemattoman malliluettelon."

    loaded_models: list[str] = []
    for item in payload.get("models", []):
        if not isinstance(item, dict) or item.get("type") != "llm":
            continue
        for instance in item.get("loaded_instances", []):
            if isinstance(instance, dict) and str(instance.get("id", "")).strip():
                loaded_models.append(str(instance["id"]).strip())

    if not loaded_models:
        return False, None, "LM Studio on käynnissä, mutta kielimallia ei ole ladattu."

    model = LOCAL_AI_MODEL if LOCAL_AI_MODEL in loaded_models else loaded_models[0]
    return True, model, "Yhteys kunnossa."


def _legacy_local_server_status() -> tuple[bool, str | None, str]:
    """Yhteensopivuus LM Studio -versioille, joissa native v1 API puuttuu."""
    response = requests.get(LOCAL_MODELS_URL, timeout=(2, 4))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Tuntematon malliluettelo")

    models = [
        str(item.get("id", "")).strip()
        for item in payload.get("data", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    ]
    if not models:
        return False, None, "LM Studio on käynnissä, mutta kielimallia ei ole ladattu."
    model = LOCAL_AI_MODEL if LOCAL_AI_MODEL in models else models[0]
    return True, model, "Yhteys kunnossa."


def _local_error_message(error: Exception) -> str:
    if isinstance(error, LocalAIError):
        detail = str(error)
    elif isinstance(error, requests.Timeout):
        detail = (
            f"Paikallinen malli ei lähettänyt dataa {LOCAL_AI_READ_TIMEOUT_SECONDS} "
            "sekuntiin. Tarkista LM Studiosta, ettei malli ole pysähtynyt."
        )
    elif isinstance(error, requests.ConnectionError):
        detail = "Yhteys LM Studioon katkesi kesken vastauksen."
    elif isinstance(error, requests.HTTPError):
        status = error.response.status_code if error.response is not None else "tuntematon"
        detail = f"LM Studio palautti HTTP-virheen {status}."
    else:
        detail = "LM Studio palautti virheellisen vastauksen."

    return f"🔴 Paikallinen tekoäly ei ole käytettävissä. {detail}"


def _iter_local_chunks(prompt: str) -> Iterator[str]:
    available, model, status_message = local_server_status()
    if not available or not model:
        raise LocalAIError(status_message)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": LOCAL_AI_MAX_TOKENS,
        "stream": True,
    }
    response = requests.post(
        LOCAL_URL,
        json=payload,
        stream=True,
        timeout=(_LOCAL_CONNECT_TIMEOUT_SECONDS, LOCAL_AI_READ_TIMEOUT_SECONDS),
    )
    try:
        response.raise_for_status()
        received_content = False

        # LM Studion SSE-vastauksessa ei aina ole charset-otsaketta. Requests
        # saattaa silloin tulkita UTF-8:n Latin-1:nä ("ä" → "Ã¤"), joten
        # dekoodataan tavut aina itse UTF-8:na.
        for line in response.iter_lines(decode_unicode=False):
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue

            json_str = line[5:].strip()
            if json_str == "[DONE]":
                break

            try:
                chunk = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            if chunk.get("error"):
                error = chunk["error"]
                message = (
                    error.get("message", "Tuntematon mallivirhe")
                    if isinstance(error, dict)
                    else str(error)
                )
                raise LocalAIError(message)

            try:
                content = chunk["choices"][0].get("delta", {}).get("content")
            except (KeyError, IndexError, TypeError):
                content = None

            if content:
                received_content = True
                yield repair_text_encoding(str(content))

        if not received_content:
            raise LocalAIError("Malli palautti tyhjän vastauksen.")
    finally:
        response.close()


def call_local(prompt: str) -> tuple[str | None, str | None]:
    """Kutsuu LM Studiota suoratoistona ja kokoaa palat yhdeksi vastaukseksi."""
    try:
        answer = "".join(_iter_local_chunks(prompt)).strip()
        return answer, None
    except Exception as error:
        return None, _local_error_message(error)


def stream_local(prompt: str) -> Iterator[str]:
    """Kutsuu paikallisesti LM Studiossa pyörivää tekoälyä streaming-tilassa."""
    try:
        yield from _iter_local_chunks(prompt)
    except Exception as error:
        yield f"\n\n{_local_error_message(error)}"


# ──────────────────────────────────────────────────────────────────────────────

def _selected_engine() -> str:
    raw = st.session_state.get("ai_engine", DEFAULT_ENGINE)
    return _normalize_engine(raw)


def _normalize_engine(value: str | None) -> str:
    if not value:
        return DEFAULT_ENGINE

    engine = str(value).strip().lower()

    if (
        "gemma" in engine
        or "local" in engine
        or "paikallinen" in engine
        or "lm studio" in engine
        or "lmstudio" in engine
    ):
        return "local"

    if (
        "demo" in engine
        or "simul" in engine
        or "gemini" in engine
        or "claude" in engine
        or "anthropic" in engine
        or "chatgpt" in engine
        or "openai" in engine
        or "gpt" in engine
    ):
        return "demo"

    return DEFAULT_ENGINE


def call_ai(prompt: str) -> tuple[str | None, str | None]:
    engine = _selected_engine()
    return call_local(prompt) if engine == "local" else call_demo(prompt)


def stream_ai(prompt: str) -> Iterator[str]:
    engine = _selected_engine()
    if engine == "local":
        yield from stream_local(prompt)
        return
    yield from stream_demo(prompt)
