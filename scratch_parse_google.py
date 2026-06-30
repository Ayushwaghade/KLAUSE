import re
import urllib.parse

with open("google_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's try to extract result blocks.
# A result block typically looks like a div containing BNeawe or similar classes
# Or in desktop layout: class="g" (div class="g") or similar.
# Let's inspect class="g" or h3 elements first.
h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html)
print("Found h3 count:", len(h3s))
for h in h3s[:10]:
    clean_h = re.sub(r'<[^>]+>', '', h)
    print("- H3:", clean_h)

# Let's check for links in the HTML
links = re.findall(r'<a href="/url\?q=(https?://[^&]+)', html)
print("Found /url?q= links:", len(links))
for l in links[:5]:
    print("- Link:", urllib.parse.unquote(l))

# Let's combine them. Google's mobile/standard simple layout has blocks of:
# <div class="ZINbbc xpd ONSPIc ...">
# Inside this we have the title in <div class="BNeawe vvjwbr ...">TITLE</div>
# And link in <a href="/url?q=LINK...">
# And snippet in <div class="BNeawe s3v9rd ...">SNIPPET</div>
blocks = re.split(r'<div class="ZINbbc[^"]*"', html)
print("Found ZINbbc blocks:", len(blocks))
parsed = []
for b in blocks[1:]:
    # Find title
    t_match = re.search(r'<div class="BNeawe vvjwbr[^>]*>(.*?)</div>', b, re.DOTALL)
    l_match = re.search(r'<a href="/url\?q=(https?://[^&]+)', b)
    s_match = re.search(r'<div class="BNeawe s3v9rd[^>]*>(.*?)</div>', b, re.DOTALL)
    
    if t_match and l_match:
        title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()
        link = urllib.parse.unquote(l_match.group(1))
        snippet = ""
        if s_match:
            # Clean inner spans / details
            snippet = re.sub(r'<[^>]+>', '', s_match.group(1)).strip()
            # If the snippet starts with the link or weather card, we clean it
            snippet = re.sub(r'\s+', ' ', snippet)
        parsed.append((title, link, snippet))

print("Parsed results count:", len(parsed))
for p in parsed[:5]:
    print(f"\nTitle: {p[0]}\nLink: {p[1]}\nSnippet: {p[2]}")
