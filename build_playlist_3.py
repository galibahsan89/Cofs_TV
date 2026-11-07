import re, base64
from urllib.parse import urljoin, urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

SITE = "http://172.19.178.180/"
SUFFIX = "/index.fmp4.m3u8"
OUT_FILE = "playlist_3.m3u"

def get_stream(ch):
    try:
        html = requests.get(ch["page"], timeout=30).text
        m = re.search(r'encodedUrl\s*=\s*"([A-Za-z0-9+/=]+)"', html)
        if not m:
            return None
        u = urlparse(base64.b64decode(m.group(1)).decode())
        stream = re.sub(r"/embed\.html$", "", u.path)
        token = parse_qs(u.query).get("token", [""])[0]
        ch["url"] = f"{u.scheme}://{u.netloc}{stream}{SUFFIX}" + (f"?token={token}" if token else "")
        return ch
    except Exception as e:
        print("failed:", ch["page"], e)
        return None

html = requests.get(SITE + "index.php", timeout=30).text
soup = BeautifulSoup(html, "html.parser")
seen, channels = set(), []
for a in soup.select("a[href*='play.php']"):
    page = urljoin(SITE, a["href"])
    cid = parse_qs(urlparse(page).query).get("id", [""])[0]
    if cid in seen:
        continue
    seen.add(cid)
    img = a.find("img")
    name = " ".join(a.get_text(" ").split()) or (img.get("alt") if img else "") or f"Channel {cid}"
    parent = a.find_parent(id=True)
    channels.append({
        "id": cid, "page": page, "name": name,
        "logo": urljoin(SITE, img["src"]) if img and img.get("src") else "",
        "group": parent["id"] if parent else "Other",
    })

with ThreadPoolExecutor(5) as ex:
    results = [r for r in ex.map(get_stream, channels) if r]

if not results:
    raise SystemExit("No streams found - keeping the old playlist.")

lines = ["#EXTM3U"]
for c in results:
    name = re.sub(r"\s+", " ", re.sub(r"[,.]", " ", c["name"])).strip()
    lines.append(f'#EXTINF:-1 tvg-id="{c["id"]}" tvg-name="{name}" tvg-logo="{c["logo"]}" group-title="{c["group"]}",{name}')
    lines.append(c["url"])

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote {len(results)}/{len(channels)} channels")
