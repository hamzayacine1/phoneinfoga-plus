# -*- coding: utf-8 -*-
"""
PhoneInfoga+ : interface web améliorée + scanners supplémentaires
- Proxifie l'API PhoneInfoga (port 5000)
- Ajoute : Truecaller, Eyecon, Twilio Lookup, Abstract API, Numverify,
  Google CSE, recherche DuckDuckGo/Bing, annuaire Tellows
- Les clés/tokens sont envoyés par le navigateur à chaque requête,
  jamais stockés côté serveur.
"""
import json
import os
import random
import re
import string
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus, urlencode

import phonenumbers as pn
from phonenumbers import carrier as pn_carrier
from phonenumbers import geocoder as pn_geocoder
from phonenumbers import timezone as pn_tz
import requests
<<<<<<< HEAD
from flask import Flask, jsonify, request, Response
=======
from flask import Flask, jsonify, request, Response, send_file
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)

PHONEINFOGA = "http://127.0.0.1:5000"  # optionnel : moteur PhoneInfoga si présent
APP_DIR = os.path.dirname(os.path.abspath(__file__))
UA_MOBILE = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Mobile Safari/537.36"

app = Flask(__name__)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def normalize_number(raw, country_code):
    """Retourne (e164_sans_plus, e164_avec_plus) ou (None, erreur)."""
    if not raw:
        return None, "Numéro vide"
    s = re.sub(r"[^0-9+]", "", raw)
    if s.startswith("00"):
        s = "+" + s[2:]
    if s.startswith("+"):
        digits = s[1:]
        if len(digits) < 6 or len(digits) > 15:
            return None, "Numéro invalide (6-15 chiffres)"
        return digits, "+" + digits
    # format national -> international avec l'indicatif du pays
    country_code = str(country_code or "").replace("+", "").strip()
    if not country_code:
        return None, "Indique le pays (indicatif) pour un numéro sans +"
    digits = re.sub(r"[^0-9]", "", s)
    if digits.startswith("0"):
        digits = digits[1:]
    if not digits:
        return None, "Numéro invalide"
    return country_code + digits, "+" + country_code + digits


def pi_get(path, timeout=20):
    """Appelle l'API PhoneInfoga locale."""
    r = requests.get(PHONEINFOGA + path, timeout=timeout)
    r.raise_for_status()
    return r.json()


def safe(fn):
    """Exécute un scanner, renvoie toujours un dict JSON."""
    def wrapper(*a, **k):
        try:
            data = fn(*a, **k)
            return {"ok": True, "data": data}
        except Exception as e:  # noqa
            return {"ok": False, "error": str(e)[:300]}
    return wrapper


# ----------------------------------------------------------------------------
# Truecaller : obtention automatique du token par OTP SMS
# (flux documenté du package open-source truecallerpy — version officielle
#  de l'API non-officielle. Le clientsecret est une constante publique du
#  package, pas un secret de notre serveur.)
# ----------------------------------------------------------------------------
TC_CLIENTSECRET = "lvc22mp3l1sfv6ujg83rd17btt"
TC_UA = "Truecaller/11.75.5 (Android;10)"
TC_LOGIN_URL = "https://account-asia-south1.truecaller.com/v2/sendOnboardingOtp"
TC_VERIFY_URL = "https://account-asia-south1.truecaller.com/v1/verifyOnboardingOtp"

# table indicative -> code ISO2 (pays les plus courants + zone francophone)
ISO2 = {
    1: "US", 7: "RU", 20: "EG", 27: "ZA", 30: "GR", 31: "NL", 32: "BE", 33: "FR",
    34: "ES", 36: "HU", 39: "IT", 40: "RO", 41: "CH", 43: "AT", 44: "GB", 45: "DK",
    46: "SE", 47: "NO", 48: "PL", 49: "DE", 52: "MX", 55: "BR", 61: "AU", 62: "ID",
    63: "PH", 64: "NZ", 65: "SG", 66: "TH", 81: "JP", 82: "KR", 84: "VN", 86: "CN",
    90: "TR", 91: "IN", 92: "PK", 94: "LK", 98: "IR", 212: "MA", 213: "DZ", 216: "TN",
    218: "LY", 220: "GM", 221: "SN", 222: "MR", 223: "ML", 224: "GN", 225: "CI",
    226: "BF", 227: "NE", 228: "TG", 229: "BJ", 230: "MU", 231: "LR", 232: "SL",
    233: "GH", 234: "NG", 235: "TD", 236: "CF", 237: "CM", 238: "CV", 239: "ST",
    240: "GQ", 241: "GA", 242: "CG", 243: "CD", 244: "AO", 245: "GW", 248: "SC",
    249: "SD", 250: "RW", 251: "ET", 252: "SO", 253: "DJ", 254: "KE", 255: "TZ",
    256: "UG", 257: "BI", 258: "MZ", 260: "ZM", 261: "MG", 262: "YT", 263: "ZW",
    264: "NA", 265: "MW", 266: "LS", 267: "BW", 268: "SZ", 269: "KM", 290: "SH",
    297: "AW", 350: "GI", 351: "PT", 352: "LU", 353: "IE", 354: "IS", 355: "AL",
    356: "MT", 357: "CY", 358: "FI", 359: "BG", 370: "LT", 371: "LV", 372: "EE",
    373: "MD", 374: "AM", 375: "BY", 376: "AD", 377: "MC", 378: "SM", 380: "UA",
    381: "RS", 382: "ME", 385: "HR", 386: "SI", 387: "BA", 389: "MK", 420: "CZ",
    421: "SK", 423: "LI", 500: "FK", 501: "BZ", 502: "GT", 503: "SV", 504: "HN",
    505: "NI", 506: "CR", 507: "PA", 508: "PM", 509: "HT", 590: "GP", 591: "BO",
    592: "GY", 593: "EC", 594: "GF", 595: "PY", 596: "MQ", 597: "SR", 598: "UY",
    599: "CW", 670: "TL", 673: "BN", 674: "NR", 675: "PG", 676: "TO", 677: "SB",
    678: "VU", 679: "FJ", 681: "WF", 682: "CK", 683: "NU", 685: "WS", 686: "KI",
    687: "NC", 688: "TV", 689: "PF", 690: "TK", 691: "FM", 692: "MH", 850: "KP",
    852: "HK", 853: "MO", 855: "KH", 856: "LA", 880: "BD", 886: "TW", 960: "MV",
    961: "LB", 962: "JO", 963: "SY", 964: "IQ", 965: "KW", 966: "SA", 967: "YE",
    968: "OM", 970: "PS", 971: "AE", 972: "IL", 973: "BH", 974: "QA", 975: "BT",
    976: "MN", 977: "NP", 992: "TJ", 993: "TM", 994: "AZ", 995: "GE", 996: "KG",
    998: "UZ",
}

# stockage temporaire des requestId OTP (mémoire, par numéro)
_tc_otp = {}


def tc_parse_number(e164):
    """Décompose un E164 -> (indicatif, iso2, numéro national)."""
    s = e164.replace("+", "").strip()
    for n in (3, 2, 1):
        if int(s[:n]) in ISO2:
            return int(s[:n]), ISO2[int(s[:n])], s[n:]
    return None, None, None


@app.route("/api/tc/login", methods=["POST"])
def tc_login():
    """Demande l'envoi d'un SMS OTP Truecaller pour le numéro donné."""
    body = request.get_json(force=True, silent=True) or {}
    raw = body.get("number", "")
    digits = re.sub(r"[^0-9+]", "", raw)
    if not digits.startswith("+"):
        digits = "+" + digits
    cc, iso, national = tc_parse_number(digits)
    if not cc:
        return jsonify({"ok": False, "error": "Indicatif pays non reconnu"}), 400
    if len(national) < 6:
        return jsonify({"ok": False, "error": "Numéro trop court"}), 400

    device_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    payload = {
        "countryCode": iso,
        "dialingCode": cc,
        "installationDetails": {
            "app": {"buildVersion": 5, "majorVersion": 11, "minorVersion": 7, "store": "GOOGLE_PLAY"},
            "device": {
                "deviceId": device_id,
                "language": "en",
                "manufacturer": "Google",
                "model": "Pixel 5",
                "osName": "Android",
                "osVersion": "10",
                "mobileServices": ["GMS"],
            },
            "language": "en",
        },
        "phoneNumber": national,
        "region": "region-2",
        "sequenceNo": 2,
    }
    headers = {
        "content-type": "application/json; charset=UTF-8",
        "accept-encoding": "gzip",
        "user-agent": TC_UA,
        "clientsecret": TC_CLIENTSECRET,
    }
    try:
        r = requests.post(TC_LOGIN_URL, json=payload, headers=headers, timeout=20)
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": f"Réseau : {str(e)[:120]}"}), 502
    try:
        j = r.json()
    except Exception:
        j = {}
    if r.status_code != 200 or not j.get("requestId"):
        msg = j.get("message") or j.get("error") or j.get("detail") or f"HTTP {r.status_code}"
        return jsonify({"ok": False, "error": f"Truecaller : {msg}"}), 502
    _tc_otp[digits] = {"requestId": j["requestId"], "deviceId": device_id}
    return jsonify({"ok": True, "message": "Code SMS envoyé", "requestId": j["requestId"]})


@app.route("/api/tc/verify", methods=["POST"])
def tc_verify():
    """Vérifie le code OTP et retourne l'installationId (= token de recherche)."""
    body = request.get_json(force=True, silent=True) or {}
    raw = body.get("number", "")
    digits = re.sub(r"[^0-9+]", "", raw)
    if not digits.startswith("+"):
        digits = "+" + digits
    otp = re.sub(r"[^0-9]", "", body.get("code", "") or "")
    st = _tc_otp.get(digits)
    if not st:
        return jsonify({"ok": False, "error": "Aucune demande OTP en cours — relance l'envoi du code"}), 400
    if len(otp) < 4:
        return jsonify({"ok": False, "error": "Code OTP invalide"}), 400
    cc, iso, national = tc_parse_number(digits)
    payload = {
        "countryCode": iso,
        "dialingCode": cc,
        "phoneNumber": national,
        "requestId": st["requestId"],
        "token": otp,
    }
    headers = {
        "content-type": "application/json; charset=UTF-8",
        "accept-encoding": "gzip",
        "user-agent": TC_UA,
        "clientsecret": TC_CLIENTSECRET,
    }
    try:
        r = requests.post(TC_VERIFY_URL, json=payload, headers=headers, timeout=20)
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": f"Réseau : {str(e)[:120]}"}), 502
    try:
        j = r.json()
    except Exception:
        j = {}
    if r.status_code != 200 or not j.get("installationId"):
        msg = j.get("message") or j.get("error") or f"HTTP {r.status_code}"
        return jsonify({"ok": False, "error": f"Truecaller : {msg}"}), 502
    _tc_otp.pop(digits, None)
    return jsonify({"ok": True, "installationId": j["installationId"],
                    "userId": j.get("userId"), "ttl": j.get("ttl")})


# ----------------------------------------------------------------------------
# Remplissage automatique des clés depuis un bloc d'en-têtes collé
# ----------------------------------------------------------------------------
@app.route("/api/parse_headers", methods=["POST"])
def parse_headers():
    text = (request.get_json(force=True, silent=True) or {}).get("text", "")
    if not text:
        return jsonify({"ok": False, "error": "Texte vide"}), 400
    out = {}

    def grab(pattern, key, transform=None, multiline=False):
        m = re.search(pattern, text, re.I | (re.S if multiline else 0))
        if m:
            v = m.group(1).strip().strip('"').strip("'").strip()
            if v and transform:
                v = transform(v)
            if v:
                out[key] = v

    grab(r"authorization\s*[:=]\s*\"?([^\"\r\n]+)\"?", "truecallerToken",
         lambda v: v if v.lower().startswith("bearer") else f"Bearer {v}")
    grab(r"e-auth-v\s*[:=]\s*\"?([^\"\r\n]+)\"?", "eyeconAuthV")
    grab(r"e-auth-c\s*[:=]\s*\"?([^\"\r\n]+)\"?", "eyeconAuthC")
    grab(r"e-auth\s*[:=]\s*\"?([^\"\r\n]+)\"?", "eyeconAuth")
    grab(r"(?:account[ _-]?sid|accountsid)\s*[:=]\s*\"?([A-Za-z0-9]+)\"?", "twilioSid")
    grab(r"(?:auth[ _-]?token|auth_token)\s*[:=]\s*\"?([A-Za-z0-9]+)\"?", "twilioToken")

    # formats JSON simples : {"authorization": "...", "e-auth": "..."}
    for key, field in [("truecallerToken", r"authorization|auth|token"),
                       ("eyeconAuthV", r"e-auth-v|e_auth_v"),
                       ("eyeconAuthC", r"e-auth-c|e_auth_c"),
                       ("eyeconAuth", r"e-auth|e_auth")]:
        if key not in out:
            grab(r"\"(?:%s)\"\s*:\s*\"([^\"]+)\"" % field, key,
                 (lambda v: v if v.lower().startswith("bearer") else f"Bearer {v}") if key == "truecallerToken" else None)

    if not out:
        return jsonify({"ok": False, "error": "Aucune clé reconnue dans le texte. Colle des lignes comme : authorization: Bearer …, e-auth: …, e-auth-v: …"}), 400
    return jsonify({"ok": True, "found": out})


# ----------------------------------------------------------------------------
# Scanners "locaux" (sans clé)
# ----------------------------------------------------------------------------
@safe
def scan_local(digits):
    """Validation & formatage 100% local (librairie phonenumbers — la même
    que celle utilisée par PhoneInfoga). Aucun serveur externe requis."""
    try:
        num = pn.parse("+" + digits, None)
    except Exception as e:
        raise Exception(f"Numéro invalide : {e}")
    valid = pn.is_valid_number(num)
    e164 = pn.format_number(num, pn.PhoneNumberFormat.E164)
    intl = pn.format_number(num, pn.PhoneNumberFormat.INTERNATIONAL)
    nat = pn.format_number(num, pn.PhoneNumberFormat.NATIONAL)
    region = pn.region_code_for_number(num)
    cc = num.country_code
    country_name = None
    try:
        country_name = pn_geocoder.country_name_for_number(num, "fr")
    except Exception:
        pass
    tz = list(pn_tz.time_zones_for_number(num))[:2]
<<<<<<< HEAD
=======
    operateur = None
    try:
        if pn_carrier.name_for_number(num, "fr"):
            operateur = pn_carrier.name_for_number(num, "fr")
    except Exception:
        pass
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
    return {
        "e164": e164,
        "international": intl,
        "local": nat,
        "raw_local": e164[1:],
        "pays": region or country_name,
        "pays_nom": country_name,
        "indicatif": cc,
        "valide": valid,
        "fuseaux": tz,
<<<<<<< HEAD
=======
        "operateur": operateur,
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
    }


@safe
def scan_dorks(digits, e164):
    """Génère une liste étendue de Google dorks (aucune API requise)."""
    num_plain = digits
    num_plus = e164.replace("+", "")
    num_space = " ".join(digits)  # ex: 3 3 6 1 2 3 4 5 6 7 8 (utile pour annuaires)
    sites = [
        ("Facebook", "facebook.com"),
        ("X / Twitter", "twitter.com OR x.com"),
        ("Instagram", "instagram.com"),
        ("LinkedIn", "linkedin.com"),
        ("TikTok", "tiktok.com"),
        ("Snapchat", "snapchat.com"),
        ("YouTube", "youtube.com"),
        ("Reddit", "reddit.com"),
        ("Pinterest", "pinterest.com"),
        ("GitHub", "github.com"),
        ("Telegram", "t.me"),
        ("VK", "vk.com"),
        ("Pastebin", "pastebin.com"),
        ("WhatsApp", "wa.me"),
        ("Skype", "skype.com OR join.skype.com"),
        ("Forums & autres", "phpbb.com OR discourse.org OR vbulletin.com"),
    ]
    out = []
    for label, site in sites:
        dork = f'site:{site} intext:"{num_plain}" OR intext:"{num_plus}" OR intext:"{num_space}"'
        out.append({"site": label, "dork": dork,
                    "url": "https://www.google.com/search?q=" + quote_plus(dork)})
    # documents publics + annuaires inversés
    extra = [
        ("Documents (PDF/DOC)", 'filetype:pdf OR filetype:doc OR filetype:docx "{num_plain}"'),
        ("Annuaires inversés", '"tel:{num_plain}" OR "tel:+{num_plus}"'),
        ("Ventes (eBay/LBC)", 'site:ebay.com OR site:leboncoin.fr "{num_plain}"'),
        ("Réseaux sociaux globaux", '"{num_plain}" OR "{num_plus}" (facebook.com OR twitter.com OR instagram.com OR linkedin.com)'),
        ("Pages blanches", '"{num_plain}" (pagesjaunes.fr OR annuaire.com OR 118712.fr OR pagesblanches.fr)'),
    ]
    for label, dork_tpl in extra:
        dork = dork_tpl.format(num_plain=num_plain, num_plus=num_plus)
        out.append({"site": label, "dork": dork,
                    "url": "https://www.google.com/search?q=" + quote_plus(dork)})
    # recherche générique
    out.append({"site": "Recherche Google globale", "dork": f'"{num_plain}" OR "{num_plus}"',
                "url": "https://www.google.com/search?q=" + quote_plus(f'"{num_plain}" OR "{num_plus}"')})
    return {"dorks": out, "nombre": len(out)}


@safe
def search_engine(engine, query, max_results=8):
    """Recherche web sans clé (DuckDuckGo / Bing)."""
    results = []
    if engine == "ddg":
        r = requests.get("https://html.duckduckgo.com/html/",
                         params={"q": query}, headers={"User-Agent": UA_MOBILE},
                         timeout=15)
        r.raise_for_status()
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                             r.text, re.S | re.I):
            url = m.group(1).replace("&amp;", "&")
            # DDG renvoie des liens internes /l/?uddg=...
            mm = re.search(r"uddg=([^&]+)", url)
            if mm:
                from urllib.parse import unquote
                url = unquote(mm.group(1))
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            results.append({"titre": title, "url": url})
            if len(results) >= max_results:
                break
    elif engine == "bing":
        r = requests.get("https://www.bing.com/search",
                         params={"q": query, "setlang": "fr"},
                         headers={"User-Agent": UA_MOBILE,
                                  "Accept-Language": "fr-FR,fr;q=0.9"},
                         timeout=15)
        r.raise_for_status()
        for m in re.finditer(r'<li class="b_algo".*?<h2><a href="([^"]+)"[^>]*>(.*?)</a>',
                             r.text, re.S | re.I):
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            results.append({"titre": title, "url": m.group(1)})
            if len(results) >= max_results:
                break
    else:
        raise Exception(f"Moteur inconnu: {engine}")
    if not results:
        raise Exception("Aucun résultat (moteur peut bloquer le datacenter)")
    return {"moteur": engine, "resultats": results}


@safe
def scan_tellows(e164):
    """Best-effort sur tellows (notes de spam communautaires)."""
    r = requests.get(f"https://www.tellows.fr/num/{quote_plus(e164)}",
                     headers={"User-Agent": UA_MOBILE, "Accept-Language": "fr-FR"},
                     timeout=15)
    r.raise_for_status()
    text = re.sub(r"<script.*?</script>", "", r.text, flags=re.S)
    score = re.search(r"score[^\d]{0,20}(\d{1,3})", text, re.I)
    nom = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S)
    out = {"url": r.url}
    if score:
        out["score_spam"] = score.group(1)
    if nom:
        out["titre"] = re.sub(r"<[^>]+>", "", nom.group(1)).strip()[:200]
    return out


# ----------------------------------------------------------------------------
# Scanners avec clé/token (fournis par l'utilisateur dans la requête)
# ----------------------------------------------------------------------------
@safe
def scan_truecaller(e164, token):
    if not token:
        raise Exception("Token Truecaller manquant")
    digits = e164.replace("+", "")
    cc = digits[:2]
    if digits.startswith("1"):
        cc = "1"  # USA/Canada : indicatif à 1 chiffre
    elif digits.startswith("7"):  # Russie/Kazakhstan
        cc = "7"
    url = ("https://search5-noneu.truecaller.com/v2/search?"
           + urlencode({"q": digits, "countryCode": cc, "type": "4", "locAddr": "",
                        "placement": "SEARCHRESULTS,HISTORY,DETAILS", "encoding": "json"}))
    headers = {
        "User-Agent": "Truecaller/14.1.6 (Android;14)",
        "Accept-Encoding": "gzip",
        "Authorization": token if token.lower().startswith("bearer") else f"Bearer {token}",
    }
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 403:
        raise Exception("Accès refusé (403) : token invalide/expiré ou IP bloquée")
    if r.status_code == 401:
        raise Exception("Token non autorisé (401) : vérifie ton token Truecaller")
    r.raise_for_status()
    j = r.json()
    if not j.get("data"):
        raise Exception("Aucune donnée : numéro introuvable ou réponse vide")
    d = j["data"][0]
    phone = (d.get("phones") or [{}])[0]
    spam = d.get("spamInfo") or {}
<<<<<<< HEAD
=======
    emails = [i.get("id") for i in (d.get("internetAddresses") or []) if i.get("id")]
    socials = [{"type": i.get("type"), "id": i.get("id")}
               for i in (d.get("socialProfiles") or []) if i.get("id")]
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
    return {
        "nom": d.get("name"),
        "pays": d.get("country", {}).get("name") if isinstance(d.get("country"), dict) else d.get("country"),
        "carrier": phone.get("carrier"),
        "type_ligne": phone.get("numberType"),
        "score_spam": spam.get("score"),
        "categorie_spam": spam.get("category"),
        "url_avatar": d.get("image"),
<<<<<<< HEAD
=======
        "emails": emails[:5],
        "reseaux": socials[:8],
        "verifie": bool(d.get("isVerified")),
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
        "brut": j,
    }


@safe
def scan_eyecon(e164, cfg):
    auth, auth_v, auth_c = cfg.get("eyeconAuth", ""), cfg.get("eyeconAuthV", ""), cfg.get("eyeconAuthC", "")
    if not (auth and auth_v and auth_c):
        raise Exception("Clés Eyecon manquantes (e-auth, e-auth-v, e-auth-c)")
    digits = e164.replace("+", "")
    cc = digits[:2]
    if digits.startswith("1"):
        cc = "1"
    elif digits.startswith("7"):
        cc = "7"
    url = ("https://api.eyecon-app.com/app/getnames.jsp?cli=" + cc + digits +
           "&lang=fr&is_callerid=true&is_ic=true&cv=vc_312_vn_2.0.312_a"
           "&requestApi=URLconnection&source=Other")
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; GM1903 Build/QKQ1.190716.003)",
        "Accept": "application/json",
        "Connection": "Keep-Alive",
        "e-auth-v": auth_v,
        "e-auth-c": auth_c,
        "e-auth": auth,
        "content-type": "application/x-www-form-urlencoded",
    }
    r = requests.post(url, headers=headers, timeout=15)
    if r.status_code in (401, 403):
        raise Exception(f"Accès refusé ({r.status_code}) : clés Eyecon invalides ou expirées")
    r.raise_for_status()
    j = r.json()
    data = j.get("data") or []
    out = []
    for item in data[:10]:
        out.append({
            "nom": item.get("name"),
            "telephone": item.get("phone"),
            "lieu": item.get("location"),
            "spam": item.get("spam"),
<<<<<<< HEAD
=======
            "type_appelant": item.get("caller_type") or item.get("callerType"),
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
        })
    if not out:
        raise Exception("Aucune donnée Eyecon (numéro introuvable ou clés expirées)")
    return {"resultats": out, "brut": j}


@safe
def scan_twilio(e164, cfg):
    sid, tok = cfg.get("twilioSid", ""), cfg.get("twilioToken", "")
    if not (sid and tok):
        raise Exception("Clés Twilio manquantes (SID + Auth Token)")
    # Lookup API v2
    url = f"https://lookups.twilio.com/v2/PhoneNumbers/{quote_plus(e164)}"
    try:
        r = requests.get(url, params={"Fields": "carrier,caller_name,line_type_intelligence"},
                         auth=(sid, tok), timeout=15)
        r.raise_for_status()
        j = r.json()
        car = j.get("carrier") or {}
        return {
            "carrier": car.get("name"),
            "type_ligne": j.get("line_type_intelligence") or j.get("line_type"),
            "pays": j.get("country_code"),
            "operateur_mcc": car.get("mobile_country_code"),
            "operateur_mnc": car.get("mobile_network_code"),
            "nom_appelant": (j.get("caller_name") or {}).get("caller_name"),
            "brut": j,
        }
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return {"note": "Numéro inconnu de Twilio (aucune donnée)", "brut": None}
        raise


@safe
def scan_abstract(e164, key):
    if not key:
        raise Exception("Clé Abstract API manquante")
    r = requests.get("https://phonevalidation.abstractapi.com/v1/",
                     params={"api_key": key, "phone": e164}, timeout=15)
    r.raise_for_status()
    j = r.json()
    return {
        "valide": j.get("valid"),
        "pays": j.get("country"),
        "carrier": j.get("carrier"),
        "type_ligne": j.get("line_type"),
        "localisation": j.get("location"),
        "brut": j,
    }


@safe
def scan_numverify(e164, key):
    if not key:
        raise Exception("Clé Numverify manquante")
    r = requests.get("http://apilayer.net/api/validate",
                     params={"access_key": key, "number": e164, "format": "1"}, timeout=15)
    r.raise_for_status()
    j = r.json()
    if j.get("success") is False:
        raise Exception(j.get("error", {}).get("info", "erreur Numverify"))
    return {
        "valide": j.get("valid"),
        "pays": j.get("country_name"),
        "localisation": j.get("location"),
        "carrier": j.get("carrier"),
        "type_ligne": j.get("line_type"),
        "brut": j,
    }


@safe
def scan_cse(e164, cfg):
    key, cx = cfg.get("cseKey", ""), cfg.get("cseCx", "")
    if not (key and cx):
        raise Exception("Clés Google CSE manquantes (API key + CX)")
    q = f'"{e164.replace("+", "")}" OR "{e164}"'
    r = requests.get("https://www.googleapis.com/customsearch/v1",
                     params={"key": key, "cx": cx, "q": q, "num": 10}, timeout=15)
    r.raise_for_status()
    j = r.json()
    items = j.get("items") or []
    return {"resultats": [{"titre": i.get("title"), "url": i.get("link"),
                           "extrait": i.get("snippet")} for i in items],
            "nombre": len(items)}


@safe
def scan_numlookup(e164, key):
    """Numlookup API (numlookupapi.com) — gratuit ~250/mois."""
    if not key:
        raise Exception("Clé Numlookup manquante")
    r = requests.get(f"https://api.numlookupapi.com/v1/validate/{quote_plus(e164)}",
                     params={"apikey": key}, timeout=15)
    if r.status_code in (401, 403):
        raise Exception("Clé Numlookup invalide (401/403)")
    r.raise_for_status()
    j = r.json()
    if j.get("valid") is False and not j.get("number"):
        raise Exception("Numéro invalide ou inconnu")
    return {
        "valide": j.get("valid"),
        "pays": j.get("country_name"),
        "code_pays": j.get("country_code"),
        "localisation": j.get("location"),
        "carrier": j.get("carrier"),
        "type_ligne": j.get("line_type"),
        "format_international": j.get("international_format"),
        "format_local": j.get("local_format"),
        "brut": j,
    }


@safe
def scan_veriphone(e164, key):
    """Veriphone.io — API officielle avec plan gratuit."""
    if not key:
        raise Exception("Clé Veriphone manquante")
    r = requests.get("https://veriphone.io/api/v2/verify",
                     params={"phone": e164, "key": key}, timeout=15)
    if r.status_code in (401, 403):
        raise Exception("Clé Veriphone invalide (401/403)")
    r.raise_for_status()
    j = r.json()
    if j.get("status") not in ("success", "failed"):
        raise Exception("Réponse Veriphone inattendue")
    return {
        "valide": j.get("phone_valid"),
        "type_ligne": j.get("phone_type"),
        "region": j.get("phone_region"),
        "pays": j.get("country"),
        "carrier": j.get("carrier"),
        "e164": j.get("e164"),
        "brut": j,
    }


@safe
def scan_opencnam(e164, cfg):
    """OpenCNAM — lookup du nom de l'appelant (CNAM)."""
    sid, tok = cfg.get("opencnamSid", ""), cfg.get("opencnamToken", "")
    if not (sid and tok):
        raise Exception("Clés OpenCNAM manquantes (Account SID + Auth Token)")
    r = requests.get(f"https://api.opencnam.com/v3/phone/{quote_plus(e164)}",
                     params={"format": "json", "account_sid": sid, "auth_token": tok},
                     timeout=15)
    if r.status_code in (401, 403):
        raise Exception("Clés OpenCNAM invalides (401/403)")
    if r.status_code == 404:
        return {"nom": None, "note": "Pas de nom CNAM pour ce numéro", "brut": None}
    r.raise_for_status()
    j = r.json()
    return {"nom": j.get("name"), "note": j.get("status") or j.get("message"), "brut": j}


@safe
def scan_iqs(e164, key):
    """IPQualityScore Phone Lookup — gratuit 500/mois."""
    if not key:
        raise Exception("Clé IPQualityScore manquante")
    num = e164.replace("+", "")
    r = requests.get(f"https://ipqualityscore.com/api/json/phone/{key}/{num}",
                     params={"strictness": 2}, timeout=15)
    if r.status_code in (401, 403):
        raise Exception("Clé IPQualityScore invalide (401/403)")
    r.raise_for_status()
    j = r.json()
    if j.get("success") is False:
        raise Exception(j.get("message", "erreur IPQualityScore"))
    return {
        "valide": j.get("valid"),
        "actif": j.get("active"),
        "carrier": j.get("carrier"),
        "type_ligne": j.get("line_type"),
        "pays": j.get("country"),
        "score_fraude": j.get("fraud_score"),
        "abus_recent": j.get("recent_abuse"),
        "spam": j.get("spam"),
        "brut": j,
    }


@safe
def scan_omkar(e164, key):
    """OmkarCloud Phone Lookup API — 200 gratuits/mois."""
    if not key:
        raise Exception("Clé OmkarCloud manquante")
    r = requests.get("https://carrier-lookup-api.omkar.cloud/lookup",
                     params={"phone": e164}, headers={"API-Key": key}, timeout=15)
    if r.status_code in (401, 403):
        raise Exception("Clé OmkarCloud invalide (401/403)")
    if r.status_code == 429:
        raise Exception("Limite mensuelle OmkarCloud atteinte (429)")
    r.raise_for_status()
    j = r.json()
    return {
        "carrier": j.get("carrier"),
        "type_ligne": j.get("line_type"),
        "valide": j.get("valid", j.get("success")),
        "indicatif": j.get("country_code"),
        "brut": j,
    }


@safe
def scan_callerapi(e164, key):
    """CallerAPI — agrège Truecaller + CallApp + ViewCaller + Eyecon + Hiya avec UNE clé."""
    if not key:
        raise Exception("Clé CallerAPI manquante")
    num = e164.replace("+", "")
    r = requests.get(f"https://callerapi.com/api/phone/info/{num}",
                     headers={"X-Auth": key}, timeout=20)
    if r.status_code in (401, 403):
        raise Exception("Clé CallerAPI invalide (401/403)")
    r.raise_for_status()
    j = r.json()
    if j.get("status") != "success":
        raise Exception(j.get("message", "erreur CallerAPI"))
    out = {}
    if isinstance(j.get("truecaller"), dict):
        t = j["truecaller"]
        tn = t.get("name")
        if not tn and isinstance(t.get("data"), list) and t["data"]:
            tn = t["data"][0].get("name")
        out["truecaller_nom"] = tn
        out["truecaller_type"] = t.get("number_type_label") or t.get("number_type")
        out["truecaller_fournisseur"] = t.get("provider")
    if isinstance(j.get("callapp"), dict):
        c = j["callapp"]
        out["callapp_nom"] = c.get("name")
        out["callapp_site"] = (c.get("websites") or [{}])[0].get("websiteUrl") if isinstance(c.get("websites"), list) else None
        out["callapp_categories"] = [x.get("name") for x in (c.get("categories") or [])][:3]
        out["callapp_rating"] = c.get("avgRating")
    if isinstance(j.get("viewcaller"), list):
        v = j["viewcaller"]
        out["viewcaller_top"] = v[0] if v else None
        out["viewcaller_nb_occurrences"] = v[0].get("occurrences") if v else None
    if j.get("eyecon"):
        out["eyecon_nom"] = j["eyecon"]
    if isinstance(j.get("hiya"), dict):
        h = j["hiya"]
        out["hiya_nom"] = h.get("name") or h.get("caller_name")
        out["hiya_spam"] = h.get("is_spam")
    out["brut"] = j
    return out


# ----------------------------------------------------------------------------
# Scan complet (parallèle)
# ----------------------------------------------------------------------------
SCANNERS = {
    "local": scan_local,
    "dorks": scan_dorks,
    "tellows": scan_tellows,
    "truecaller": scan_truecaller,
    "eyecon": scan_eyecon,
    "twilio": scan_twilio,
    "abstract": scan_abstract,
    "numverify": scan_numverify,
    "cse": scan_cse,
    "numlookup": scan_numlookup,
    "veriphone": scan_veriphone,
    "opencnam": scan_opencnam,
    "iqs": scan_iqs,
    "omkar": scan_omkar,
    "callerapi": scan_callerapi,
}


@app.route("/api/scan", methods=["POST"])
def api_scan():
    body = request.get_json(force=True, silent=True) or {}
    raw = body.get("number", "")
    cc = body.get("country", "")
    digits, e164 = normalize_number(raw, cc)
    if not digits:
        return jsonify({"ok": False, "error": e164}), 400

    cfg = body.get("config", {}) or {}
    engines = [e for e in body.get("engines", ["ddg"]) if e in ("ddg", "bing")]

    def run_local():
        return scan_local(digits)

    def run_dorks():
        return scan_dorks(digits, e164)

    tasks = {"local": run_local, "dorks": run_dorks}
    # Recherches web scrappées : souvent bloquées depuis un datacenter.
    # On les tente quand même (elles peuvent marcher), sinon l'UI propose
    # d'ouvrir la recherche dans le navigateur.
    if engines:
        def run_eng(engine):
            q = f'"{digits}" OR "{e164}"'
            return search_engine(engine, q)
        for e in engines:
            tasks[f"web_{e}"] = (lambda eng=e: run_eng(eng))

    # scanners à clé : seulement si l'utilisateur a fourni les clés
    if cfg.get("truecallerToken"):
        tasks["truecaller"] = lambda: scan_truecaller(e164, cfg.get("truecallerToken", ""))
    if cfg.get("eyeconAuth") and cfg.get("eyeconAuthV") and cfg.get("eyeconAuthC"):
        tasks["eyecon"] = lambda: scan_eyecon(e164, cfg)
    if cfg.get("twilioSid") and cfg.get("twilioToken"):
        tasks["twilio"] = lambda: scan_twilio(e164, cfg)
    if cfg.get("abstractKey"):
        tasks["abstract"] = lambda: scan_abstract(e164, cfg.get("abstractKey", ""))
    if cfg.get("numverifyKey"):
        tasks["numverify"] = lambda: scan_numverify(e164, cfg.get("numverifyKey", ""))
    if cfg.get("cseKey") and cfg.get("cseCx"):
        tasks["cse"] = lambda: scan_cse(e164, cfg)
    if cfg.get("numlookupKey"):
        tasks["numlookup"] = lambda: scan_numlookup(e164, cfg.get("numlookupKey", ""))
    if cfg.get("veriphoneKey"):
        tasks["veriphone"] = lambda: scan_veriphone(e164, cfg.get("veriphoneKey", ""))
    if cfg.get("opencnamSid") and cfg.get("opencnamToken"):
        tasks["opencnam"] = lambda: scan_opencnam(e164, cfg)
    if cfg.get("iqsKey"):
        tasks["iqs"] = lambda: scan_iqs(e164, cfg.get("iqsKey", ""))
    if cfg.get("omkarKey"):
        tasks["omkar"] = lambda: scan_omkar(e164, cfg.get("omkarKey", ""))
    if cfg.get("callerapiKey"):
        tasks["callerapi"] = lambda: scan_callerapi(e164, cfg.get("callerapiKey", ""))
    # tellows : best-effort, ignoré silencieusement en cas d'échec
    # (souvent bloqué depuis un datacenter -> on ne l'inclut pas par défaut)

    results = {}
    with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results[name] = fut.result()
            except Exception as e:  # noqa
                results[name] = {"ok": False, "error": str(e)[:300]}

    # tri : locaux d'abord, puis web, puis ceux à clé
    order = ["local", "dorks", "tellows", "web_ddg", "web_bing",
             "numlookup", "veriphone", "opencnam", "iqs", "omkar", "callerapi",
             "truecaller", "eyecon", "twilio", "abstract", "numverify", "cse"]
    ordered = {}
    for k in order:
        if k in results:
            ordered[k] = results[k]
    for k in results:
        if k not in ordered:
            ordered[k] = results[k]

    return jsonify({"ok": True, "number": e164, "scanners": ordered})


@app.route("/api/scanner/<name>", methods=["POST"])
def api_scanner(name):
    """Relance UN seul scanner sur un numéro (pour la ré-exécution ciblée)."""
    body = request.get_json(force=True, silent=True) or {}
    raw = body.get("number", "")
    cc = body.get("country", "")
    digits, e164 = normalize_number(raw, cc)
    if not digits:
        return jsonify({"ok": False, "error": e164}), 400
    cfg = body.get("config", {}) or {}

    if name == "local":
        res = scan_local(digits)
    elif name == "dorks":
        res = scan_dorks(digits, e164)
    elif name == "truecaller":
        res = scan_truecaller(e164, cfg.get("truecallerToken", ""))
    elif name == "eyecon":
        res = scan_eyecon(e164, cfg)
    elif name == "twilio":
        res = scan_twilio(e164, cfg)
    elif name == "abstract":
        res = scan_abstract(e164, cfg.get("abstractKey", ""))
    elif name == "numverify":
        res = scan_numverify(e164, cfg.get("numverifyKey", ""))
    elif name == "cse":
        res = scan_cse(e164, cfg)
    elif name == "numlookup":
        res = scan_numlookup(e164, cfg.get("numlookupKey", ""))
    elif name == "veriphone":
        res = scan_veriphone(e164, cfg.get("veriphoneKey", ""))
    elif name == "opencnam":
        res = scan_opencnam(e164, cfg)
    elif name == "iqs":
        res = scan_iqs(e164, cfg.get("iqsKey", ""))
    elif name == "omkar":
        res = scan_omkar(e164, cfg.get("omkarKey", ""))
    elif name == "callerapi":
        res = scan_callerapi(e164, cfg.get("callerapiKey", ""))
    else:
        return jsonify({"ok": False, "error": f"Scanner inconnu: {name}"}), 400

    return jsonify({"ok": True, "number": e164, "scanner": name, "result": res})


@app.route("/api/search", methods=["GET"])
def api_search():
    engine = request.args.get("engine", "ddg")
    q = request.args.get("q", "")
    n = int(request.args.get("max", 8))
    if not q:
        return jsonify({"ok": False, "error": "q manquant"}), 400
    res = search_engine(engine, q, n)
    return jsonify({"ok": res["ok"], **({"data": res["data"]} if res["ok"] else {"error": res["error"]})})


# ----------------------------------------------------------------------------
# Proxy vers PhoneInfoga (scanners d'origine + UI d'origine si besoin)
# ----------------------------------------------------------------------------
@app.route("/pi/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def pi_proxy(path):
    url = f"{PHONEINFOGA}/{path}"
    params = request.args.to_dict()
    headers = {"Content-Type": request.content_type or "application/json"}
    if request.method == "GET":
        r = requests.get(url, params=params, headers=headers, timeout=25)
    else:
        r = requests.request(request.method, url, params=params,
                             data=request.get_data(), headers=headers, timeout=25)
    resp = Response(r.content, status=r.status_code)
    resp.headers["Content-Type"] = r.headers.get("Content-Type", "application/json")
    return resp


@app.route("/api/health")
def api_health():
<<<<<<< HEAD
    """Healthcheck pour les hébergeurs (Render, Railway…)."""
    try:
        r = requests.get(PHONEINFOGA + "/api/", timeout=5)
        pi = r.status_code == 200
    except Exception:
        pi = False
    return jsonify({"ok": True, "phoneinfoga": pi})
=======
    """Healthcheck pour les hébergeurs (Render, Railway…) et le gardien anti-sommeil."""
    return jsonify({"ok": True, "phoneinfoga": True, "ts": int(__import__("time").time())})


@app.route("/api/scan/batch", methods=["POST"])
def api_scan_batch():
    """Analyse plusieurs numéros en une seule requête (un par ligne)."""
    body = request.get_json(force=True, silent=True) or {}
    numbers = [n.strip() for n in body.get("numbers", []) if n and n.strip()]
    if not numbers:
        return jsonify({"ok": False, "error": "Aucun numéro fourni"}), 400
    cc = body.get("country", "")
    cfg = body.get("config", {}) or {}
    out = []
    for raw in numbers[:30]:
        digits, e164 = normalize_number(raw, cc)
        if not digits:
            out.append({"input": raw, "ok": False, "error": e164})
            continue
        loc = scan_local(digits)
        dorks = scan_dorks(digits, e164)
        tc = None
        if cfg.get("truecallerToken"):
            tc = scan_truecaller(e164, cfg.get("truecallerToken", ""))
        out.append({
            "input": raw, "ok": True, "number": e164,
            "local": loc, "dorks": dorks, "truecaller": tc,
        })
    return jsonify({"ok": True, "results": out})


# ----------------------------------------------------------------------------
# PWA (installation sur l'écran d'accueil)
# ----------------------------------------------------------------------------
@app.route("/manifest.webmanifest")
def manifest():
    return send_file(os.path.join(APP_DIR, "manifest.webmanifest"),
                     mimetype="application/manifest+json")


@app.route("/sw.js")
def sw():
    return send_file(os.path.join(APP_DIR, "sw.js"), mimetype="application/javascript")


@app.route("/icons/<name>")
def icon(name):
    if name not in ("icon-192.png", "icon-512.png"):
        return jsonify({"ok": False, "error": "not found"}), 404
    return send_file(os.path.join(APP_DIR, "icons", name), mimetype="image/png")
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)


@app.route("/")
def index():
    return Response(INDEX_HTML, content_type="text/html; charset=utf-8")


@app.after_request
def no_store(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp


INDEX_HTML = open(os.path.join(APP_DIR, "index.html"), encoding="utf-8").read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True)
