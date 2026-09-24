"""Verify static documentation links, images and local anchors before deployment."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / "site"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if fields.get("id"):
            self.ids.add(fields["id"])
        for key in ("href", "src"):
            if fields.get(key):
                self.links.append(fields[key])


pages = {}
for path in ROOT.rglob("*.html"):
    parser = Page()
    parser.feed(path.read_text(encoding="utf-8"))
    pages[path.resolve()] = parser
if not pages:
    raise SystemExit("No built documentation pages found")
errors = []
for path, page in pages.items():
    for link in page.links:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        destination = (path.parent / unquote(url.path)).resolve() if url.path else path
        if not destination.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing {link}")
        elif (
            url.fragment
            and destination in pages
            and unquote(url.fragment) not in pages[destination].ids
        ):
            errors.append(f"{path.relative_to(ROOT)}: missing anchor {link}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Checked {len(pages)} documentation pages: links, images and anchors passed.")
