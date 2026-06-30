with open("google_raw.html", "r", encoding="utf-8") as f:
    html = f.read()

print("HTML Start:")
print(html[:1000])

# Find some links
import re
links = re.findall(r'href="([^"]+)"', html)
print("\nLinks count:", len(links))
for l in links[:15]:
    print("-", l)
