"""
data/datasets.py — Kaikki staattiset tietokokoelmat.
"""
from models import Course

AGENCIES: dict[str, str] = {
    "Avidly":           "https://avidly.fi/",
    "Bob the Robot":    "https://www.bobtherobot.fi/",
    "Dagmar":           "https://www.dagmar.fi/",
    "Folk Finland":     "https://folkfinland.fi/",
    "Futurice":         "https://futurice.com/careers",
    "hasan & partners": "https://www.hasanpartners.fi/",
    "Kuulu":            "https://www.kuulu.fi/",
    "Miltton":          "https://miltton.com/fi/",
    "N2 Creative":      "https://n2.fi/",
    "Nitro AIM":        "https://www.nitroaim.fi/",
    "Reaktor":          "https://www.reaktor.com/careers/",
    "Samy":             "https://samy.com/",
    "SEK":              "https://sek.io/careers/",
    "Siili Solutions":  "https://www.siili.com/",
    "TBWA Helsinki":    "https://www.tbwa.fi/",
    "Valve":            "https://valve.fi/",
    "Vapa Media":       "https://vapamedia.fi/",
    "Vincit":           "https://www.vincit.fi/careers/",
}

SCHOOLS: list[dict] = [
    {"name": "Aalto-yliopisto (Taiteet & Suunnittelu)",
     "url": "https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu", "status": "⭐ HUIPPU"},
    {"name": "HEO Kansanopisto (Graafinen & Kuvallinen)",
     "url": "https://www.heo.fi/", "status": "Portfolio"},
    {"name": "Metropolia AMK (Viestintä & Muotoilu)",
     "url": "https://www.metropolia.fi/fi/opiskelu-metropoliassa/amk-tutkinnot/", "status": "AMK / Haku"},
    {"name": "Haaga-Helia (Journalismi & Digi)",
     "url": "https://www.haaga-helia.fi/fi/viestinta-ja-journalismi", "status": "AMK / Haku"},
    {"name": "Humak (Kulttuurituottaja)",
     "url": "https://www.humak.fi/opiskelu/amk-tutkinnot/kulttuurituottaja/", "status": "AMK / Tuottaja"},
    {"name": "Taitotalo (Digimarkkinointi)",
     "url": (
         "https://www.taitotalo.fi/koulutukset/ict-ja-media/109191-6279-6315-"
         "digimarkkinoinnin-asiantuntija-verkko-opiskelu-media-alan-ja-kuvallisen-"
         "ilmaisun-perustutkinnon-osa"
     ), "status": "Erikoistuminen"},
    {"name": "Stadin AO (Media & Kuvallinen)",
     "url": "https://stadinao.fi/koulutustarjonta/media-ja-visuaalinen-ala/", "status": "Jatkuva haku"},
    {"name": "Varia (Media-ala)",
     "url": "https://www.varia.fi/koulutukset/media-ala/", "status": "Vantaa"},
    {"name": "Omnia (Media & Kuvallinen ilmaisu)",
     "url": "https://www.omnia.fi/koulutukset/mediapalvelujen-toteuttaja", "status": "Espoo"},
    {"name": "Business College Helsinki (Digi)",
     "url": "https://bc.fi/koulutukset/", "status": "Helsinki"},
    {"name": "Rastor-instituutti (Markkinointi)",
     "url": "https://www.rastor.fi/koulutukset/", "status": "Aikuis"},
    {"name": "Careeria (Media)",
     "url": "https://careeria.fi/koulutukset/", "status": "Hki/Vantaa"},
]

STARTUPS: dict[str, str] = {
    "Aalto Startup Center": "https://startupcenter.aalto.fi/",
    "Kiuas Accelerator":    "https://www.kiuas.com/",
    "Kurio (Mainostoimisto)": "https://www.kurio.fi/",
    "Maria 01 (Yritykset)": "https://maria.io/",
    "Supercell Careers":    "https://supercell.com/en/careers/",
    "The Hub (Helsinki Jobs)": "https://thehub.io/jobs?location=Helsinki",
    "Wolt Careers":         "https://careers.wolt.com/en",
}

SITES_INTL: dict[str, str] = {
    "Behance Jobs":       "https://www.behance.net/joblist",
    "Design Jobs Board":  "https://www.designjobsboard.com/",
    "Krop":               "https://www.krop.com/",
}

SITES_FI_NORDIC: dict[str, str] = {
    "Grafia ry":              "https://www.grafia.fi/",
    "Journalistiliitto":      "https://journalistiliitto.fi/",
    "Kuntarekry (Kulttuuri)": "https://www.kuntarekry.fi/fi/tyopaikat/kulttuuri-ja-museoala/",
    "TAKU ry":                "https://taku.fi/avainsana/tyopaikat/",
    "Valtiolle.fi":           "https://valtiolle.fi/",
    "Viesti ry":              "https://viesti.fi/tyoelama/avoimet-tyopaikat/",
}

SITES_MEDIA: dict[str, str] = {
    "Alma Media Urat":  "https://www.almamedia.fi/tyopaikat/",
    "Duunitori (Media)":"https://duunitori.fi/tyopaikat/ala/media-ala",
    "Kelaamo (AV-ala)": "https://www.kelaamo.fi/",
    "Sanoma Urat":      "https://www.sanoma.com/fi/keita-olemme/toihin-sanomalle/",
    "Yle Rekry":        "https://yle.fi/rekry",
}

AI_COURSES: list[Course] = [
    Course(
        name="Generative AI Learning Path", provider="Google Cloud",
        url="https://www.cloudskillsboost.google/paths/118",
        desc="Googlen virallinen ja ilmainen polku generatiivisen tekoälyn syvälliseen ymmärtämiseen.",
        type="SERTIFIKAATTI",
    ),
    Course(
        name="Opin.fi: Tekoäly & Luova osaaminen", provider="Suomen Korkeakoulut (Digivisio)",
        url="https://opin.fi/fi/search?q=teko%C3%A4ly",
        desc="Kokoava haku. Kriteerit: Laskennallinen luovuus, XR, Visual Culture, Palvelumuotoilu & AI.",
        type="HAKUPALVELU",
    ),
    Course(
        name="Elements of AI", provider="Helsingin Yliopisto & Reaktor",
        url="https://www.elementsofai.com/fi",
        desc="Suomalainen klassikko. Pakollinen pohjatieto kaikille alalla toimiville.",
        type="MOOC / ETÄ",
    ),
    Course(
        name="HY Avoin: Tekoäly & Data", provider="Helsingin Yliopisto",
        url="https://www.helsinki.fi/fi/hakeminen-ja-opetus/etsi-koulutuksia-ja-kursseja"
            "?s_format=mooc%2Cdistance_or_online_teaching&s_itg=open_university&s_q=ai",
        desc="Helsingin yliopiston avoimet tekoälykurssit. MOOC-toteutuksia joustavasti.",
        type="YLIOPISTO / MOOC",
    ),
    Course(
        name="FiTech – Tekoäly", provider="Yliopistoverkosto (Aalto ym.)",
        url="https://fitech.io/fi/opinnot/?s=teko%C3%A4ly",
        desc="Suomen laajin ilmainen tekniikan tarjonta. Etäopintoja Aallosta, LUTista ja Oulusta.",
        type="YLIOPISTO / ETÄ",
    ),
    Course(
        name="Aalto Avoin: Art & Media", provider="Aalto Arts",
        url="https://www.aalto.fi/fi/taiteiden-ja-suunnittelun-korkeakoulu",
        desc="Seuraa Aalto Artsin avoimia kursseja. Usein AI- ja mediayhteyksiä.",
        type="YLIOPISTO (HKI)",
    ),
    Course(
        name="3AMK (AI & Future)", provider="Metropolia, Haaga-Helia, Laurea",
        url="https://www.3amk.fi/",
        desc="Pääkaupunkiseudun korkeakoulujen yhteiset tulevaisuuskurssit.",
        type="AMK (HKI)",
    ),
    Course(
        name="DeepLearning.AI: AI for Everyone", provider="DeepLearning.AI",
        url="https://www.deeplearning.ai/courses/ai-for-everyone/",
        desc="Andrew Ng:n kurssi bisnespuolelle ja tuottajille. Ei vaadi koodausta.",
        type="KV / ETÄ",
    ),
]

# Taitotalo-hakututkan kohde-URL (eriytetty, helppo muuttaa)
TAITOTALO_URL = (
    "https://www.taitotalo.fi/koulutukset/ict-ja-media/109191-6279-6315-"
    "digimarkkinoinnin-asiantuntija-verkko-opiskelu-media-alan-ja-kuvallisen-"
    "ilmaisun-perustutkinnon-osa"
)

TRAINING_TOPICS: dict[str, str] = {
    "Kaikki aiheet":       "media viestintä",
    "Viestintä":           "viestintä",
    "Graafinen":           "graafinen",
    "Osatutkinnot":        "osatutkinto",
    "Tutkinnon osat":      "tutkinnon osa",
    "Osatutkintokoulutus": "osatutkintokoulutus",
}
