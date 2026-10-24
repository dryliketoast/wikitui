"""Fake BookStack REST API on 127.0.0.1:16875 for rendering docs/demo.gif.

Serves a small made-up handbook: /api/books, /api/books/{id}, /api/pages, /api/pages/{id}
and /api/search.  Requires `Authorization: Token demo:demo`, like the real thing.
"""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = 16875

# (book id, slug, name), then chapters/pages
BOOKS = [
    (1, "engineering-handbook", "Engineering Handbook"),
    (2, "team-wiki", "Team Wiki"),
    (3, "runbooks", "Runbooks"),
]

# page id: (book id, chapter name or None, slug, title, markdown)
PAGES = {
    11: (1, "Getting Started", "onboarding-checklist", "Onboarding checklist", """\
Welcome aboard! Work through this list in your first week.

## Day one

- [ ] Get your laptop and set up disk encryption
- [ ] Join the `#engineering` channel
- [ ] Read the [architecture overview](/books/engineering-handbook/page/architecture-overview)
- [ ] Pair with your onboarding buddy

## First week

1. Clone the main repositories
2. Run the test suite locally
3. Ship a small change through the [deploy process](/books/engineering-handbook/page/deploy-process)

> **Tip:** ask questions early. Nobody expects you to know everything yet.
"""),
    12: (1, "Getting Started", "dev-environment", "Dev environment", """\
We use `uv` for Python and `mise` for everything else.

```bash
git clone git@git.example.com:platform/api.git
cd api
uv sync
uv run pytest -q
```

| Tool    | Version | Install            |
|---------|---------|--------------------|
| Python  | 3.13    | `uv python install`|
| Node    | 22 LTS  | `mise use node@22` |
| Postgres| 16      | `docker compose up`|

Run the app with `uv run flask --app api run --debug`.
"""),
    13: (1, "Operations", "deploy-process", "Deploy process", """\
Every merge to `main` is deployed automatically, once CI is green.

## Pipeline

1. **Build** the container image
2. **Test** unit and integration suites
3. **Stage** deploy and smoke tests
4. **Production** rolling deploy, 10% at a time

## Rolling back

```bash
deployctl rollback --service api --to previous
```

If a deploy looks wrong, roll back first and investigate afterwards. See
[incident response](/books/engineering-handbook/page/incident-response).
"""),
    14: (1, "Operations", "incident-response", "Incident response", """\
## Severity levels

| Level | Meaning                      | Response time |
|-------|------------------------------|---------------|
| SEV1  | Customer-facing outage       | 5 minutes     |
| SEV2  | Degraded service             | 30 minutes    |
| SEV3  | Minor issue, workaround known| Next day      |

## First steps

1. Declare the incident in `#incidents`
2. Assign an **incident lead**
3. Post updates every 15 minutes
4. Write the post-mortem within 3 days
"""),
    15: (1, None, "architecture-overview", "Architecture overview", """\
The platform is a handful of small services behind a single gateway.

- **gateway**: terminates TLS, routes requests
- **api**: the main Flask application
- **worker**: background jobs from the queue
- **postgres**: primary datastore

```
client -> gateway -> api -> postgres
                      \\-> queue -> worker
```
"""),
    21: (2, None, "meeting-notes", "Meeting notes", """\
## Weekly sync

- Release 2.4 is on track for Thursday
- Two new starters join next Monday
- Retro action: add a deploy checklist

## Decisions

| Topic          | Decision          | Owner |
|----------------|-------------------|-------|
| Logging        | Adopt JSON logs   | Sam   |
| On-call rota   | Rotate weekly     | Priya |
"""),
    22: (2, None, "holiday-calendar", "Holiday calendar", """\
Remember to book leave early over the summer.

- Spring bank holiday: office closed
- Summer shutdown: first two weeks of August
- Winter break: 24 December to 1 January
"""),
    31: (3, None, "restore-from-backup", "Restore from backup", """\
Backups run nightly and are kept for 30 days.

```bash
backupctl list --service postgres
backupctl restore --service postgres --snapshot latest
```

Always restore into a **scratch** instance first and check the data before
promoting it.
"""),
}


def page_summary(pid):
    book, chapter, slug, title, _ = PAGES[pid]
    bslug = next(b[1] for b in BOOKS if b[0] == book)
    return {"id": pid, "book_id": book, "name": title, "slug": slug, "book_slug": bslug}


def book_contents(bid):
    chapters, pages = {}, []
    for pid, (b, chapter, *_rest) in PAGES.items():
        if b != bid:
            continue
        if chapter is None:
            pages.append({"type": "page", **page_summary(pid)})
        else:
            ch = chapters.setdefault(chapter, {"type": "chapter", "id": 100 + bid * 10 + len(chapters), "name": chapter, "pages": []})
            ch["pages"].append(page_summary(pid))
    return [*chapters.values(), *pages]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Authorization") != "Token demo:demo":
            return self.send_json(401, {"error": {"message": "No authorization token found on the request", "code": 401}})
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        path = url.path
        if path == "/api/books":
            data = [{"id": i, "name": n, "slug": s} for i, s, n in sorted(BOOKS, key=lambda b: b[2])]
            return self.send_json(200, {"data": data, "total": len(data)})
        if m := re.fullmatch(r"/api/books/(\d+)", path):
            bid = int(m[1])
            book = next(((i, s, n) for i, s, n in BOOKS if i == bid), None)
            if not book:
                return self.send_json(404, {"error": {"message": "Not found", "code": 404}})
            return self.send_json(200, {"id": bid, "name": book[2], "slug": book[1], "contents": book_contents(bid)})
        if m := re.fullmatch(r"/api/pages/(\d+)", path):
            pid = int(m[1])
            if pid not in PAGES:
                return self.send_json(404, {"error": {"message": "Not found", "code": 404}})
            return self.send_json(200, {**page_summary(pid), "markdown": PAGES[pid][4], "html": ""})
        if path == "/api/pages":
            slug = q.get("filter[slug]")
            data = [page_summary(p) for p in PAGES if not slug or PAGES[p][2] == slug]
            return self.send_json(200, {"data": data, "total": len(data)})
        if path == "/api/search":
            term = q.get("query", "").lower()
            data = [{"type": "page", **page_summary(p)} for p, v in PAGES.items() if term in v[3].lower() or term in v[4].lower()]
            data += [{"type": "chapter", "id": 0, "name": c["name"]} for b in BOOKS for c in book_contents(b[0]) if c["type"] == "chapter" and term in c["name"].lower()]
            return self.send_json(200, {"data": data, "total": len(data)})
        self.send_json(404, {"error": {"message": "Not found", "code": 404}})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
