"""
config.py — Kaikki vakiot ja asetukset yhdessä paikassa.
"""

# ── Käyttäjä & tiedostot ──────────────────────────────────────────────────────
USER_NAME         = "Demo User"
STORAGE_FILE      = "local_storage.json"
KELA_FILE         = "kela_storage.json"
SHEET_ID          = ""
USER_EDUCATION    = {
    "degree": "",
    "year": None,
    "level": "",
    "is_higher_education": False,
    "has_amk_degree": False,
    "has_university_degree": False,
}

# Julkaistava GitHub-versio toimii tarkoituksella ilman oikeita API-avaimia.
# Tunniste on vain paikallisen demoreitittimen käyttöön eikä avaa mitään palvelua.
DEMO_MODE = True
SIMULATED_API_KEY = "demo-api-key-not-a-real-secret"
VISITOR_DATA_ENABLED = False
VISITOR_DATA_ENDPOINT = ""
VISITOR_DATA_TOKEN = ""
PORTFOLIO_URL = "https://tulevaisuudentekija.janmyllymaki.workers.dev/"
FUTURE_MAKER_LINK = PORTFOLIO_URL

# ── AI-mallit (Paikallinen LM Studio M5 MacBook Airilla) ──────────────────────
LOCAL_AI_BASE_URL = "http://127.0.0.1:1234/v1"
LOCAL_AI_API_KEY  = SIMULATED_API_KEY
# "local-model" on LM Studion yleisavain, joka toimii aina riippumatta ladatusta tiedostosta
LOCAL_AI_MODEL    = "local-model"
# Paikallinen 12B-malli voi tarvita yli kaksi minuuttia ensimmäiseen vastaukseen.
# Suoratoisto pitää yhteyden aktiivisena, ja tämä on yksittäisten osien välinen
# enimmäisodotus (ei koko vastauksen kesto).
LOCAL_AI_READ_TIMEOUT_SECONDS = 600
LOCAL_AI_MAX_TOKENS = 1600

# Pilvimallit (varalla)
GEMINI_MODEL    = "gemini-2.5-flash"
CLAUDE_MODEL    = "claude-3-5-sonnet-latest"
OPENAI_MODEL    = "gpt-4o-mini"

# ── Logiikka-asetukset ────────────────────────────────────────────────────────
MONTHLY_QUOTA   = 4
KELA_CYCLE_DAYS = 28
AGENT_SILENCE_THRESHOLD = 14
INTERVIEW_WARNING_DAYS  = 2
FUTURE_DATE_BUFFER      = 30

# ── Hakuasetukset ─────────────────────────────────────────────────────────────
TARGET_ROLES = [
    "Graafinen suunnittelija", "Sisällöntuottaja", "Visuaalinen suunnittelija",
    "Projektipäällikkö (luovat sisällöt)", "Viestintäsuunnittelija",
    "Markkinointisuunnittelija", "UI/UX-suunnittelija", "Creative Producer",
    "Content Manager", "Art Director Assistant", "Junior Designer", "Video Editor",
]

SEARCH_KEYWORDS = ["graafinen suunnittelija", "sisällöntuottaja", "ICT", "digitaalinen viestintä"]
UNI_KEYWORDS = ["laskennallinen luovuus", "human-computer interaction"]
AMK_KEYWORDS = ["palvelumuotoilu", "mediatuotanto"]

# ── Hakemuksen tilavärit ──────────────────────────────────────────────────────
STATUS_COLORS = {
    "Odottaa":                  {"bg": "#FFF3CD", "text": "#856404"},
    "Keskustelu":               {"bg": "#D1ECF1", "text": "#0C5460"},
    "Haastattelu":              {"bg": "#C3E6CB", "text": "#155724"},
    "Ei vastausta":             {"bg": "#E2E3E5", "text": "#6C757D"},
    "Hylätty":                  {"bg": "#F8D7DA", "text": "#721C24"},
    "Kiinnostunut":             {"bg": "#E2E3E5", "text": "#333333"},
}

ALL_STATUSES = list(STATUS_COLORS.keys())
