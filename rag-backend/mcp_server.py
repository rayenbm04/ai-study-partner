#!/usr/bin/env python3
"""
mcp_server.py — MCP server for the RAG Assistant.

Exposes nine tools to any MCP-compatible client (Claude Desktop, etc.):
  • list_documents           — see what files are indexed
  • query_documents          — ask a question against indexed files
  • upload_document          — index a new file from a local path
  • list_github_repos        — list repos for any GitHub user/org (REST API)
  • get_github_profile       — full profile summary: bio, languages, top repos (recruiter-ready)
  • index_github_repo        — auto-fetch & index key files from a repo for deep Q&A
  • upload_document_from_url — download from a URL and index (ideal for GitHub/Notion)
  • upload_document_content  — index from base64 content (for direct file attachments)
  • check_indexing_status    — poll indexing progress for a previously uploaded file

All upload tools return immediately — indexing runs in the background.
Call check_indexing_status(filename) to know when a file is ready to query.

Setup
-----
1.  pip install fastmcp requests python-dotenv

2.  Add credentials to rag-backend/.env:
        MCP_EMAIL=your@email.com
        MCP_PASSWORD=yourpassword
        MCP_BASE_URL=http://localhost:8000   # or your deployed URL

3.  Add to Claude Desktop config
    (%APPDATA%\\Claude\\claude_desktop_config.json on Windows):
        {
          "mcpServers": {
            "rag-assistant": {
              "command": "python",
              "args": ["D:/PROJECTS/rag-assistant/rag-backend/mcp_server.py"]
            }
          }
        }

4.  Restart Claude Desktop.
"""

import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

BASE_URL      = os.getenv("MCP_BASE_URL",  "http://localhost:8000")
EMAIL         = os.getenv("MCP_EMAIL",     "")
GITHUB_TOKEN  = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
PASSWORD     = os.getenv("MCP_PASSWORD",  "")
SSE_TIMEOUT  = 180   # seconds to wait for /ask to finish streaming

if not EMAIL or not PASSWORD:
    print(
        "[mcp_server] ERROR: MCP_EMAIL and MCP_PASSWORD must be set in .env",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Auth ──────────────────────────────────────────────────────────────────────

_token: str = ""
_token_ts: float = 0.0
TOKEN_TTL = 6 * 24 * 3600   # refresh after 6 days (JWT expires in 7)


def _get_token() -> str:
    """Return a valid JWT, refreshing if it is about to expire."""
    global _token, _token_ts
    if _token and (time.time() - _token_ts) < TOKEN_TTL:
        return _token
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login failed ({r.status_code}): {r.text[:200]}")
    _token    = r.json()["access_token"]
    _token_ts = time.time()
    return _token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


# ── MCP server ────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "RAG Assistant",
    instructions=(
        # Document Q&A
        "To answer questions about indexed documents: call list_documents first, "
        "then query_documents with the relevant file names. "
        "Always pass the most specific file list you can — querying all files at once reduces precision.\n\n"

        # GitHub — ALWAYS use these tools, never search_repositories
        "For ANY GitHub user or organisation lookup — listing repos, checking a profile, "
        "extracting skills, giving career advice — ALWAYS use this server's tools:\n"
        "  • get_github_profile(username)  — bio, languages, top repos in one call. "
        "Use this first for any recruiter or profile analysis request.\n"
        "  • list_github_repos(username)   — simple repo list. Use when only names are needed.\n"
        "  • index_github_repo(username, repo_name) — indexes repo files for deep Q&A.\n"
        "NEVER use the GitHub connector's search_repositories for user-specific lookups — "
        "it fails on usernames with hyphens and returns incomplete results. "
        "Use get_github_profile or list_github_repos instead, always.\n\n"

        # Upload flow
        "To index a file from a URL (e.g. a raw GitHub file): call upload_document_from_url, "
        "then poll check_indexing_status every 30 s until status is ready."
    ),
)


# ── Tool 1: list_documents ────────────────────────────────────────────────────

@mcp.tool()
def list_documents() -> str:
    """
    List all documents currently indexed in the RAG assistant and ready to query.
    Returns a plain-text list of file names, one per line.
    Call this before query_documents to know which files exist.
    """
    r = requests.get(f"{BASE_URL}/documents", headers=_headers(), timeout=15)
    if r.status_code != 200:
        return f"Error listing documents ({r.status_code}): {r.text[:200]}"

    docs = r.json()
    ready = [d["name"] for d in docs if d.get("status", "ready") == "ready"]
    if not ready:
        return "No documents are indexed yet. Upload files via the web UI first."
    return "\n".join(f"• {name}" for name in sorted(ready))


# ── Tool 2: query_documents ───────────────────────────────────────────────────

@mcp.tool()
def query_documents(
    question: str,
    files: list[str],
    provider: str = "local",
) -> str:
    """
    Ask a question about one or more indexed documents.

    Parameters
    ----------
    question : str
        The question to answer. Can be in French or English.
    files : list[str]
        File names to search (e.g. ["CCF04162026.pdf", "report.docx"]).
        Use list_documents() to see available names.
        Pass an empty list [] to search across all indexed documents.
    provider : str
        "local"  — use the local Ollama model (default, private, no API cost).
        "cloud"  — use Groq llama-3.3-70b (faster, higher quality, requires GROQ_API_KEY).

    Returns
    -------
    str
        The answer followed by the source files and page numbers cited.
    """
    # If no files specified, query across all indexed documents
    if not files:
        r = requests.get(f"{BASE_URL}/documents", headers=_headers(), timeout=15)
        if r.status_code == 200:
            files = [d["name"] for d in r.json() if d.get("status", "ready") == "ready"]
        if not files:
            return "No documents are indexed yet. Upload a file first."

    payload = {
        "question": question,
        "files":    files,
        "history":  [],
        "provider": provider,
        "fast":     False,   # full pipeline: HyDE + multi-query + rerank
    }

    answer_parts: list[str] = []
    sources:      list[str] = []
    citations:    list[dict] = []

    try:
        with requests.post(
            f"{BASE_URL}/ask",
            json=payload,
            headers={**_headers(), "Accept": "text/event-stream"},
            stream=True,
            timeout=SSE_TIMEOUT,
        ) as resp:
            if resp.status_code != 200:
                return f"Error from /ask ({resp.status_code}): {resp.text[:300]}"

            buffer = ""
            for raw in resp.iter_content(chunk_size=None, decode_unicode=True):
                buffer += raw
                while "\n\n" in buffer:
                    event_str, buffer = buffer.split("\n\n", 1)
                    for line in event_str.splitlines():
                        if not line.startswith("data:"):
                            continue
                        try:
                            data = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        t = data.get("type", "")
                        if t == "token":
                            answer_parts.append(data.get("content", ""))
                        elif t == "done":
                            sources   = data.get("sources",   [])
                            citations = data.get("citations", [])
                        elif t == "error":
                            return f"[RAG error] {data.get('message', '')}"

    except requests.Timeout:
        return "[timeout] The RAG assistant took too long to respond."
    except Exception as e:
        return f"[exception] {e}"

    answer = "".join(answer_parts).strip()
    if not answer:
        return "No answer was returned. The document may not be indexed yet."

    # Append source citations
    if citations:
        cite_lines = []
        for c in citations:
            pages = c.get("pages", [])
            if pages:
                cite_lines.append(f"  • {c['file']}  (pages {', '.join(str(p) for p in pages)})")
            else:
                cite_lines.append(f"  • {c['file']}")
        answer += "\n\nSources:\n" + "\n".join(cite_lines)
    elif sources:
        answer += "\n\nSources:\n" + "\n".join(f"  • {s}" for s in sources)

    return answer


# ── Shared upload helper ──────────────────────────────────────────────────────

def _post_file(name: str, content: bytes, provider: str) -> str:
    """
    POST file bytes to /upload and return immediately — do NOT poll.
    Returns the indexed filename on success, or raises RuntimeError on failure.
    """
    resp = requests.post(
        f"{BASE_URL}/upload",
        files={"file": (name, io.BytesIO(content))},
        data={"provider": provider},
        headers=_headers(),
        timeout=120,   # generous for large files; just the HTTP POST, not indexing
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Upload failed ({resp.status_code}): {resp.text[:200]}")
    return resp.json().get("name", name)


# ── Tool 3: upload_document ───────────────────────────────────────────────────

@mcp.tool()
def upload_document(file_path: str, provider: str = "local") -> str:
    """
    Upload and index a document from a local file path.

    Returns immediately once the file is accepted — indexing runs in the
    background. Call check_indexing_status(filename) to monitor progress.

    Parameters
    ----------
    file_path : str
        Absolute path to the file on disk
        (e.g. "C:/Users/rayen/Documents/report.pdf").
        Supported formats: PDF, DOCX, PPTX, XLSX, PNG, JPG, TXT, MD, CSV, PUML.
    provider : str
        "local" or "cloud" — which vision model to use for image/scanned PDF pages.
    """
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    if not path.is_file():
        return f"Not a file: {file_path}"

    with open(path, "rb") as fh:
        content = fh.read()

    try:
        indexed_name = _post_file(path.name, content, provider)
    except RuntimeError as e:
        return str(e)

    return (
        f"✓ '{indexed_name}' uploaded — indexing started in the background.\n"
        f"Call check_indexing_status('{indexed_name}') in ~30 s to see when it's ready."
    )


# ── Tool 4: list_github_repos ────────────────────────────────────────────────

@mcp.tool()
def list_github_repos(username: str, per_page: int = 30) -> str:
    """
    List repositories for a GitHub user or organisation via the REST API.

    PREFER THIS over search_repositories from the GitHub connector — search_repositories
    uses a keyword index that fails for users with few public repos or hyphenated names.
    This tool calls /users/{username}/repos directly and always works.

    Parameters
    ----------
    username : str
        GitHub username or organisation name (e.g. "rayen-ben-mimoun").
    per_page : int
        Number of repos to return (max 100). Default 30.
    """
    if not GITHUB_TOKEN:
        return "GITHUB_PERSONAL_ACCESS_TOKEN is not set in .env — cannot call GitHub API."

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    params = {"per_page": min(per_page, 100), "sort": "updated", "direction": "desc"}

    r = requests.get(
        f"https://api.github.com/users/{username}/repos",
        headers=headers,
        params=params,
        timeout=15,
    )
    if r.status_code == 404:
        return f"GitHub user '{username}' not found."
    if r.status_code != 200:
        return f"GitHub API error ({r.status_code}): {r.text[:200]}"

    repos = r.json()
    if not repos:
        return f"No repositories found for '{username}'."

    lines = [f"Repositories for {username} ({len(repos)} shown, sorted by last update):\n"]
    for repo in repos:
        private = " [private]" if repo.get("private") else ""
        desc = repo.get("description") or ""
        desc_str = f" — {desc}" if desc else ""
        lines.append(f"• {repo['name']}{private}{desc_str}")
    return "\n".join(lines)


# ── Tool 5: get_github_profile ───────────────────────────────────────────────

@mcp.tool()
def get_github_profile(username: str) -> str:
    """
    Get a full profile summary for a GitHub user: bio, location, stats,
    language breakdown across all repos, and top repositories with descriptions.

    USE THIS — not search_repositories — whenever the user asks to analyse a GitHub
    account, extract skills, assess a developer, or give career advice based on
    their GitHub. Works for any username including those with hyphens.

    Parameters
    ----------
    username : str
        GitHub username (e.g. "rayen-ben-mimoun").
    """
    if not GITHUB_TOKEN:
        return "GITHUB_PERSONAL_ACCESS_TOKEN is not set in .env — cannot call GitHub API."

    gh_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    # 1. User profile
    u = requests.get(f"https://api.github.com/users/{username}", headers=gh_headers, timeout=15)
    if u.status_code == 404:
        return f"GitHub user '{username}' not found."
    if u.status_code != 200:
        return f"GitHub API error ({u.status_code}): {u.text[:200]}"
    user = u.json()

    # 2. Repos (up to 100, sorted by stars)
    r = requests.get(
        f"https://api.github.com/users/{username}/repos",
        headers=gh_headers,
        params={"per_page": 100, "sort": "updated"},
        timeout=15,
    )
    repos = r.json() if r.status_code == 200 else []

    # Aggregate language bytes across all repos
    lang_totals: dict[str, int] = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            lang_totals[lang] = lang_totals.get(lang, 0) + 1

    top_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:8]
    lang_str = ", ".join(f"{l} ({c} repos)" for l, c in top_langs) if top_langs else "unknown"

    # Top 10 repos by stars
    top_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:10]

    lines = [
        f"# GitHub Profile: {user.get('name') or username} (@{username})",
        "",
        f"**Bio:** {user.get('bio') or 'Not set'}",
        f"**Location:** {user.get('location') or 'Not set'}",
        f"**Company:** {user.get('company') or 'Not set'}",
        f"**Blog/Website:** {user.get('blog') or 'Not set'}",
        f"**Public repos:** {user.get('public_repos', 0)}  |  "
        f"**Followers:** {user.get('followers', 0)}  |  "
        f"**Following:** {user.get('following', 0)}",
        f"**Account created:** {user.get('created_at', '')[:10]}",
        "",
        f"**Primary languages:** {lang_str}",
        "",
        "## Top repositories (by stars)",
    ]

    for repo in top_repos:
        stars   = repo.get("stargazers_count", 0)
        forks   = repo.get("forks_count", 0)
        lang    = repo.get("language") or "—"
        desc    = repo.get("description") or "No description"
        updated = repo.get("updated_at", "")[:10]
        topics  = ", ".join(repo.get("topics", [])) or "—"
        lines += [
            f"\n### {repo['name']}",
            f"- Stars: {stars}  |  Forks: {forks}  |  Language: {lang}",
            f"- Last updated: {updated}",
            f"- Topics: {topics}",
            f"- Description: {desc}",
            f"- URL: {repo['html_url']}",
            f"- Raw base URL: https://raw.githubusercontent.com/{username}/{repo['name']}/HEAD/",
        ]

    lines += [
        "",
        "---",
        "To deep-dive into a specific repo, call index_github_repo(username, repo_name) "
        "and then query_documents() for detailed code analysis.",
    ]

    return "\n".join(lines)


# ── Tool 6: index_github_repo ─────────────────────────────────────────────────

@mcp.tool()
def index_github_repo(
    username: str,
    repo_name: str,
    provider: str = "local",
    max_files: int = 10,
) -> str:
    """
    Automatically fetch and index the key files from a GitHub repository
    into the RAG assistant — README, main source files, config files.

    After calling this, use query_documents() to ask detailed questions about
    the repo: architecture, patterns, skills demonstrated, code quality, etc.

    Returns immediately — call check_indexing_status(filename) to track progress
    for each file.

    Parameters
    ----------
    username : str
        GitHub username (e.g. "rayenbm04").
    repo_name : str
        Repository name (e.g. "rag-assistant").
    provider : str
        "local" or "cloud" — vision model for any PDFs/images in the repo.
    max_files : int
        Max number of source files to index (excluding README). Default 10.
    """
    if not GITHUB_TOKEN:
        return "GITHUB_PERSONAL_ACCESS_TOKEN is not set in .env."

    gh_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    base_api = f"https://api.github.com/repos/{username}/{repo_name}"

    # Verify repo exists
    meta = requests.get(base_api, headers=gh_headers, timeout=15)
    if meta.status_code == 404:
        return f"Repo '{username}/{repo_name}' not found or not accessible."
    if meta.status_code != 200:
        return f"GitHub API error ({meta.status_code}): {meta.text[:200]}"

    default_branch = meta.json().get("default_branch", "main")

    # Walk the repo tree (flat, one level of recursion)
    tree_r = requests.get(
        f"{base_api}/git/trees/{default_branch}",
        headers=gh_headers,
        params={"recursive": "1"},
        timeout=20,
    )
    if tree_r.status_code != 200:
        return f"Could not fetch repo tree: {tree_r.status_code}"

    tree = tree_r.json().get("tree", [])

    # Prioritise: README first, then source files, skip binaries/lockfiles
    SKIP_PATTERNS = {
        "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock",
        ".gitignore", ".env", ".env.example",
    }
    SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".venv", "venv"}
    SOURCE_EXTS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp",
        ".c", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".ipynb",
        ".sql", ".sh", ".yaml", ".yml", ".toml", ".md", ".txt",
    }

    readme_files = []
    source_files = []

    for item in tree:
        if item.get("type") != "blob":
            continue
        path: str = item["path"]
        parts = path.split("/")

        # Skip hidden/vendor dirs
        if any(p in SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
            continue
        filename = parts[-1]
        if filename in SKIP_PATTERNS:
            continue

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        name_lower = filename.lower()

        if name_lower.startswith("readme"):
            readme_files.append(path)
        elif ext in SOURCE_EXTS and item.get("size", 0) < 200_000:  # skip files >200KB
            source_files.append(path)

    # Build final file list: README(s) first, then source up to max_files
    to_index = readme_files[:2] + source_files[:max_files]
    if not to_index:
        return f"No indexable files found in '{username}/{repo_name}'."

    indexed: list[str] = []
    errors:  list[str] = []

    for path in to_index:
        raw_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/{default_branch}/{path}"
        # Use just the filename as the index key (prefix with repo name to avoid collisions)
        safe_filename = f"{repo_name}__{path.replace('/', '__')}"
        try:
            indexed_name = _fetch_and_post(raw_url, safe_filename, provider, gh_headers)
            indexed.append(indexed_name)
        except Exception as e:
            errors.append(f"{path}: {e}")

    result_lines = [
        f"✓ Indexing started for {len(indexed)} file(s) from '{username}/{repo_name}':",
    ]
    for name in indexed:
        result_lines.append(f"  • {name}")
    if errors:
        result_lines.append(f"\n⚠ {len(errors)} file(s) failed:")
        for e in errors:
            result_lines.append(f"  • {e}")
    result_lines += [
        "",
        "Call check_indexing_status(filename) for each file to track progress.",
        "Once ready, use query_documents() to analyse the repo.",
    ]
    return "\n".join(result_lines)


def _fetch_and_post(url: str, filename: str, provider: str, extra_headers: dict) -> str:
    """Download from URL with auth headers and POST to /upload."""
    resp = requests.get(url, headers=extra_headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Download failed ({resp.status_code})")
    return _post_file(filename, resp.content, provider)


# ── Tool 7: upload_document_from_url ─────────────────────────────────────────

@mcp.tool()
def upload_document_from_url(
    url: str,
    filename: str = "",
    provider: str = "local",
) -> str:
    """
    Download a file from a URL and index it in the RAG assistant.

    Perfect for the GitHub → RAG workflow:
      1. Use the GitHub MCP to get the raw download URL of a file.
      2. Pass that URL here — the MCP server downloads and uploads it directly.

    Returns immediately once the file is accepted — indexing runs in the
    background. Call check_indexing_status(filename) to monitor progress.

    For private GitHub repos the server automatically adds your
    GITHUB_PERSONAL_ACCESS_TOKEN from .env.

    Parameters
    ----------
    url : str
        Direct download URL. For GitHub use the raw URL:
        https://raw.githubusercontent.com/owner/repo/main/path/file.py
    filename : str
        Override the file name. If omitted, inferred from the URL.
    provider : str
        "local" or "cloud" — vision model for image/scanned PDF pages.
    """
    dl_headers: dict = {}
    if GITHUB_TOKEN and ("github.com" in url or "githubusercontent.com" in url):
        dl_headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        resp = requests.get(url, headers=dl_headers, timeout=60)
        if resp.status_code != 200:
            return f"Failed to download file ({resp.status_code}): {url}"
        content = resp.content
    except Exception as e:
        return f"Download error: {e}"

    if not filename:
        filename = url.rstrip("/").split("/")[-1].split("?")[0]
    if not filename:
        return "Could not infer a filename from the URL. Please pass filename= explicitly."

    try:
        indexed_name = _post_file(filename, content, provider)
    except RuntimeError as e:
        return str(e)

    return (
        f"✓ '{indexed_name}' uploaded — indexing started in the background.\n"
        f"Call check_indexing_status('{indexed_name}') in ~30 s to see when it's ready."
    )


# ── Tool 5: upload_document_content ──────────────────────────────────────────

@mcp.tool()
def upload_document_content(
    filename: str,
    content_base64: str,
    provider: str = "local",
) -> str:
    """
    Upload and index a document from base64-encoded bytes.

    Use this when the user attaches a file directly to the conversation.
    Returns immediately — call check_indexing_status(filename) to monitor.

    Parameters
    ----------
    filename : str
        The file name including extension (e.g. "report.pdf").
    content_base64 : str
        Base64-encoded file content.
    provider : str
        "local" or "cloud".
    """
    try:
        content = base64.b64decode(content_base64)
    except Exception as e:
        return f"Failed to decode base64 content: {e}"

    try:
        indexed_name = _post_file(filename, content, provider)
    except RuntimeError as e:
        return str(e)

    return (
        f"✓ '{indexed_name}' uploaded — indexing started in the background.\n"
        f"Call check_indexing_status('{indexed_name}') in ~30 s to see when it's ready."
    )


# ── Tool 6: check_indexing_status ────────────────────────────────────────────

@mcp.tool()
def check_indexing_status(filename: str) -> str:
    """
    Check whether a previously uploaded document has finished indexing.

    Call this after any upload tool returns. For large files (e.g. 3000-line
    Python files) embedding can take 1–5 minutes locally — poll every 30 s.

    Parameters
    ----------
    filename : str
        The file name returned by the upload tool (e.g. "main.py").

    Returns
    -------
    str
        Current status: ready / processing (with page progress) / error / unknown.
    """
    try:
        s = requests.get(
            f"{BASE_URL}/status/{filename}",
            headers=_headers(),
            timeout=10,
        )
    except Exception as e:
        return f"Could not reach backend: {e}"

    if s.status_code == 404:
        return f"'{filename}' not found. Has it been uploaded yet?"
    if s.status_code != 200:
        return f"Status check failed ({s.status_code}): {s.text[:200]}"

    data     = s.json()
    status   = data.get("status", "unknown")
    progress = data.get("progress") or {}   # backend sends null when no progress yet
    cur      = progress.get("current", 0)
    tot      = progress.get("total", 0)

    if status == "ready":
        return f"✓ '{filename}' is fully indexed and ready to query."
    if status == "error":
        return f"✗ Indexing failed for '{filename}'. Try re-uploading."
    if status in ("indexing", "processing"):
        if tot:
            pct = int(cur / tot * 100)
            return f"⏳ '{filename}' is indexing: {cur}/{tot} pages ({pct}%). Check again in 30 s."
        return f"⏳ '{filename}' is indexing (no page count yet). Check again in 30 s."
    if status == "unknown":
        return f"'{filename}' is not in the indexing queue — it may already be ready or not uploaded yet."
    return f"⏳ '{filename}' status: {status}. Check again in 30 s."


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Verify credentials on startup so failures are obvious immediately
    try:
        _get_token()
        print("[mcp_server] Auth OK — RAG Assistant MCP server starting", file=sys.stderr)
    except RuntimeError as e:
        print(f"[mcp_server] {e}", file=sys.stderr)
        sys.exit(1)

    mcp.run(transport="stdio")
