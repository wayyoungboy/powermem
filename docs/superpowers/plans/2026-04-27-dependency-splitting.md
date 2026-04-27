# Dependency Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split powermem's monolithic hard-dependency list into a minimal core plus opt-in extras, so `pip install powermem` installs only what every user needs, and features like CLI, HTTP server, MCP, OceanBase, PostgreSQL, and each LLM provider are installed on demand.

**Architecture:** `pyproject.toml` is restructured so `[dependencies]` contains only universally-needed packages; each optional group of packages becomes a named extra under `[project.optional-dependencies]`. Every file that directly imports an optional package is given a lazy-import guard that prints a user-friendly install hint instead of an opaque `ImportError`. No public APIs change; only import structure and packaging metadata are affected.

**Tech Stack:** Python packaging (setuptools / pyproject.toml), `importlib`, `try/except ImportError` guards, FastMCP, FastAPI, Click, pytest.

---

## Scope

This plan is split into three independent phases, each its own PR/branch:

| Phase | Branch | Extras delivered |
|-------|--------|-----------------|
| 1 – CLI / Server / MCP | `feat-optional-cli-server-0427` | `[cli]` `[server]` `[mcp]` |
| 2 – Storage backends | `feat-optional-storage-MMDD` | `[oceanbase]` `[pgvector]` `[seekdb]` |
| 3 – LLM / Embedding providers | `feat-optional-providers-MMDD` | `[anthropic]` `[google]` `[vertexai]` `[together]` `[ollama]` `[qwen]` `[zai]` `[azure]` |

A `[full]` extra that aggregates all others is added at the end of Phase 3.

---

## Target `pyproject.toml` state (end of all phases)

```toml
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.24.0",
    "sqlalchemy>=2.0.0",        # SQLite storage (no extra driver needed)
    "numpy>=1.21.0",
    "pytz>=2023.3",
    "python-dotenv>=1.0.0",
    "rank-bm25>=0.2.2",         # BM25 search algorithm
    "openai>=1.90.0,<3.0.0",    # default compatible API (OpenAI / Qwen / DeepSeek / vLLM …)
    "psutil>=5.9.0",
]

[project.optional-dependencies]
# ── Feature components ────────────────────────────────────────────────────
cli    = ["click>=8.0.0"]
server = ["click>=8.0.0", "fastapi>=0.100.0", "python-multipart>=0.0.6",
          "uvicorn>=0.23.0", "slowapi>=0.1.9"]
mcp    = ["fastmcp>=1.0", "uvicorn>=0.27.1"]

# ── Storage backends ──────────────────────────────────────────────────────
seekdb    = ["pyseekdb>=0.1.0"]
oceanbase = ["pyobvector>=0.2.24,<0.3.0", "sqlglot>=26.0.1,<26.25.0", "jieba>=0.42.1"]
pgvector  = ["psycopg2-binary>=2.9.0", "pgvector>=0.2.0",
             "psycopg>=3.2.8", "psycopg-pool>=3.2.6,<4.0.0"]

# ── LLM / Embedding providers ─────────────────────────────────────────────
anthropic = ["anthropic>=0.7.0"]
google    = ["google-generativeai>=0.3.0", "google-genai>=1.0.0"]
vertexai  = ["vertexai>=0.1.0"]
together  = ["together>=0.2.10"]
ollama    = ["ollama>=0.1.0"]
qwen      = ["dashscope>=1.14.0"]
zai       = ["zai-sdk>=0.2.0"]
azure     = ["azure-identity>=1.24.0"]
extras    = ["sentence-transformers>=5.0.0"]

# ── Convenience bundles ───────────────────────────────────────────────────
full = [
    "powermem[cli,server,mcp,seekdb,oceanbase,pgvector,anthropic,google,vertexai,together,ollama,qwen,zai,azure,extras]",
]

# ── Dev / test (unchanged) ────────────────────────────────────────────────
dev  = [...]
test = [...]
```

---

## File map

### Phase 1

| Action | Path | Change |
|--------|------|--------|
| Modify | `pyproject.toml` | Remove cli/server deps from hard list; `[cli]`/`[server]`/`[mcp]` extras already added |
| Modify | `src/powermem/cli/main.py` | Import guard for `click` |
| Modify | `src/server/cli/server.py` | Import guard for `click` + `uvicorn` + `fastapi` |
| Create | `src/powermem/mcp/__init__.py` | Package marker (**done**) |
| Create | `src/powermem/mcp/server.py` | 13 MCP tools (**done**) |
| Create | `src/powermem/mcp/__main__.py` | `python -m powermem.mcp` alias (**done**) |
| Create | `tests/unit/test_mcp_import_guard.py` | Guard test |
| Create | `tests/unit/test_cli_import_guard.py` | Guard test |

### Phase 2

| Action | Path | Change |
|--------|------|--------|
| Modify | `pyproject.toml` | Remove oceanbase/pgvector/seekdb from hard list; add extras |
| Modify | `src/powermem/storage/oceanbase/oceanbase.py` | Guard for `pyobvector`, `sqlglot`, `jieba` |
| Modify | `src/powermem/storage/oceanbase/oceanbase_graph.py` | Same guards |
| Modify | `src/powermem/storage/pgvector/pgvector.py` | Guard for `psycopg2`, `pgvector`, `psycopg` |
| Modify | `src/powermem/storage/factory.py` | Guard unknown provider message |
| Create | `tests/unit/test_storage_import_guards.py` | Guard tests |

### Phase 3

| Action | Path | Change |
|--------|------|--------|
| Modify | `pyproject.toml` | Remove all provider deps from hard list; add extras |
| Modify | `src/powermem/integrations/llm/anthropic.py` | Guard `anthropic` |
| Modify | `src/powermem/integrations/llm/gemini.py` | Guard `google-generativeai` / `google-genai` |
| Modify | `src/powermem/integrations/llm/azure.py` | Guard `azure-identity` |
| Modify | `src/powermem/integrations/llm/together.py` | Guard `together` |
| Modify | `src/powermem/integrations/llm/ollama.py` | Guard `ollama` |
| Modify | `src/powermem/integrations/llm/qwen.py` | Guard `dashscope` |
| Modify | `src/powermem/integrations/llm/qwen_asr.py` | Guard `dashscope` |
| Modify | `src/powermem/integrations/llm/vertexai.py` | Guard `vertexai` |
| Modify | `src/powermem/integrations/llm/zai.py` | Guard `zai-sdk` |
| Modify | `src/powermem/integrations/embeddings/azure_openai.py` | Guard `azure-identity` |
| Modify | `src/powermem/integrations/embeddings/gemini.py` | Guard `google-genai` |
| Modify | `src/powermem/integrations/embeddings/vertexai.py` | Guard `vertexai` |
| Modify | `src/powermem/integrations/embeddings/together.py` | Guard `together` |
| Modify | `src/powermem/integrations/embeddings/huggingface.py` | Guard `sentence-transformers` |
| Create | `tests/unit/test_provider_import_guards.py` | Guard tests |

---

## Phase 1 — CLI / Server / MCP

> Branch: `feat-optional-cli-server-0427`
> MCP files already created. Tasks 1–2 complete the pyproject change and add guards.

---

### Task 1: Strip cli/server deps from hard dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove the five packages from `dependencies`**

In `pyproject.toml`, remove these lines from the `dependencies` array:

```toml
    "fastapi>=0.100.0",
    "python-multipart>=0.0.6",
    "uvicorn>=0.23.0",
    "slowapi>=0.1.9",
    "click>=8.0.0",
```

`rank-bm25>=0.2.2` (the line immediately after `click`) stays.

- [ ] **Step 2: Verify extras are already present**

Run:
```bash
grep -A3 "^\[project.optional-dependencies\]" pyproject.toml | head -12
```
Expected: `cli`, `server`, `mcp` sections visible.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(deps): move cli/server deps to optional extras"
```

---

### Task 2: Import guard — `powermem/cli/main.py`

**Files:**
- Modify: `src/powermem/cli/main.py:1-10`
- Create: `tests/unit/test_cli_import_guard.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_cli_import_guard.py`:

```python
"""Verify CLI entry point prints a helpful message when click is missing."""
import subprocess
import sys


def test_cli_guard_message(monkeypatch, tmp_path):
    """Running cli/main.py without click installed exits with code 1 and a hint."""
    script = tmp_path / "run.py"
    script.write_text(
        "import sys\n"
        "sys.modules['click'] = None\n"          # simulate missing package
        "from importlib import import_module\n"
        "import importlib.util, types\n"
        # patch builtins.__import__ to raise ImportError for click
        "import builtins\n"
        "_real = builtins.__import__\n"
        "def _fake(name, *a, **kw):\n"
        "    if name == 'click': raise ImportError('No module named click')\n"
        "    return _real(name, *a, **kw)\n"
        "builtins.__import__ = _fake\n"
        "from powermem.cli import main\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "powermem[cli]" in result.stderr
```

Run: `pytest tests/unit/test_cli_import_guard.py -v`
Expected: FAIL (guard does not exist yet).

- [ ] **Step 2: Add guard to `src/powermem/cli/main.py`**

Insert the following block **at the very top of the file**, before any other import:

```python
import sys as _sys


def _require_cli_deps() -> None:
    try:
        import click  # noqa: F401
    except ImportError:
        _sys.stderr.write(
            "Missing dependency: click.\n"
            "Run: pip install 'powermem[cli]'\n"
        )
        _sys.exit(1)


_require_cli_deps()
```

The rest of the file (`import click`, `import sys`, …) remains unchanged.

- [ ] **Step 3: Run test — expect PASS**

```bash
source .venv/bin/activate
pytest tests/unit/test_cli_import_guard.py -v
```
Expected: PASS.

- [ ] **Step 4: Smoke-test with click available**

```bash
source .venv/bin/activate
python -c "from powermem.cli.main import cli; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add src/powermem/cli/main.py tests/unit/test_cli_import_guard.py
git commit -m "feat(cli): add import guard — hint pip install powermem[cli]"
```

---

### Task 3: Import guard — `server/cli/server.py`

**Files:**
- Modify: `src/server/cli/server.py:1-10`
- Create: `tests/unit/test_server_import_guard.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_server_import_guard.py`:

```python
"""Verify server entry point prints a helpful message when server deps are missing."""
import subprocess
import sys


def test_server_guard_message(tmp_path):
    """Running server/cli/server.py without fastapi exits with code 1 and a hint."""
    script = tmp_path / "run.py"
    script.write_text(
        "import builtins\n"
        "_real = builtins.__import__\n"
        "def _fake(name, *a, **kw):\n"
        "    if name in ('fastapi', 'uvicorn', 'click'):\n"
        "        raise ImportError(f'No module named {name}')\n"
        "    return _real(name, *a, **kw)\n"
        "builtins.__import__ = _fake\n"
        "from server.cli import server\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "powermem[server]" in result.stderr
```

Run: `pytest tests/unit/test_server_import_guard.py -v`
Expected: FAIL.

- [ ] **Step 2: Add guard to `src/server/cli/server.py`**

Insert at the **very top**, before any other import:

```python
import sys as _sys


def _require_server_deps() -> None:
    missing = []
    for pkg in ("click", "fastapi", "uvicorn"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        _sys.stderr.write(
            f"Missing dependencies: {', '.join(missing)}.\n"
            "Run: pip install 'powermem[server]'\n"
        )
        _sys.exit(1)


_require_server_deps()
```

The existing `import click` / `import uvicorn` lines that follow remain in place.

- [ ] **Step 3: Run test — expect PASS**

```bash
pytest tests/unit/test_server_import_guard.py -v
```
Expected: PASS.

- [ ] **Step 4: Smoke-test with deps available**

```bash
source .venv/bin/activate
python -c "from server.cli.server import server; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add src/server/cli/server.py tests/unit/test_server_import_guard.py
git commit -m "feat(server): add import guard — hint pip install powermem[server]"
```

---

### Task 4: Import guard — `powermem/mcp/server.py` test

**Files:**
- Create: `tests/unit/test_mcp_import_guard.py`

The guard is already implemented in `src/powermem/mcp/server.py`. This task adds the test.

- [ ] **Step 1: Write and run the test**

Create `tests/unit/test_mcp_import_guard.py`:

```python
"""Verify MCP server entry point prints a helpful message when fastmcp is missing."""
import subprocess
import sys


def test_mcp_guard_message(tmp_path):
    script = tmp_path / "run.py"
    script.write_text(
        "import builtins\n"
        "_real = builtins.__import__\n"
        "def _fake(name, *a, **kw):\n"
        "    if name == 'fastmcp':\n"
        "        raise ImportError('No module named fastmcp')\n"
        "    return _real(name, *a, **kw)\n"
        "builtins.__import__ = _fake\n"
        "from powermem.mcp import server\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "powermem[mcp]" in result.stderr
```

Run:
```bash
pytest tests/unit/test_mcp_import_guard.py -v
```
Expected: PASS (guard already present).

- [ ] **Step 2: Commit**

```bash
git add tests/unit/test_mcp_import_guard.py
git commit -m "test(mcp): verify import guard exits with install hint"
```

---

### Task 5: Phase 1 PR

- [ ] **Step 1: Run all unit tests**

```bash
source .venv/bin/activate
pytest tests/unit/ -v
```
Expected: all PASS.

- [ ] **Step 2: Push and open PR**

```bash
git push origin feat-optional-cli-server-0427
```

PR title: `feat(deps): make cli / server / mcp optional extras`

PR body checklist:
```
- [ ] `pip install powermem` no longer installs click/fastapi/uvicorn/slowapi
- [ ] `pip install powermem[cli]` → pmem / powermem-cli work
- [ ] `pip install powermem[server]` → powermem-server works
- [ ] `pip install powermem[mcp]` → powermem-mcp works
- [ ] Missing deps print install hint and exit(1)
- [ ] All unit tests pass
```

---

## Phase 2 — Storage backends

> New branch: `feat-optional-storage-MMDD` from `main` (after Phase 1 merges).

### Guard pattern used in every storage file

```python
# At top of file, before any provider-specific import
import sys as _sys

def _require_X() -> None:
    missing = []
    for pkg in ("pkg_a", "pkg_b"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        _sys.stderr.write(
            f"Missing dependencies: {', '.join(missing)}.\n"
            "Run: pip install 'powermem[EXTRA_NAME]'\n"
        )
        _sys.exit(1)

_require_X()
```

---

### Task 6: Strip storage deps from hard dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove storage packages from `dependencies`**

Remove from the `dependencies` array:
```toml
    "pyobvector>=0.2.24,<0.3.0",
    "sqlglot>=26.0.1,<26.25.0",
    "jieba>=0.42.1",
    "psycopg2-binary>=2.9.0",
    "pgvector>=0.2.0",
    "psycopg>=3.2.8",
    "psycopg-pool>=3.2.6,<4.0.0",
    "pyseekdb>=0.1.0",
```

- [ ] **Step 2: Add storage extras to `[project.optional-dependencies]`**

```toml
seekdb    = ["pyseekdb>=0.1.0"]
oceanbase = ["pyobvector>=0.2.24,<0.3.0", "sqlglot>=26.0.1,<26.25.0", "jieba>=0.42.1"]
pgvector  = ["psycopg2-binary>=2.9.0", "pgvector>=0.2.0",
             "psycopg>=3.2.8", "psycopg-pool>=3.2.6,<4.0.0"]
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(deps): move storage deps to optional extras [oceanbase,pgvector,seekdb]"
```

---

### Task 7: Import guard — OceanBase storage

**Files:**
- Modify: `src/powermem/storage/oceanbase/oceanbase.py`
- Modify: `src/powermem/storage/oceanbase/oceanbase_graph.py`
- Create: `tests/unit/test_storage_import_guards.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_storage_import_guards.py`:

```python
import subprocess, sys

def _run_with_blocked(blocked: list, import_path: str, tmp_path):
    script = tmp_path / "run.py"
    blocked_str = repr(blocked)
    script.write_text(
        f"import builtins\n"
        f"_real = builtins.__import__\n"
        f"def _fake(name, *a, **kw):\n"
        f"    if name in {blocked_str}: raise ImportError(f'No module named {{name}}')\n"
        f"    return _real(name, *a, **kw)\n"
        f"builtins.__import__ = _fake\n"
        f"import {import_path}\n"
    )
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True)

def test_oceanbase_guard(tmp_path):
    r = _run_with_blocked(["pyobvector"], "powermem.storage.oceanbase.oceanbase", tmp_path)
    assert r.returncode == 1
    assert "powermem[oceanbase]" in r.stderr

def test_pgvector_guard(tmp_path):
    r = _run_with_blocked(["psycopg2", "psycopg"], "powermem.storage.pgvector.pgvector", tmp_path)
    assert r.returncode == 1
    assert "powermem[pgvector]" in r.stderr
```

Run: `pytest tests/unit/test_storage_import_guards.py -v`
Expected: FAIL.

- [ ] **Step 2: Add guard to `src/powermem/storage/oceanbase/oceanbase.py`**

At the very top, before any existing import:

```python
import sys as _sys


def _require_oceanbase_deps() -> None:
    missing = []
    for pkg in ("pyobvector", "sqlglot", "jieba"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        _sys.stderr.write(
            f"Missing dependencies: {', '.join(missing)}.\n"
            "Run: pip install 'powermem[oceanbase]'\n"
        )
        _sys.exit(1)


_require_oceanbase_deps()
```

- [ ] **Step 3: Add same guard to `src/powermem/storage/oceanbase/oceanbase_graph.py`**

Same block as Step 2 (copy verbatim).

- [ ] **Step 4: Add guard to `src/powermem/storage/pgvector/pgvector.py`**

```python
import sys as _sys


def _require_pgvector_deps() -> None:
    missing = []
    for pkg in ("psycopg2", "pgvector", "psycopg"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        _sys.stderr.write(
            f"Missing dependencies: {', '.join(missing)}.\n"
            "Run: pip install 'powermem[pgvector]'\n"
        )
        _sys.exit(1)


_require_pgvector_deps()
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/unit/test_storage_import_guards.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/powermem/storage/oceanbase/oceanbase.py \
        src/powermem/storage/oceanbase/oceanbase_graph.py \
        src/powermem/storage/pgvector/pgvector.py \
        tests/unit/test_storage_import_guards.py
git commit -m "feat(storage): add import guards for oceanbase and pgvector"
```

---

### Task 8: Phase 2 PR

Same checklist pattern as Task 5. Push `feat-optional-storage-MMDD` and open PR.

---

## Phase 3 — LLM / Embedding providers

> New branch: `feat-optional-providers-MMDD` from `main` (after Phase 2 merges).

### Guard pattern for each provider file

```python
import sys as _sys


def _require_PROVIDER() -> None:
    try:
        import PACKAGE  # noqa: F401
    except ImportError:
        _sys.stderr.write(
            "Missing dependency: PACKAGE.\n"
            "Run: pip install 'powermem[EXTRA]'\n"
        )
        _sys.exit(1)


_require_PROVIDER()
```

---

### Task 9: Strip all provider deps from hard dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove provider packages from `dependencies`**

Remove:
```toml
    "azure-identity>=1.24.0",
    "together>=0.2.10",
    "anthropic>=0.7.0",
    "ollama>=0.1.0",
    "vertexai>=0.1.0",
    "google-generativeai>=0.3.0",
    "google-genai>=1.0.0",
    "dashscope>=1.14.0",
    "zai-sdk>=0.2.0",
```

`openai` stays in hard deps.

- [ ] **Step 2: Add provider extras**

```toml
anthropic = ["anthropic>=0.7.0"]
google    = ["google-generativeai>=0.3.0", "google-genai>=1.0.0"]
vertexai  = ["vertexai>=0.1.0"]
together  = ["together>=0.2.10"]
ollama    = ["ollama>=0.1.0"]
qwen      = ["dashscope>=1.14.0"]
zai       = ["zai-sdk>=0.2.0"]
azure     = ["azure-identity>=1.24.0"]
extras    = ["sentence-transformers>=5.0.0"]
```

- [ ] **Step 3: Add `full` bundle**

```toml
full = [
    "powermem[cli,server,mcp,seekdb,oceanbase,pgvector,anthropic,google,vertexai,together,ollama,qwen,zai,azure,extras]",
]
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat(deps): move all provider deps to optional extras; add [full] bundle"
```

---

### Task 10: Import guards — LLM providers

**Files:**
- Modify: `src/powermem/integrations/llm/anthropic.py`
- Modify: `src/powermem/integrations/llm/gemini.py`
- Modify: `src/powermem/integrations/llm/azure.py`
- Modify: `src/powermem/integrations/llm/together.py`
- Modify: `src/powermem/integrations/llm/ollama.py`
- Modify: `src/powermem/integrations/llm/qwen.py`
- Modify: `src/powermem/integrations/llm/qwen_asr.py`
- Modify: `src/powermem/integrations/llm/vertexai.py`
- Modify: `src/powermem/integrations/llm/zai.py`
- Create: `tests/unit/test_provider_import_guards.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_provider_import_guards.py`:

```python
import subprocess, sys

def _guard_test(blocked_pkg, module_path, extra_name, tmp_path):
    script = tmp_path / f"run_{blocked_pkg}.py"
    script.write_text(
        f"import builtins\n"
        f"_real = builtins.__import__\n"
        f"def _fake(name, *a, **kw):\n"
        f"    if name == {repr(blocked_pkg)}: raise ImportError(f'No module named {blocked_pkg}')\n"
        f"    return _real(name, *a, **kw)\n"
        f"builtins.__import__ = _fake\n"
        f"import {module_path}\n"
    )
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert r.returncode == 1, f"{module_path}: expected exit 1"
    assert f"powermem[{extra_name}]" in r.stderr, f"{module_path}: missing install hint"

def test_anthropic_guard(tmp_path):
    _guard_test("anthropic", "powermem.integrations.llm.anthropic", "anthropic", tmp_path)

def test_gemini_guard(tmp_path):
    _guard_test("google.generativeai", "powermem.integrations.llm.gemini", "google", tmp_path)

def test_azure_llm_guard(tmp_path):
    _guard_test("azure.identity", "powermem.integrations.llm.azure", "azure", tmp_path)

def test_together_llm_guard(tmp_path):
    _guard_test("together", "powermem.integrations.llm.together", "together", tmp_path)

def test_ollama_guard(tmp_path):
    _guard_test("ollama", "powermem.integrations.llm.ollama", "ollama", tmp_path)

def test_qwen_guard(tmp_path):
    _guard_test("dashscope", "powermem.integrations.llm.qwen", "qwen", tmp_path)

def test_vertexai_guard(tmp_path):
    _guard_test("vertexai", "powermem.integrations.llm.vertexai", "vertexai", tmp_path)

def test_zai_guard(tmp_path):
    _guard_test("zai", "powermem.integrations.llm.zai", "zai", tmp_path)
```

Run: `pytest tests/unit/test_provider_import_guards.py -v`
Expected: FAIL on all.

- [ ] **Step 2: Add guards — one per file**

For each file below, insert the matching guard block at the very top before existing imports.

**`src/powermem/integrations/llm/anthropic.py`**
```python
import sys as _sys
try:
    import anthropic  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: anthropic.\nRun: pip install 'powermem[anthropic]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/gemini.py`**
```python
import sys as _sys
try:
    import google.generativeai  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: google-generativeai.\nRun: pip install 'powermem[google]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/azure.py`**
```python
import sys as _sys
try:
    import azure.identity  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: azure-identity.\nRun: pip install 'powermem[azure]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/together.py`**
```python
import sys as _sys
try:
    import together  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: together.\nRun: pip install 'powermem[together]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/ollama.py`**
```python
import sys as _sys
try:
    import ollama  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: ollama.\nRun: pip install 'powermem[ollama]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/qwen.py`** and **`qwen_asr.py`**
```python
import sys as _sys
try:
    import dashscope  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: dashscope.\nRun: pip install 'powermem[qwen]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/vertexai.py`**
```python
import sys as _sys
try:
    import vertexai  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: vertexai.\nRun: pip install 'powermem[vertexai]'\n")
    _sys.exit(1)
```

**`src/powermem/integrations/llm/zai.py`**
```python
import sys as _sys
try:
    import zai  # noqa: F401
except ImportError:
    _sys.stderr.write("Missing dependency: zai-sdk.\nRun: pip install 'powermem[zai]'\n")
    _sys.exit(1)
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
pytest tests/unit/test_provider_import_guards.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/powermem/integrations/llm/ tests/unit/test_provider_import_guards.py
git commit -m "feat(providers): add import guards for all LLM providers"
```

---

### Task 11: Import guards — Embedding providers

**Files:**
- Modify: `src/powermem/integrations/embeddings/azure_openai.py`
- Modify: `src/powermem/integrations/embeddings/gemini.py`
- Modify: `src/powermem/integrations/embeddings/vertexai.py`
- Modify: `src/powermem/integrations/embeddings/together.py`
- Modify: `src/powermem/integrations/embeddings/huggingface.py`

Same guard pattern as Task 10. Guards are identical to their LLM counterparts (same package → same extra).

- [ ] **Step 1: Add guards to each file** (same blocks as Task 10 Step 2 for matching providers)

- [ ] **Step 2: Extend `tests/unit/test_provider_import_guards.py` with embedding tests**

Append to the existing test file:

```python
def test_azure_embedding_guard(tmp_path):
    _guard_test("azure.identity", "powermem.integrations.embeddings.azure_openai", "azure", tmp_path)

def test_gemini_embedding_guard(tmp_path):
    _guard_test("google.generativeai", "powermem.integrations.embeddings.gemini", "google", tmp_path)

def test_vertexai_embedding_guard(tmp_path):
    _guard_test("vertexai", "powermem.integrations.embeddings.vertexai", "vertexai", tmp_path)

def test_together_embedding_guard(tmp_path):
    _guard_test("together", "powermem.integrations.embeddings.together", "together", tmp_path)

def test_huggingface_guard(tmp_path):
    _guard_test("sentence_transformers", "powermem.integrations.embeddings.huggingface", "extras", tmp_path)
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
pytest tests/unit/test_provider_import_guards.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/powermem/integrations/embeddings/ tests/unit/test_provider_import_guards.py
git commit -m "feat(providers): add import guards for all embedding providers"
```

---

### Task 12: Phase 3 PR

- [ ] **Step 1: Full unit test run**

```bash
pytest tests/unit/ -v
```
Expected: all PASS.

- [ ] **Step 2: Verify minimal install has no stray heavy deps**

```bash
pip install --dry-run . 2>&1 | grep -E "anthropic|fastapi|click|pyobvector|dashscope"
```
Expected: no output (none of those pulled in as hard deps).

- [ ] **Step 3: Push and open PR**

```bash
git push origin feat-optional-providers-MMDD
```

PR title: `feat(deps): make all LLM/embedding provider deps optional`

---

## Installation reference (final state)

```bash
# Minimal core (SQLite + OpenAI-compatible API)
pip install powermem

# CLI tools
pip install "powermem[cli]"

# HTTP server
pip install "powermem[server]"

# MCP server
pip install "powermem[mcp]"
powermem-mcp sse 8000

# OceanBase storage
pip install "powermem[oceanbase]"

# PostgreSQL storage
pip install "powermem[pgvector]"

# Embedded OceanBase (SeekDB)
pip install "powermem[seekdb]"

# Anthropic / Google / others
pip install "powermem[anthropic]"
pip install "powermem[google]"

# Typical production stack
pip install "powermem[oceanbase,server,qwen]"

# Everything
pip install "powermem[full]"
```
