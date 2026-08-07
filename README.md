# 📞 PhoneInfoga+

Interface web améliorée pour l'OSINT de numéros de téléphone, basée sur PhoneInfoga v2.

<<<<<<< HEAD
## Fonctionnalités
- 🧭 Validation locale (librairie `phonenumbers`, la même que PhoneInfoga) — aucun serveur requis
- 🎯 22 Google Dorks ciblés (Facebook, X, Instagram, LinkedIn, TikTok, Snapchat, Reddit, Pastebin, annuaire inversé…)
- 🔗 16 liens directs (WhatsApp, Telegram, Viber, Truecaller web, Numlookup, Sync.Me, SpyDialer, annuaires…)
- 🔵 Truecaller (token par SMS automatique ou collage d'en-têtes)
- 👁️ Eyecon · 🔺 Twilio · 📦 Abstract · 🔢 Numverify · 📇 Numlookup · 📞 Veriphone · 🏷️ OpenCNAM · 🛡️ IPQualityScore · ☁️ OmkarCloud · 🔎 Google CSE · 🔀 CallerAPI
- ⚡ Remplissage automatique des clés par collage d'en-têtes capturés
- 📤 Export/Import des clés (localStorage, jamais stockées côté serveur)
=======
## ✨ Fonctionnalités

### Analyse d'un numéro
- 🧭 **Local** : validation, pays (nom complet), opérateur, fuseaux, formats E164/international/local — 100% local, aucune API
- 🎯 **22 Google Dorks** ciblés (Facebook, X, Instagram, LinkedIn, TikTok, Snapchat, Reddit, GitHub, Telegram, VK, Pastebin, WhatsApp, Skype, forums, documents PDF/DOC, annuaires inversés, ventes, pages blanches…)
- 🔗 **18 liens directs** (WhatsApp, Telegram, Viber, Truecaller web, Numlookup, Sync.Me, SpyDialer, Google Maps, MapQuest, annuaires…)

### 15 scanners avec clé (menu ⚙️)
Truecaller (token auto par SMS), Eyecon, Twilio Lookup, Abstract API, Numverify, Google CSE, Numlookup, Veriphone, OpenCNAM, IPQualityScore, OmkarCloud, CallerAPI (5-en-1 : Truecaller+CallApp+ViewCaller+Eyecon+Hiya)

### Remplissage automatique des clés
- 🔵 **Token Truecaller par SMS** : entre ton numéro → reçois le code → token créé automatiquement
- 📋 **Collage d'en-têtes** : colle une capture (authorization, e-auth…) → toutes les clés remplies d'un coup
- 📤 Export / 📥 Import JSON

### Outils avancés
- 📚 **Analyse en lot** : jusqu'à 30 numéros d'un coup + export CSV
- 🖨️ **Rapport PDF** (impression) + ⬇️ **Export JSON**
- 📂 Tout déplier/replier, historique local, thème clair/sombre
- 📱 **PWA** : installable sur l'écran d'accueil (hors-ligne)

### 🛡️ Gardien anti-sommeil
`.github/workflows/keepalive.yml` ping le site toutes les 5 min → empêche Render (plan gratuit) de s'endormir. Gratuit (GitHub Actions illimité sur dépôt public).
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)

## Déploiement

### Render (gratuit, lien permanent)
<<<<<<< HEAD
1. Fork/pousse ce dépôt sur ton compte GitHub
2. https://render.com → New + → Blueprint → choisis ce dépôt → Apply
=======
1. Ce dépôt contient `render.yaml`
2. https://render.com → New + → Blueprint → ce dépôt → Apply
>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
3. URL : `https://phoneinfoga-plus.onrender.com`

### Termux (Android)
```bash
pkg install -y python
pip install flask requests phonenumbers
python app.py
```

<<<<<<< HEAD
=======
## 🔒 Confidentialité
Les clés API restent dans le localStorage du navigateur, jamais stockées côté serveur. Aucun historique serveur.

>>>>>>> 407da16 (🚀 v2 : batch, PWA, PDF/JSON, thème, enrichissement, gardien anti-sommeil)
## Licence
GPL-3.0 (PhoneInfoga) — usage légal uniquement.
