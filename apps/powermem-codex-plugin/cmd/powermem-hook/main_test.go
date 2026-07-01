package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
)

func TestUserPromptSubmitSearchInjectsAdditionalContext(t *testing.T) {
	var searchBody map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/memories/search" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&searchBody); err != nil {
			t.Fatal(err)
		}
		_, _ = w.Write([]byte(`{"data":{"results":[{"content":"Project Alpha uses OceanBase.","score":0.91}]}}`))
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_HOOK_SCRUB", "0")
	var out bytes.Buffer
	input := `{"hook_event_name":"UserPromptSubmit","prompt":"What do we know about Project Alpha?"}`
	if err := run(strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	if got := searchBody["query"]; got != "What do we know about Project Alpha?" {
		t.Fatalf("query = %v", got)
	}
	var hookOut map[string]any
	if err := json.Unmarshal(out.Bytes(), &hookOut); err != nil {
		t.Fatal(err)
	}
	specific := hookOut["hookSpecificOutput"].(map[string]any)
	context := specific["additionalContext"].(string)
	if !strings.Contains(context, "Project Alpha uses OceanBase.") {
		t.Fatalf("missing memory context: %s", context)
	}
}

func TestStopSavesMemoryWithMetadata(t *testing.T) {
	var saved map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/memories" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&saved); err != nil {
			t.Fatal(err)
		}
		_, _ = w.Write([]byte(`{"data":{"id":"mem_1"}}`))
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_HOOK_SCRUB", "0")
	t.Setenv("POWERMEM_CODEX_STOP_SAVE", "1")
	t.Setenv("POWERMEM_INFER_CODEX_STOP", "0")
	input := `{"hook_event_name":"Stop","session_id":"sess_1","turn_id":"turn_2","cwd":"/tmp/project","model":"gpt-5.5","permission_mode":"ask","last_assistant_message":"Implemented the hook."}`
	if err := run(strings.NewReader(input), ioDiscard{}); err != nil {
		t.Fatal(err)
	}
	if saved["run_id"] != "sess_1:turn_2" {
		t.Fatalf("run_id = %v", saved["run_id"])
	}
	if saved["infer"] != false {
		t.Fatalf("infer = %v", saved["infer"])
	}
	content := saved["content"].(string)
	if !strings.Contains(content, "Implemented the hook.") {
		t.Fatalf("content = %s", content)
	}
	meta := saved["metadata"].(map[string]any)
	if meta["source"] != "codex-hook" || meta["kind"] != "codex-stop-summary" {
		t.Fatalf("metadata = %#v", meta)
	}
}

func TestStopSavesByDefaultInNoLLMMode(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		_, _ = w.Write([]byte(`{"data":{"id":"mem_1"}}`))
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_CODEX_STOP_SAVE", "")
	t.Setenv("LLM_PROVIDER", "noop")
	input := `{"hook_event_name":"Stop","session_id":"sess","turn_id":"turn","last_assistant_message":"Implemented the hook."}`
	if err := run(strings.NewReader(input), ioDiscard{}); err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 1 {
		t.Fatalf("expected save request in no-LLM mode, got %d", calls.Load())
	}
}

func TestStopCanBeDisabled(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_CODEX_STOP_SAVE", "0")
	input := `{"hook_event_name":"Stop","session_id":"sess","turn_id":"turn","last_assistant_message":"Implemented the hook."}`
	if err := run(strings.NewReader(input), ioDiscard{}); err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 0 {
		t.Fatalf("expected disabled Stop writes, got %d calls", calls.Load())
	}
}

func TestUserPromptSubmitSavesDurableUserStatement(t *testing.T) {
	var saved map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/memories" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&saved); err != nil {
			t.Fatal(err)
		}
		_, _ = w.Write([]byte(`{"data":{"id":"mem_1"}}`))
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_HOOK_SCRUB", "0")
	t.Setenv("POWERMEM_PROMPT_SEARCH", "0")
	var out bytes.Buffer
	input := `{"hook_event_name":"UserPromptSubmit","session_id":"sess","turn_id":"turn","prompt":"我喜欢吃牛肉"}`
	if err := run(strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	if out.Len() != 0 {
		t.Fatalf("expected no self-injected output, got %s", out.String())
	}
	content := saved["content"].(string)
	if !strings.Contains(content, "User stated:") || !strings.Contains(content, "我喜欢吃牛肉") {
		t.Fatalf("content = %s", content)
	}
	if saved["infer"] != false {
		t.Fatalf("infer = %v", saved["infer"])
	}
	meta := saved["metadata"].(map[string]any)
	if meta["source"] != "codex-hook" || meta["kind"] != "codex-user-statement" {
		t.Fatalf("metadata = %#v", meta)
	}
}

func TestUserPromptSubmitQuestionDoesNotSaveUserStatement(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_PROMPT_SEARCH", "0")
	var out bytes.Buffer
	input := `{"hook_event_name":"UserPromptSubmit","prompt":"我喜欢吃什么？"}`
	if err := run(strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 0 {
		t.Fatalf("expected no save request, got %d", calls.Load())
	}
}

func TestUserPromptSubmitQuestionWithoutPunctuationDoesNotSaveUserStatement(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_PROMPT_SEARCH", "0")
	input := `{"hook_event_name":"UserPromptSubmit","prompt":"我喜欢吃什么"}`
	if err := run(strings.NewReader(input), ioDiscard{}); err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 0 {
		t.Fatalf("expected no save request, got %d", calls.Load())
	}
}

func TestRawCodexStopSummarySearchResultIsFiltered(t *testing.T) {
	resp := []byte(`{"data":{"results":[
		{"content":"Codex turn summary (session_id=s, turn_id=t, cwd=~/.powermem)\n\nassistant-only preference","metadata":{"source":"codex-hook","kind":"codex-stop-summary"},"score":0.88},
		{"content":"User likes spicy noodles.","score":0.77}
	]}}`)
	context, err := formatSearchResults(resp)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(context, "assistant-only preference") {
		t.Fatalf("raw Codex stop summary was not filtered: %s", context)
	}
	if !strings.Contains(context, "User likes spicy noodles.") {
		t.Fatalf("expected useful memory to remain: %s", context)
	}
}

func TestPromptWithSecretIsSkipped(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	var out bytes.Buffer
	input := `{"hook_event_name":"UserPromptSubmit","prompt":"Use API_KEY=test-secret-placeholder-123456 now"}`
	if err := run(strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 0 {
		t.Fatalf("expected no search request, got %d", calls.Load())
	}
	if out.Len() != 0 {
		t.Fatalf("expected no hook output, got %s", out.String())
	}
}

func TestStopWithSecretBlockSkipsWrite(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
	}))
	defer server.Close()

	t.Setenv("POWERMEM_BASE_URL", server.URL)
	t.Setenv("POWERMEM_HOOK_SECRET_ACTION", "block")
	t.Setenv("POWERMEM_CODEX_STOP_SAVE", "1")
	input := `{"hook_event_name":"Stop","session_id":"sess","turn_id":"turn","last_assistant_message":"Saved API_KEY=test-secret-placeholder-123456"}`
	if err := run(strings.NewReader(input), ioDiscard{}); err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 0 {
		t.Fatalf("expected no save request, got %d", calls.Load())
	}
}

type ioDiscard struct{}

func (ioDiscard) Write(p []byte) (int, error) {
	return len(p), nil
}
