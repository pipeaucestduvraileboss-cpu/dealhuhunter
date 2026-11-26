
import feedparser
import re
from urllib.request import Request, urlopen

FEEDS = {
    "Dealabs Informatique": "https://www.dealabs.com/rss/groupe/informatique",
    "Les Numeriques": "https://www.lesnumeriques.com/rss-gooddeals.xml",
}

KEYWORDS = [
    "carte graphique", "geforce", "radeon", "rtx", "rx ",
    "processeur", "ryzen", "intel core", "cpu",
    "ram", "ddr4", "ddr5", "ssd", "nvme",
    "carte mere", "carte mère", "alimentation",
    "boitier pc", "boîtier pc"
]

def clean(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def is_relevant(text):
    text = text.lower()
    return any(word in text for word in KEYWORDS)

def main():
    print("=== DEALHUNTER ===")
    print("Recherche des offres informatiques...\n")

    seen = set()

    for source, url in FEEDS.items():
        print(f"Source : {source}")

        try:
            request = Request(
                url,
                headers={"User-Agent": "DealHunter/1.0"}
            )
            data = urlopen(request, timeout=15).read()
            feed = feedparser.parse(data)

            for entry in feed.entries:
                title = clean(entry.get("title", ""))
                link = entry.get("link", "")
                summary = clean(entry.get("summary", ""))

                if not is_relevant(title + " " + summary):
                    continue

                if link in seen:
                    continue

                seen.add(link)

                print(f"\n{title}")
                print(link)

        except Exception as error:
            print(f"Erreur sur cette source : {error}")

    print("\nRecherche terminée.")

if __name__ == "__main__":
    main()
