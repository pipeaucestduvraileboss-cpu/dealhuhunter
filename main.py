

import feedparser
import re
import html
import unicodedata
from urllib.request import Request, urlopen

# ==========================================
# CONFIGURATION
# ==========================================

FEEDS = {
    "Dealabs Informatique": "https://www.dealabs.com/rss/groupe/informatique",
    "Les Numeriques": "https://www.lesnumeriques.com/rss-gooddeals.xml",
}

# ==========================================
# CATEGORIES RECHERCHEES
# ==========================================

CATEGORIES = {
    "GPU": [
        "carte graphique", "geforce", "radeon",
        "rtx", "rx "
    ],

    "CPU": [
        "processeur", "ryzen", "intel core",
        "core i5", "core i7", "core i9",
        "core ultra"
    ],

    "RAM": [
        "ram", "ddr4", "ddr5", "memoire vive"
    ],

    "SSD": [
        "ssd", "nvme"
    ],

    "CARTE MERE": [
        "carte mere", "motherboard",
        "b650", "x670", "x870",
        "z790", "z890"
    ],

    "ALIMENTATION": [
        "alimentation pc", "bloc alimentation",
        "power supply", "80 plus gold",
        "80 plus platinum"
    ],

    "BOITIER": [
        "boitier pc", "boitier gaming"
    ],

    "REFROIDISSEMENT": [
        "ventirad", "watercooling", "aio",
        "refroidissement liquide", "radiateur cpu"
    ],

    "VENTILATEUR": [
        "ventilateur pc", "ventilateur boitier"
    ],

    "ECRAN": [
        "ecran", "moniteur", "monitor",
        "oled", "qd-oled", "mini-led",
        "amoled", "ips", "144hz", "165hz",
        "180hz", "240hz", "360hz", "ultrawide"
    ],

    "CLAVIER": [
        "clavier gaming", "clavier mecanique",
        "clavier sans fil", "clavier rgb"
    ],

    "SOURIS": [
        "souris gaming", "souris sans fil",
        "souris ergonomique"
    ],

    "CASQUE": [
        "casque gaming", "casque gamer",
        "micro casque gaming"
    ]
}

# ==========================================
# PRODUITS EXCLUS
# ==========================================

EXCLUDED = [
    "pc portable",
    "ordinateur portable",
    "laptop",
    "notebook",
    "chromebook",
    "tablette",
    "ipad",
    "galaxy tab",
    "pc gamer",
    "pc gaming",
    "ordinateur gamer",
    "ordinateur gaming",
    "tour gaming",
    "tour gamer",
    "pc preassemble",
    "pc pre monte",
    "pc premonté",
    "pc assemble",
    "pc assemblé",
    "pc complet",
    "configuration gaming",
    "configuration gamer",
    "desktop gaming",
    "barebone",
    "mini pc",
    "all in one",
    "tout en un"
]

# ==========================================
# NORMALISATION DU TEXTE
# ==========================================

def normalize(text):

    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)

    text = unicodedata.normalize("NFD", text.lower())

    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )

    text = re.sub(r"[^a-z0-9]+", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def contains_keyword(text, keyword):

    keyword = normalize(keyword)

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(keyword)
        + r"(?![a-z0-9])"
    )

    return re.search(pattern, text) is not None


# ==========================================
# DETECTION DES PC COMPLETS
# ==========================================

def is_prebuilt(title, summary):

    title = normalize(title)
    summary = normalize(summary)

    # Exclusions prioritaires dans le titre
    for word in EXCLUDED:

        if contains_keyword(title, word):
            return True

    # Exclusions dans la description
    summary_exclusions = [
        "pc preassemble",
        "pc pre monte",
        "pc complet",
        "tour gaming",
        "tour gamer",
        "configuration gaming",
        "configuration gamer",
        "ordinateur gaming"
    ]

    for word in summary_exclusions:

        if contains_keyword(summary, word):
            return True

    return False


# ==========================================
# CLASSIFICATION DES OFFRES
# ==========================================

def classify(title, summary):

    title = normalize(title)
    summary = normalize(summary)

    # On refuse les PC complets
    if is_prebuilt(title, summary):
        return None

    # Le titre doit contenir un mot-clé pertinent.
    # La description seule ne suffit pas.

    for category, keywords in CATEGORIES.items():

        for keyword in keywords:

            if contains_keyword(title, keyword):

                # RTX et RX seuls ne suffisent pas
                if keyword in ["rtx", "rx "]:
                    if not any(
                        contains_keyword(title, x)
                        for x in [
                            "carte graphique",
                            "geforce",
                            "radeon"
                        ]
                    ):
                        continue

                # Les périphériques et composants
                # sont classés par catégorie.
                return category

    return None


# ==========================================
# RECHERCHE DES OFFRES
# ==========================================

def main():

    print("=" * 55)
    print("                  DEALHUNTER")
    print("       COMPOSANTS PC ET PERIPHERIQUES")
    print("=" * 55)

    seen = set()
    results = {}

    for source, url in FEEDS.items():

        print(f"\nSOURCE : {source}")

        try:

            request = Request(
                url,
                headers={
                    "User-Agent": "DealHunter/3.0"
                }
            )

            data = urlopen(
                request,
                timeout=20
            ).read()

            feed = feedparser.parse(data)

            for entry in feed.entries:

                title = html.unescape(
                    entry.get("title", "")
                )

                link = entry.get("link", "")

                summary = html.unescape(
                    entry.get("summary", "")
                )

                if not title or not link:
                    continue

                # Vérification des doublons
                if link in seen:
                    continue

                # Classification
                category = classify(title, summary)

                if category is None:
                    continue

                seen.add(link)

                if category not in results:
                    results[category] = []

                results[category].append({
                    "title": title,
                    "link": link,
                    "source": source
                })

        except Exception as error:

            print(f"Erreur : {error}")

    # ======================================
    # AFFICHAGE DES RESULTATS
    # ======================================

    print("\n\n" + "=" * 55)
    print("                OFFRES DETECTEES")
    print("=" * 55)

    if not results:

        print("\nAucune offre pertinente trouvee.")

    for category, offers in results.items():

        print(f"\n\n######## {category} ########")

        for offer in offers:

            print(f"\nSource : {offer['source']}")
            print(f"Produit : {offer['title']}")
            print(f"Lien : {offer['link']}")

    # ======================================
    # BILAN
    # ======================================

    total = sum(
        len(offers)
        for offers in results.values()
    )

    print("\n\n" + "=" * 55)
    print(f"TOTAL : {total} offres")
    print("=" * 55)

    print("\nRecherche terminee.")


if __name__ == "__main__":
    main()
