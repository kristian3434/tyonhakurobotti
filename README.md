# Mission Jobs Hub

Mission Jobs Hub on Streamlit-sovellus työnhaun, hakemusten seurannan,
työpaikkailmoitusten analysoinnin ja koulutushakujen tueksi.

## Julkisen version tietosuoja

Tämä GitHub-versio on puhdistettu julkaisua varten:

- oikeita API-avaimia tai pilvipohjaisia AI-kutsuja ei käytetä
- AI-toiminnot käyttävät oletuksena paikallista, determinististä demovastausta
- vierailudatan rajapinta on poistettu käytöstä
- käyttäjän työpaikka-, Kela-, koulutus- ja portfoliotietoja ei ole mukana
- ajon aikana syntyvät JSON-tiedostot ja välimuistit on rajattu pois Gitistä

Koodissa näkyvä `demo-api-key-not-a-real-secret` on tarkoituksella toimimaton
simulaatiotunniste. Se ei anna pääsyä mihinkään ulkoiseen palveluun.

## Käynnistys

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
streamlit run app.py
```

Sovellus luo paikalliset tallennustiedostot tarvittaessa. Niitä ei seurata
Gitissä.

## Paikallinen kielimalli

Demotilan rinnalla voi valita paikallisen Gemma/LM Studio -vaihtoehdon.
Se odottaa OpenAI-yhteensopivaa paikallista palvelinta osoitteessa
`http://127.0.0.1:1234/v1`. Paikallinen vaihtoehto ei käytä pilvi-API-avainta.

## Testit

```bash
python -m unittest discover -v
```
