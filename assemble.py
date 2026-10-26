"""Put the data into the page template.

Usage:
  assemble.py TEMPLATE.html USAGE.json SCHEMES.json OUT.html              (page body only)
  assemble.py TEMPLATE.html USAGE.json SCHEMES.json OUT.html --standalone (full web page for GitHub Pages)
"""
import sys

tpl, usage, schemes, out = sys.argv[1:5]
standalone = "--standalone" in sys.argv[5:]

t = open(tpl, encoding="utf-8").read()
for ph in ("/*DATA*/null", "/*SCHEMES*/null"):
    assert t.count(ph) == 1, f"placeholder {ph} missing or repeated"
t = (t.replace("/*DATA*/null", open(usage, encoding="utf-8").read())
      .replace("/*SCHEMES*/null", open(schemes, encoding="utf-8").read()))

if standalone:
    # Split the template into its <head> part (title, fonts, styles) and the visible page.
    cut = t.index('<div class="band">')
    head, body = t[:cut], t[cut:]
    icon = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
            "%3Crect width='64' height='64' rx='14' fill='%231d3fd8'/%3E"
            "%3Ctext x='32' y='44' font-family='Arial' font-weight='700' font-size='34' fill='white' text-anchor='middle'%3EF%3C/text%3E"
            "%3Ccircle cx='50' cy='44' r='5' fill='%23ff7a1a'/%3E%3C/svg%3E")
    t = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="FPF Fantasy: NFL usage trends, weekly start/sit rankings and offensive scheme profiles. Fantasy Points First.">
<link rel="icon" href="{icon}">
<style>
:root{{color-scheme:dark;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
body{{margin:0;font:14px system-ui,-apple-system,"Segoe UI",sans-serif}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
{head}
</head>
<body>
{body}
</body>
</html>
"""

open(out, "w", encoding="utf-8").write(t)
print("wrote", out, len(t), "bytes", "(standalone)" if standalone else "")
