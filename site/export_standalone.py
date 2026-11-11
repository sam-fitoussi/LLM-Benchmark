"""Copy the explorer to the personal site as a standalone page (samuelfitoussi.com/nuclear-button/).

The artifact version (site/index.html) has no <head>: claude.ai wraps it. This adds one (charset, canonical link,
share tags), a link back to the article, and copies the data files.

python site/export_standalone.py ../samuelfitoussi.com/public/nuclear-button
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
dest = sys.argv[1]
URL = "https://samuelfitoussi.com/nuclear-button/"
ARTICLE = "/posts/nuclear-button-benchmark"
DESC = ("Every prompt, answer and internal reasoning behind “I gave the nuclear button to five AIs”: four situations, "
        "five models, all tables recomputed from the raw data.")

src = open(os.path.join(HERE, "index.html")).read()
head, body = src.split("</style>", 1)
head = re.sub(r"<title>.*?</title>\n", "", head)
head = re.sub(r'<meta name="claude:viewport-fit-sides"[^>]*>\n', "", head)
top = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Nuclear Button: all the data · Samuel Fitoussi</title>
<meta name="description" content="{DESC}">
<meta name="author" content="Samuel Fitoussi">
<link rel="canonical" href="{URL}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:title" content="The Nuclear Button: all the data">
<meta property="og:description" content="{DESC}">
<meta property="og:type" content="website">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="https://samuelfitoussi.com/og-default.png">
<meta property="og:site_name" content="Samuel Fitoussi">
<meta name="twitter:card" content="summary_large_image">
"""
sub = '<p class="brand-sub">All the data behind the experiment</p>'
assert sub in body
body = body.replace(sub, sub + f'\n    <p class="brand-sub"><a href="{ARTICLE}">← Read the article</a></p>', 1)
os.makedirs(os.path.join(dest, "data"), exist_ok=True)
open(os.path.join(dest, "index.html"), "w").write(top + head + "</style>\n</head>\n<body>" + body.rstrip() + "\n</body>\n</html>\n")
for f in os.listdir(os.path.join(HERE, "data")):
    shutil.copy(os.path.join(HERE, "data", f), os.path.join(dest, "data", f))
print("wrote", dest)
