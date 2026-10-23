import re
import webbrowser

import httpx
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Tree
from textual.widgets.tree import TreeNode

from wikitui.client import WikiClient
from wikitui.config import CONFIG_PATH, load_config

WELCOME = "# wikitui\n\nPick a page from the tree on the left, or press `/` to search."
PAGE_LINK = re.compile(r"/books/(?P<book>[^/]+)/page/(?P<page>[^/?#]+)")


class WikiTUI(App):
    TITLE = "wiki"
    CSS = """
    #sidebar { width: 40; border-right: solid $primary; }
    #sidebar.hidden { display: none; }
    #search { margin: 0 1; }
    #viewer { padding: 0 2; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "search", "Search"),
        Binding("b", "toggle_sidebar", "Sidebar"),
        Binding("left", "step(-1)", "Prev page", priority=True),
        Binding("right", "step(1)", "Next page", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_browser", "Open in browser"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.client = WikiClient(self.config)
        self.current_page: dict | None = None
        self.current_node: TreeNode | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with VerticalScroll(id="sidebar"):
                yield Input(placeholder="Search (/)", id="search")
                yield Tree("Books", id="tree")
            with VerticalScroll(id="viewer"):
                yield Markdown(WELCOME, id="md")
        yield Footer()

    async def on_mount(self) -> None:
        self.sub_title = self.config.url
        tree = self.query_one("#tree", Tree)
        tree.root.expand()
        tree.focus()
        self.load_books()

    async def on_unmount(self) -> None:
        await self.client.aclose()

    # -- data loading ---------------------------------------------------

    def _show_error(self, exc: Exception) -> None:
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403):
            hint = (
                f"Not authorised. Set `WIKI_TOKEN_ID` / `WIKI_TOKEN_SECRET`, or create "
                f"`{CONFIG_PATH}` with `token_id` and `token_secret` "
                f"(BookStack: *Edit Profile → API Tokens*)."
            )
        else:
            hint = f"`{exc!r}`"
        self.query_one("#md", Markdown).update(f"# Error\n\n{hint}")

    @work(exclusive=True, group="books")
    async def load_books(self) -> None:
        tree = self.query_one("#tree", Tree)
        try:
            books = await self.client.books()
        except Exception as exc:
            self._show_error(exc)
            return
        for node in [n for n in tree.root.children if n.data and n.data[0] != "search"]:
            node.remove()
        for b in books:
            tree.root.add(f"📚 {b['name']}", data=("book", b["id"]), allow_expand=True)

    @work(group="expand")
    async def load_book_contents(self, node: TreeNode) -> None:
        try:
            book = await self.client.book(node.data[1])
        except Exception as exc:
            self._show_error(exc)
            return
        node.remove_children()
        for item in book["contents"]:
            if item["type"] == "chapter":
                chapter = node.add(f"📁 {item['name']}", data=("chapter", item["id"]))
                for p in item.get("pages", []):
                    chapter.add_leaf(f"📄 {p['name']}", data=("page", p["id"], p))
            else:
                node.add_leaf(f"📄 {item['name']}", data=("page", item["id"], item))
        node.data = ("book", node.data[1], True)

    @work(exclusive=True, group="page")
    async def open_page(self, page_id: int, summary: dict | None = None) -> None:
        md = self.query_one("#md", Markdown)
        try:
            title, text = await self.client.page_markdown(page_id)
        except Exception as exc:
            self._show_error(exc)
            return
        self.current_page = summary or {"id": page_id}
        self.sub_title = title
        await md.update(f"# {title}\n\n{text}" if not text.lstrip().startswith("# ") else text)
        self.query_one("#viewer").scroll_home(animate=False)

    @work(exclusive=True, group="search")
    async def run_search(self, query: str) -> None:
        tree = self.query_one("#tree", Tree)
        for node in [n for n in tree.root.children if n.data and n.data[0] == "search"]:
            node.remove()
        if not query.strip():
            return
        try:
            results = await self.client.search(query)
        except Exception as exc:
            self._show_error(exc)
            return
        node = tree.root.add(f"🔎 {query} ({len(results)})", data=("search",), expand=True)
        for r in results:
            if r["type"] == "page":
                node.add_leaf(f"📄 {r['name']}", data=("page", r["id"], r))
            else:
                node.add_leaf(f"[{r['type']}] {r['name']}", data=("other",))
        tree.move_cursor(node)

    # -- events ---------------------------------------------------------

    @on(Tree.NodeExpanded)
    def _expanded(self, event: Tree.NodeExpanded) -> None:
        data = event.node.data
        if data and data[0] == "book" and len(data) == 2:
            self.load_book_contents(event.node)

    @on(Tree.NodeSelected)
    def _selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if data and data[0] == "page":
            self.current_node = event.node
            self.open_page(data[1], data[2])
            self.query_one("#viewer").focus()

    @on(Input.Submitted, "#search")
    def _search_submitted(self, event: Input.Submitted) -> None:
        self.run_search(event.value)
        self.query_one("#tree").focus()

    @on(Markdown.LinkClicked)
    def _link(self, event: Markdown.LinkClicked) -> None:
        event.prevent_default()
        href = event.href
        m = PAGE_LINK.search(href)
        if m and (href.startswith("/") or href.startswith(self.config.url)):
            self.open_internal(m["book"], m["page"])
        elif href.startswith("/"):
            webbrowser.open(self.config.url + href)
        elif href.startswith(("http://", "https://")):
            webbrowser.open(href)

    @work(exclusive=True, group="page")
    async def open_internal(self, book_slug: str, page_slug: str) -> None:
        try:
            page = await self.client.page_by_slug(book_slug, page_slug)
        except Exception as exc:
            self._show_error(exc)
            return
        if page:
            self.open_page(page["id"], page)

    # -- actions --------------------------------------------------------

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        # Leave left/right to the search box's cursor while it has focus.
        if action == "step" and isinstance(self.focused, Input):
            return False
        return True

    def action_step(self, delta: int) -> None:
        """Open the previous/next page within the current book (or search results)."""
        node = self.current_node
        if node is None or node.tree is None:
            return
        scope = node
        while scope.parent is not None and scope.parent.parent is not None:
            scope = scope.parent
        pages: list[TreeNode] = []

        def walk(n: TreeNode) -> None:
            for child in n.children:
                if child.data and child.data[0] == "page":
                    pages.append(child)
                walk(child)

        walk(scope)
        if node not in pages:
            return
        target = pages.index(node) + delta
        if not 0 <= target < len(pages):
            return
        new = pages[target]
        ancestor = new.parent
        while ancestor is not None:
            ancestor.expand()
            ancestor = ancestor.parent
        self.current_node = new
        tree = self.query_one("#tree", Tree)
        tree.move_cursor(new)
        self.open_page(new.data[1], new.data[2])

    def action_search(self) -> None:
        self.query_one("#sidebar").remove_class("hidden")
        self.query_one("#search", Input).focus()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.toggle_class("hidden")
        if sidebar.has_class("hidden"):
            self.query_one("#viewer").focus()
        else:
            self.query_one("#tree", Tree).focus()

    def action_refresh(self) -> None:
        self.load_books()

    def action_open_browser(self) -> None:
        if self.current_page:
            webbrowser.open(self.client.page_url(self.current_page))


def main() -> None:
    WikiTUI().run()
