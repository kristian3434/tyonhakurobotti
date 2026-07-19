# GDPR Cookie Scanner

Erillinen Streamlit-sovellus verkkosivujen eväste- ja suostumusasetusten tekniseen GDPR/ePrivacy-tarkistukseen.

## Käynnistys

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
streamlit run gdpr_app.py
```

Jos Chromium-selainta ei voi käynnistää nykyisessä ympäristössä, sovellus tekee rajatumman staattisen HTML-tarkistuksen ja näyttää siitä huomautuksen raportissa.

## Sisältö

- `gdpr_app.py` — erillinen Streamlit-sovellus.
- `gdpr_tab.py` — käyttöliittymä, raportti ja taulukot.
- `gdpr_scanner.py` — tarkistusmoottori ja GDPR/ePrivacy-säännöt.
- `test_gdpr_scanner.py` — yksikkötestit.
- `requirements.txt` — tarvittavat Python-paketit.

Tulokset ovat tekninen auditointiapu, eivät lopullinen juridinen lausunto.
