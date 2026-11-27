
import feedparser
import html
import json
import os
import re
import smtplib
import unicodedata
import ssl

from email.message import EmailMessage
from pathlib import Path
from urllib.request import Request, urlopen

# ==========================================
# CONFIGURATION
# ==========================================

FEEDS = {
    "Dealabs Informatique": "https://www.dealabs.com/rss/groupe/informatique",
    "Les Numeriques": "https://www.lesnumeriques.com/rss-gooddeals.xml",
}

STATE_FILE = Path("seen_links.json")

# ==========================================
# 13 CATEGORIES RECHERCHEES
# ==========================================

CATEGORIES = {
    "GPU": [
        "carte graphique", "geforce", "radeon", "rtx", "rx "
    ],
    "CPU": [
        "processeur", "ryzen", "intel core", "core i5",
        "core i7", "core i9", "core ultra"
    ],
    "RAM": ["ram", "ddr4", "ddr5", "memoire vive"],
    "SSD": ["ssd", "nvme"],
    "CARTE MERE": [
        "carte mere", "motherboard", "b650",
        "x670", "x870", "z790", "z890"
    ],
    "ALIMENTATION": [
        "alimentation pc", "bloc alimentation",
        "power supply", "80 plus gold", "80 plus platinum"
    ],
    "BOITIER": ["boitier pc", "boitier gaming"],
    "REFROIDISSEMENT": [
        "ventirad", "watercooling", "aio",
        "refroidissement liquide", "radiateur cpu"
    ],
    "VENTILATEUR": [
        "ventilateur pc", "ventilateur boitier"
    ],
    "ECRAN": [
        "ecran", "moniteur", "monitor", "oled",
        "qd-oled", "mini-led", "amoled", "ips",
        "144hz", "165hz", "180hz", "240hz",
        "360hz", "ultrawide"
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
    ],
}

# ==========================================
# NORMALISATION
# ==========================================

def normalize(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = unicodedata.normalize("NFD", text.lower())

    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_keyword(text, keyword):
    text = normalize(text)
    keyword = normalize(keyword)

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(keyword)
        + r"(?![a-z0-9])"
    )

    return re.search(pattern, text) is not None


# ==========================================
# EXCLUSION DES PC COMPLETS ET PORTABLES
# ==========================================

def is_prebuilt(title, summary):
    title = normalize(title)
    summary = normalize(summary)

    if re.match(r"^pc\b", title):
        return True

    excluded_patterns = [
        r"\bpc portable\b",
        r"\bordinateur portable\b",
        r"\blaptop\b",
        r"\bnotebook\b",
        r"\bchromebook\b",
        r"\btablette\b",
        r"\bipad\b",
        r"\bgalaxy tab\b",
        r"\bpc gamer\b",
        r"\bpc gaming\b",
        r"\bordinateur gamer\b",
        r"\bordinateur gaming\b",
        r"\btour gaming\b",
        r"\btour gamer\b",
        r"\bpc fixe\b",
        r"\bpc complet\b",
        r"\bordinateur complet\b",
        r"\bordinateur de bureau\b",
        r"\bpc preassemble\b",
        r"\bpc pre monte\b",
        r"\bpc assemble\b",
        r"\bunite centrale\b",
        r"\bdesktop gaming\b",
        r"\bconfiguration gaming\b",
        r"\bconfiguration gamer\b",
        r"\bmini pc\b",
        r"\bbarebone\b",
        r"\ball in one\b",
        r"\btout en un\b",
    ]

    if any(
        re.search(pattern, title)
        for pattern in excluded_patterns
    ):
        return True

    summary_exclusions = [
        "pc preassemble",
        "pc pre monte",
        "pc complet",
        "tour gaming",
        "tour gamer",
        "configuration gaming",
        "configuration gamer",
        "ordinateur gaming",
        "ordinateur gamer",
        "unite centrale",
    ]

    if any(
        contains_keyword(summary, word)
        for word in summary_exclusions
    ):
        return True

    # Plusieurs composants réunis peuvent indiquer un PC complet.
    cpu_words = [
        "ryzen", "intel core", "core i5",
        "core i7", "core i9", "core ultra"
    ]

    gpu_words = ["geforce", "radeon", "rtx", "rx "]

    has_cpu = any(
        contains_keyword(title, word)
        for word in cpu_words
    )

    has_gpu = any(
        contains_keyword(title, word)
        for word in gpu_words
    )

    has_ram = any(
        contains_keyword(title, word)
        for word in ["ddr4", "ddr5", "ram"]
    )

    has_storage = any(
        contains_keyword(title, word)
        for word in ["ssd", "nvme"]
    )

    return has_cpu and has_gpu and has_ram and has_storage


# ==========================================
# CLASSIFICATION
# ==========================================

def classify(title, summary):
    title = normalize(title)

    if is_prebuilt(title, summary):
        return None

    for category, keywords in CATEGORIES.items():

        if category == "ECRAN":
            identifiers = [
                "ecran", "moniteur", "monitor", "display"
            ]

            if not any(
                contains_keyword(title, word)
                for word in identifiers
            ):
                continue

        for keyword in keywords:

            if not contains_keyword(title, keyword):
                continue

            if normalize(keyword) in ["rtx", "rx"]:
                identifiers = [
                    "carte graphique", "geforce", "radeon"
                ]

                if not any(
                    contains_keyword(title, word)
                    for word in identifiers
                ):
                    continue

            return category

    return None


# ==========================================
# HISTORIQUE DES DOUBLONS
# ==========================================

def load_seen_links():
    if not STATE_FILE.exists():
        return set()

    try:
        data = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )

        return set(data) if isinstance(data, list) else set()

    except (OSError, json.JSONDecodeError):
        print("Attention : historique illisible.")
        return set()


def save_seen_links(seen_links):
    STATE_FILE.write_text(
        json.dumps(
            sorted(seen_links),
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# ==========================================
# ENVOI GMAIL
# ==========================================


def send_email(Titre, lien, Categorie, Source):

    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        raise RuntimeError("Identifiants Gmail manquants.")

    gmail_password = gmail_password.replace(" ", "")

    message = EmailMessage()
    message["From"] = gmail_address
    message["To"] = gmail_address
    message["Subject"] = f"DEALHUNTER - Nouvelle offre : {Categorie}"

    message.set_content(
        f"Nouvelle promotion détectée !\n\n"
        f"Produit : {Titre}\n"
        f"Catégorie : {Categorie}\n"
        f"Source : {Source}\n"
        f"Lien : {lien}\n"
    )

    etape = "Connexion au serveur"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as serveur:

            etape = "Identification EHLO"
            serveur.ehlo()

            etape = "Activation TLS"
            serveur.starttls(context=ssl.create_default_context())
            serveur.ehlo()

            etape = "Authentification Gmail"
            serveur.login(gmail_address, gmail_password)

            etape = "Envoi du message"
            serveur.send_message(message)

        print("EMAIL ENVOYE AVEC SUCCES")

    except Exception as erreur:
        raise RuntimeError(
            f"Echec à l'étape : {etape} | "
            f"{type(erreur).__name__} : {erreur}"
        ) from erreur



# ==========================================
# PROGRAMME PRINCIPAL
# ==========================================

def main():

    print("=" * 55)
    print("                 DEALHUNTER")
    print("       COMPOSANTS PC ET PERIPHERIQUES")
    print("=" * 55)

    seen_links = load_seen_links()
    new_count = 0

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
                timeout=30
            ).read()

            feed = feedparser.parse(data)

            if feed.bozo and not feed.entries:
                print("Flux RSS illisible.")
                continue

            for entry in feed.entries:

                title = html.unescape(
                    entry.get("title", "")
                ).strip()

                link = entry.get("link", "").strip()

                summary = html.unescape(
                    entry.get("summary", "")
                )

                if not title or not link:
                    continue

                if link in seen_links:
                    continue

                category = classify(title, summary)

                if category is None:
                    continue

                print(f"\nNouvelle offre : {title}")
                print(f"Categorie : {category}")
                print(f"Source : {source}")

                try:

                    send_email(
                        title,
                        link,
                        category,
                        source
                    )

                except Exception as error:

                    print(
                        f"Erreur Gmail : {error}"
                    )

                    continue

                # Historique uniquement après envoi réussi.
                seen_links.add(link)
                save_seen_links(seen_links)

                new_count += 1

                print("E-mail envoyé avec succès !")

        except Exception as error:

            print(
                f"Erreur pour {source} : {error}"
            )

    print("\n" + "=" * 55)
    print(
        f"TOTAL : {new_count} nouvelles offres envoyées"
    )
    print("=" * 55)

    print("\nRecherche terminée.")


if __name__ == "__main__":
    main()
