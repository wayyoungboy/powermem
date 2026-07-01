package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

const (
	defaultPowerMemBaseURL = "http://localhost:8848"
	redactedSecret         = "<redacted:secret>"
	redactedPII            = "<redacted:pii>"
	omittedPath            = "<path omitted>"
)

type hookPrivacyConfig struct {
	Enabled            bool
	PrivacyLevel       string
	SecretAction       string
	PathPrivacy        string
	SearchSecretPolicy string
}

type scrubReport struct {
	SecretRedactions int `json:"secret_redactions"`
	PIIRedactions    int `json:"pii_redactions"`
	PathRedactions   int `json:"path_redactions"`
}

func main() {
	_ = run(os.Stdin, os.Stdout)
}

func run(r io.Reader, w io.Writer) error {
	raw, err := io.ReadAll(r)
	if err != nil || len(bytes.TrimSpace(raw)) == 0 {
		return err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil
	}
	event := stringField(payload, "hook_event_name")
	switch event {
	case "UserPromptSubmit":
		return handleUserPromptSubmit(payload, w)
	case "Stop":
		return handleStop(payload)
	default:
		return nil
	}
}

func handleUserPromptSubmit(payload map[string]any, w io.Writer) error {
	prompt := strings.TrimSpace(stringField(payload, "prompt"))
	if len([]rune(prompt)) < 2 {
		return nil
	}
	cfg := loadHookPrivacyConfig()
	var context string
	if boolEnvDefault("POWERMEM_PROMPT_SEARCH", true) {
		query, ok := scrubPromptForSearch(prompt, cfg)
		if ok {
			foundContext, err := searchMemoriesForPrompt(query, cfg)
			if err == nil {
				context = foundContext
			}
		}
	}
	_ = maybeSaveUserPromptFact(payload, prompt, cfg)
	if strings.TrimSpace(context) == "" {
		return nil
	}
	if cfg.Enabled {
		var report scrubReport
		context, report = scrubText(context, cfg)
		if shouldBlockWrite(cfg, report) || strings.TrimSpace(context) == "" {
			return nil
		}
	}
	context = truncateText(context, promptSearchMaxContextChars())
	out := map[string]any{
		"hookSpecificOutput": map[string]any{
			"hookEventName":     "UserPromptSubmit",
			"additionalContext": context,
		},
	}
	b, err := json.Marshal(out)
	if err != nil {
		return nil
	}
	_, _ = w.Write(b)
	return nil
}

func maybeSaveUserPromptFact(payload map[string]any, prompt string, cfg hookPrivacyConfig) error {
	if !boolEnvDefault("POWERMEM_USER_FACT_SAVE", true) {
		return nil
	}
	content, ok := userPromptFactMemoryContent(prompt, cfg)
	if !ok {
		return nil
	}
	sessionID := stringField(payload, "session_id")
	turnID := stringField(payload, "turn_id")
	cwd := stringField(payload, "cwd")
	model := stringField(payload, "model")
	permissionMode := stringField(payload, "permission_mode")
	runID := codexRunID(sessionID, turnID)
	meta := map[string]any{
		"source":          "codex-hook",
		"kind":            "codex-user-statement",
		"capture":         "user-prompt-submit",
		"session_id":      sessionID,
		"turn_id":         turnID,
		"cwd":             cwd,
		"model":           model,
		"permission_mode": permissionMode,
	}
	var runIDPtr *string
	if runID != "" {
		runIDPtr = &runID
	}
	return postMemory(content, meta, runIDPtr, boolEnvDefault("POWERMEM_INFER_USER_FACTS", false))
}

func userPromptFactMemoryContent(prompt string, cfg hookPrivacyConfig) (string, bool) {
	prompt = strings.TrimSpace(prompt)
	if prompt == "" || !isLikelyDurableUserStatement(prompt) {
		return "", false
	}
	if cfg.Enabled {
		scrubbed, report := scrubText(prompt, cfg)
		if report.SecretRedactions > 0 || shouldBlockWrite(cfg, report) {
			return "", false
		}
		prompt = strings.TrimSpace(scrubbed)
	}
	if prompt == "" {
		return "", false
	}
	return "User stated:\n\n" + prompt, true
}

func isLikelyDurableUserStatement(prompt string) bool {
	prompt = strings.TrimSpace(prompt)
	if prompt == "" || len([]rune(prompt)) > userFactMaxChars() {
		return false
	}
	if strings.ContainsAny(prompt, "?？") {
		return false
	}
	normalized := strings.ToLower(prompt)
	for _, marker := range []string{"什么", "怎么", "为什么", "为何", "哪", "谁", "多少", "吗", "么"} {
		if strings.Contains(prompt, marker) {
			return false
		}
	}
	for _, marker := range []string{"what", "why", "how", "which", "who", "where", "when"} {
		if strings.Contains(normalized, marker) {
			return false
		}
	}
	for _, marker := range []string{
		"我喜欢", "我很喜欢", "我非常喜欢", "我特别喜欢", "我最喜欢",
		"我爱吃", "我最爱吃", "我常吃", "我经常吃", "我通常吃",
		"我偏好", "我不喜欢", "我讨厌",
	} {
		if strings.Contains(prompt, marker) {
			return true
		}
	}
	for _, marker := range []string{
		"i like ", "i love ", "i prefer ", "i dislike ", "i hate ",
		"my favorite ", "my favourite ",
	} {
		if strings.Contains(normalized, marker) {
			return true
		}
	}
	return false
}

func userFactMaxChars() int {
	n := intEnvDefault("POWERMEM_USER_FACT_MAX_CHARS", 500)
	if n < 20 {
		return 500
	}
	return n
}

func handleStop(payload map[string]any) error {
	if !codexStopSaveEnabled() {
		return nil
	}
	message := strings.TrimSpace(stringField(payload, "last_assistant_message"))
	if message == "" {
		return nil
	}
	message = truncateText(message, maxCodexSaveChars())

	sessionID := stringField(payload, "session_id")
	turnID := stringField(payload, "turn_id")
	cwd := stringField(payload, "cwd")
	model := stringField(payload, "model")
	permissionMode := stringField(payload, "permission_mode")
	runID := codexRunID(sessionID, turnID)
	content := fmt.Sprintf("Codex turn summary (session_id=%s, turn_id=%s, cwd=%s)\n\n%s", sessionID, turnID, cwd, message)
	meta := map[string]any{
		"source":          "codex-hook",
		"kind":            "codex-stop-summary",
		"session_id":      sessionID,
		"turn_id":         turnID,
		"cwd":             cwd,
		"model":           model,
		"permission_mode": permissionMode,
	}
	return postMemory(content, meta, &runID, boolEnvDefault("POWERMEM_INFER_CODEX_STOP", true))
}

func searchMemoriesForPrompt(query string, cfg hookPrivacyConfig) (string, error) {
	body := map[string]any{
		"query": query,
		"limit": promptSearchLimit(),
	}
	userID, ok := scrubSearchIdentifier(memoryUserID(), cfg)
	if !ok {
		return "", nil
	}
	agentID, ok := scrubSearchIdentifier(strings.TrimSpace(os.Getenv("POWERMEM_AGENT_ID")), cfg)
	if !ok {
		return "", nil
	}
	if userID != "" {
		body["user_id"] = userID
	}
	if agentID != "" {
		body["agent_id"] = agentID
	}
	respBody, err := postJSON(baseURL()+"/api/v1/memories/search", body, searchTimeout())
	if err != nil {
		return "", err
	}
	return formatSearchResults(respBody)
}

func postMemory(content string, meta map[string]any, runID *string, infer bool) error {
	cfg := loadHookPrivacyConfig()
	userID := memoryUserID()
	agentID := strings.TrimSpace(os.Getenv("POWERMEM_AGENT_ID"))
	runIDValue := ""
	if runID != nil {
		runIDValue = *runID
	}
	if cfg.Enabled {
		var report scrubReport
		userID, report = scrubMetadataString("user_id", userID, cfg)
		if shouldBlockWrite(cfg, report) {
			return nil
		}
		agentID, report = scrubMetadataString("agent_id", agentID, cfg)
		if shouldBlockWrite(cfg, report) {
			return nil
		}
		runIDValue, report = scrubMetadataString("run_id", runIDValue, cfg)
		if shouldBlockWrite(cfg, report) {
			return nil
		}
	}
	content, meta, blocked := scrubMemoryPayload(content, meta, cfg)
	if blocked {
		return nil
	}
	body := map[string]any{
		"content":  content,
		"infer":    infer,
		"metadata": meta,
	}
	if userID != "" {
		body["user_id"] = userID
	}
	if agentID != "" {
		body["agent_id"] = agentID
	}
	if runIDValue != "" {
		body["run_id"] = runIDValue
	}
	_, err := postJSON(baseURL()+"/api/v1/memories", body, saveTimeout())
	return err
}

func postJSON(url string, body map[string]any, timeout time.Duration) ([]byte, error) {
	b, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json; charset=utf-8")
	if k := strings.TrimSpace(os.Getenv("POWERMEM_API_KEY")); k != "" {
		req.Header.Set("X-API-Key", k)
	}
	resp, err := (&http.Client{Timeout: timeout}).Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("http %d", resp.StatusCode)
	}
	return respBody, nil
}

func formatSearchResults(respBody []byte) (string, error) {
	var root map[string]any
	if err := json.Unmarshal(respBody, &root); err != nil {
		return "", err
	}
	results := searchResultsFromResponse(root)
	if len(results) == 0 {
		return "", nil
	}
	var b strings.Builder
	b.WriteString("## PowerMem (retrieved for this prompt)\n\n")
	b.WriteString("Relevant long-term memories from PowerMem; use them only if they help answer the user.\n\n")
	written := 0
	for _, result := range results {
		m, ok := result.(map[string]any)
		if !ok {
			continue
		}
		content := strings.TrimSpace(stringField(m, "content"))
		if content == "" || shouldSkipSearchResult(m, content) {
			continue
		}
		written++
		b.WriteString(fmt.Sprintf("### Memory %d", written))
		if score, ok := m["score"].(float64); ok && score > 0 {
			b.WriteString(fmt.Sprintf(" (score %.2f)", score))
		}
		b.WriteString("\n\n")
		b.WriteString(content)
		b.WriteString("\n\n")
	}
	out := strings.TrimSpace(b.String())
	if written == 0 {
		return "", nil
	}
	return out, nil
}

func shouldSkipSearchResult(result map[string]any, content string) bool {
	if boolEnvDefault("POWERMEM_INCLUDE_RAW_CODEX_STOP_SUMMARIES", false) {
		return false
	}
	if !strings.HasPrefix(strings.TrimSpace(content), "Codex turn summary (") {
		return false
	}
	meta, _ := result["metadata"].(map[string]any)
	if meta == nil {
		return true
	}
	return stringField(meta, "source") == "codex-hook" || stringField(meta, "kind") == "codex-stop-summary"
}

func searchResultsFromResponse(root map[string]any) []any {
	if results, ok := root["results"].([]any); ok {
		return results
	}
	data, _ := root["data"].(map[string]any)
	if data == nil {
		return nil
	}
	if results, ok := data["results"].([]any); ok {
		return results
	}
	return nil
}

func scrubPromptForSearch(prompt string, cfg hookPrivacyConfig) (string, bool) {
	if !cfg.Enabled {
		return prompt, strings.TrimSpace(prompt) != ""
	}
	scrubbed, report := scrubText(prompt, cfg)
	if cfg.SearchSecretPolicy == "off" {
		scrubbed, report = scrubTextWithoutSecretRedaction(prompt, cfg)
	}
	if cfg.SearchSecretPolicy == "skip" && report.SecretRedactions > 0 {
		return "", false
	}
	if strings.TrimSpace(scrubbed) == "" {
		return "", false
	}
	return scrubbed, true
}

func scrubSearchIdentifier(value string, cfg hookPrivacyConfig) (string, bool) {
	if strings.TrimSpace(value) == "" {
		return "", true
	}
	if !cfg.Enabled {
		return value, true
	}
	scrubbed, report := scrubMetadataString("search_id", value, cfg)
	if cfg.SearchSecretPolicy == "off" {
		scrubbed, report = scrubTextWithoutSecretRedaction(value, cfg)
	}
	if cfg.SearchSecretPolicy == "skip" && report.SecretRedactions > 0 {
		return "", false
	}
	return scrubbed, true
}

func scrubMemoryPayload(content string, meta map[string]any, cfg hookPrivacyConfig) (string, map[string]any, bool) {
	if !cfg.Enabled {
		return content, cloneMetadata(meta), false
	}
	scrubbedContent, contentReport := scrubText(content, cfg)
	scrubbedMeta, metaReport := scrubMetadata(meta, cfg)
	contentReport.merge(metaReport)
	if shouldBlockWrite(cfg, contentReport) {
		return "", nil, true
	}
	if scrubbedMeta == nil {
		scrubbedMeta = map[string]any{}
	}
	if contentReport.total() > 0 {
		scrubbedMeta["privacy"] = map[string]any{
			"scrubbed":      true,
			"level":         cfg.PrivacyLevel,
			"secret_action": cfg.SecretAction,
			"path_privacy":  cfg.PathPrivacy,
			"redactions": map[string]any{
				"secrets": contentReport.SecretRedactions,
				"pii":     contentReport.PIIRedactions,
				"paths":   contentReport.PathRedactions,
				"total":   contentReport.total(),
			},
		}
	}
	return scrubbedContent, scrubbedMeta, false
}

func scrubMetadata(meta map[string]any, cfg hookPrivacyConfig) (map[string]any, scrubReport) {
	if meta == nil {
		return nil, scrubReport{}
	}
	out := make(map[string]any, len(meta))
	var report scrubReport
	for k, v := range meta {
		scrubbed, itemReport := scrubMetadataValue(k, v, cfg)
		out[k] = scrubbed
		report.merge(itemReport)
	}
	return out, report
}

func scrubMetadataValue(key string, value any, cfg hookPrivacyConfig) (any, scrubReport) {
	switch v := value.(type) {
	case string:
		return scrubMetadataString(key, v, cfg)
	case map[string]any:
		return scrubMetadata(v, cfg)
	case []any:
		out := make([]any, len(v))
		var report scrubReport
		for i, el := range v {
			scrubbed, itemReport := scrubMetadataValue(key, el, cfg)
			out[i] = scrubbed
			report.merge(itemReport)
		}
		return out, report
	default:
		return value, scrubReport{}
	}
}

func scrubMetadataString(key string, value string, cfg hookPrivacyConfig) (string, scrubReport) {
	if !cfg.Enabled || value == "" {
		return value, scrubReport{}
	}
	if isPathMetadataKey(key) {
		scrubbed := applyPathPrivacy(value, cfg)
		if scrubbed != value {
			return scrubbed, scrubReport{PathRedactions: 1}
		}
	}
	return scrubText(value, cfg)
}

func scrubText(input string, cfg hookPrivacyConfig) (string, scrubReport) {
	if !cfg.Enabled || input == "" {
		return input, scrubReport{}
	}
	out := input
	var report scrubReport
	var count int
	out, count = scrubPathsInText(out, cfg)
	report.PathRedactions += count
	out, count = applySecretRedactions(out)
	report.SecretRedactions += count
	if cfg.PrivacyLevel == "strict" {
		out, count = replaceAllWithCount(emailRE, out, redactedPII)
		report.PIIRedactions += count
		out, count = replaceAllStringFuncWithCount(phoneRE, out, func(match string) (string, bool) {
			if countDigits(match) < 10 {
				return match, false
			}
			return redactedPII, true
		})
		report.PIIRedactions += count
	}
	return out, report
}

func scrubTextWithoutSecretRedaction(input string, cfg hookPrivacyConfig) (string, scrubReport) {
	if !cfg.Enabled || input == "" {
		return input, scrubReport{}
	}
	out, pathCount := scrubPathsInText(input, cfg)
	report := scrubReport{PathRedactions: pathCount}
	if cfg.PrivacyLevel == "strict" {
		var count int
		out, count = replaceAllWithCount(emailRE, out, redactedPII)
		report.PIIRedactions += count
		out, count = replaceAllStringFuncWithCount(phoneRE, out, func(match string) (string, bool) {
			if countDigits(match) < 10 {
				return match, false
			}
			return redactedPII, true
		})
		report.PIIRedactions += count
	}
	return out, report
}

func scrubPathsInText(input string, cfg hookPrivacyConfig) (string, int) {
	out := input
	total := 0
	for _, re := range []*regexp.Regexp{unixPathRE, windowsPathRE} {
		out = re.ReplaceAllStringFunc(out, func(match string) string {
			replacement := applyPathPrivacy(match, cfg)
			if replacement != match {
				total++
			}
			return replacement
		})
	}
	return out, total
}

func applySecretRedactions(input string) (string, int) {
	out := input
	total := 0
	var count int
	out, count = replaceAllWithCount(privateKeyRE, out, redactedSecret)
	total += count
	out, count = replaceAllWithCount(envAssignmentRE, out, "$1"+redactedSecret)
	total += count
	out, count = replaceAllWithCount(doubleQuotedKVRE, out, "$1"+redactedSecret+"$2")
	total += count
	out, count = replaceAllWithCount(singleQuotedKVRE, out, "$1"+redactedSecret+"$2")
	total += count
	out, count = replaceAllWithCount(yamlKVRE, out, "$1"+redactedSecret)
	total += count
	out, count = replaceAllWithCount(authHeaderRE, out, "$1"+redactedSecret)
	total += count
	out, count = replaceAllWithCount(bearerTokenRE, out, "$1"+redactedSecret)
	total += count
	out, count = replaceAllWithCount(urlUserinfoRE, out, "$1"+redactedSecret+"@")
	total += count
	out, count = replaceAllWithCount(queryParamRE, out, "$1"+redactedSecret)
	total += count
	out, count = replaceAllWithCount(prefixedTokenRE, out, redactedSecret)
	total += count
	out, count = replaceAllWithCount(jwtRE, out, redactedSecret)
	total += count
	out, count = replaceLongTokensWithCount(out)
	total += count
	return out, total
}

func applyPathPrivacy(value string, cfg hookPrivacyConfig) string {
	switch cfg.PathPrivacy {
	case "full":
		return value
	case "omit":
		return omittedPath
	case "basename":
		return pathBase(value)
	default:
		home := strings.TrimRight(os.Getenv("HOME"), `/\`)
		if home != "" && (value == home || strings.HasPrefix(value, home+"/")) {
			return "~" + strings.TrimPrefix(value, home)
		}
		return pathBase(value)
	}
}

func pathBase(value string) string {
	value = strings.TrimRight(value, `/\`)
	if value == "" {
		return value
	}
	slash := strings.LastIndex(value, "/")
	backslash := strings.LastIndex(value, `\`)
	if backslash > slash {
		slash = backslash
	}
	if slash >= 0 && slash+1 < len(value) {
		return value[slash+1:]
	}
	return filepath.Base(value)
}

func replaceAllWithCount(re *regexp.Regexp, input string, replacement string) (string, int) {
	count := 0
	out := re.ReplaceAllStringFunc(input, func(match string) string {
		if strings.Contains(match, redactedSecret) || strings.Contains(match, redactedPII) || strings.Contains(match, omittedPath) {
			return match
		}
		count++
		return re.ReplaceAllString(match, replacement)
	})
	return out, count
}

func replaceAllStringFuncWithCount(re *regexp.Regexp, input string, fn func(string) (string, bool)) (string, int) {
	count := 0
	out := re.ReplaceAllStringFunc(input, func(match string) string {
		replacement, ok := fn(match)
		if !ok {
			return match
		}
		count++
		return replacement
	})
	return out, count
}

func replaceLongTokensWithCount(input string) (string, int) {
	matches := longTokenRE.FindAllStringIndex(input, -1)
	if len(matches) == 0 {
		return input, 0
	}
	var b strings.Builder
	b.Grow(len(input))
	count := 0
	last := 0
	for _, span := range matches {
		start, end := span[0], span[1]
		match := input[start:end]
		b.WriteString(input[last:start])
		if looksLikeLongToken(match) {
			b.WriteString(redactedSecret)
			count++
		} else {
			b.WriteString(match)
		}
		last = end
	}
	b.WriteString(input[last:])
	return b.String(), count
}

func looksLikeLongToken(value string) bool {
	hasAlpha := false
	hasDigit := false
	for _, r := range value {
		switch {
		case r >= 'A' && r <= 'Z' || r >= 'a' && r <= 'z':
			hasAlpha = true
		case r >= '0' && r <= '9':
			hasDigit = true
		}
	}
	return hasAlpha && hasDigit
}

func countDigits(value string) int {
	count := 0
	for _, r := range value {
		if r >= '0' && r <= '9' {
			count++
		}
	}
	return count
}

func shouldBlockWrite(cfg hookPrivacyConfig, report scrubReport) bool {
	return cfg.Enabled && cfg.SecretAction == "block" && report.SecretRedactions > 0
}

func (r scrubReport) total() int {
	return r.SecretRedactions + r.PIIRedactions + r.PathRedactions
}

func (r *scrubReport) merge(other scrubReport) {
	r.SecretRedactions += other.SecretRedactions
	r.PIIRedactions += other.PIIRedactions
	r.PathRedactions += other.PathRedactions
}

func cloneMetadata(meta map[string]any) map[string]any {
	if meta == nil {
		return nil
	}
	out := make(map[string]any, len(meta))
	for k, v := range meta {
		out[k] = v
	}
	return out
}

func loadHookPrivacyConfig() hookPrivacyConfig {
	cfg := hookPrivacyConfig{
		Enabled:            true,
		PrivacyLevel:       "standard",
		SecretAction:       "redact",
		PathPrivacy:        "home",
		SearchSecretPolicy: "skip",
	}
	switch strings.ToLower(strings.TrimSpace(os.Getenv("POWERMEM_HOOK_SCRUB"))) {
	case "0", "false", "no", "off":
		cfg.Enabled = false
	case "1", "true", "yes", "on", "":
		cfg.Enabled = true
	}
	switch v := strings.ToLower(strings.TrimSpace(os.Getenv("POWERMEM_HOOK_PRIVACY_LEVEL"))); v {
	case "standard", "strict":
		cfg.PrivacyLevel = v
	}
	switch v := strings.ToLower(strings.TrimSpace(os.Getenv("POWERMEM_HOOK_SECRET_ACTION"))); v {
	case "redact", "block":
		cfg.SecretAction = v
	}
	switch v := strings.ToLower(strings.TrimSpace(os.Getenv("POWERMEM_HOOK_PATH_PRIVACY"))); v {
	case "home", "basename", "omit", "full":
		cfg.PathPrivacy = v
	}
	switch v := strings.ToLower(strings.TrimSpace(os.Getenv("POWERMEM_HOOK_SEARCH_SECRET_POLICY"))); v {
	case "skip", "redact", "off":
		cfg.SearchSecretPolicy = v
	}
	return cfg
}

func baseURL() string {
	s := strings.TrimSpace(os.Getenv("POWERMEM_BASE_URL"))
	if s == "" {
		s = defaultPowerMemBaseURL
	}
	return strings.TrimRight(s, "/")
}

func memoryUserID() string {
	if u := strings.TrimSpace(os.Getenv("POWERMEM_USER_ID")); u != "" {
		return u
	}
	if u := os.Getenv("USER"); u != "" {
		return u
	}
	return os.Getenv("USERNAME")
}

func promptSearchLimit() int {
	n := intEnvDefault("POWERMEM_PROMPT_SEARCH_LIMIT", 8)
	if n < 1 {
		return 8
	}
	if n > 30 {
		return 30
	}
	return n
}

func promptSearchMaxContextChars() int {
	n := intEnvDefault("POWERMEM_PROMPT_SEARCH_MAX_CHARS", 24000)
	if n < 500 {
		return 24000
	}
	return n
}

func maxCodexSaveChars() int {
	n := intEnvDefault("POWERMEM_CODEX_SAVE_MAX_CHARS", 16000)
	if n < 500 {
		return 16000
	}
	return n
}

func codexStopSaveEnabled() bool {
	return boolEnvDefault("POWERMEM_CODEX_STOP_SAVE", true)
}

func searchTimeout() time.Duration {
	return secondsEnvDefault("POWERMEM_PROMPT_SEARCH_TIMEOUT_SECONDS", 90)
}

func saveTimeout() time.Duration {
	return secondsEnvDefault("POWERMEM_CODEX_SAVE_TIMEOUT_SECONDS", 20)
}

func secondsEnvDefault(name string, def int) time.Duration {
	n := intEnvDefault(name, def)
	if n < 1 {
		n = def
	}
	return time.Duration(n) * time.Second
}

func intEnvDefault(name string, def int) int {
	raw := strings.TrimSpace(os.Getenv(name))
	if raw == "" {
		return def
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		return def
	}
	return n
}

func boolEnvDefault(name string, def bool) bool {
	if v, ok := boolEnvIfSet(name); ok {
		return v
	}
	return def
}

func boolEnvIfSet(name string) (bool, bool) {
	raw := strings.ToLower(strings.TrimSpace(os.Getenv(name)))
	if raw == "" {
		return false, false
	}
	switch raw {
	case "1", "true", "yes", "on":
		return true, true
	case "0", "false", "no", "off":
		return false, true
	default:
		return false, false
	}
}

func truncateText(s string, maxChars int) string {
	if maxChars <= 0 {
		return s
	}
	runes := []rune(s)
	if len(runes) <= maxChars {
		return s
	}
	return string(runes[:maxChars]) + "\n..."
}

func codexRunID(sessionID string, turnID string) string {
	switch {
	case sessionID != "" && turnID != "":
		return sessionID + ":" + turnID
	case sessionID != "":
		return sessionID
	default:
		return turnID
	}
}

func stringField(m map[string]any, key string) string {
	v, ok := m[key]
	if !ok || v == nil {
		return ""
	}
	switch x := v.(type) {
	case string:
		return x
	default:
		return fmt.Sprint(x)
	}
}

func isPathMetadataKey(key string) bool {
	key = strings.ToLower(key)
	return key == "cwd" ||
		key == "file" ||
		key == "path" ||
		strings.HasSuffix(key, "_path") ||
		strings.HasSuffix(key, "path")
}

var (
	envAssignmentRE  = regexp.MustCompile(`(?im)\b([A-Z0-9_]*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD|PASSWD|AUTH)[A-Z0-9_]*\s*=\s*)("[^"\r\n]{4,}"|'[^'\r\n]{4,}'|[^\s\r\n]{4,})`)
	doubleQuotedKVRE = regexp.MustCompile(`(?im)(["']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|id[_-]?token|token|client[_-]?secret|secret|password|passwd|private[_-]?key)["']?\s*[:=]\s*")[^"\r\n]{4,}(")`)
	singleQuotedKVRE = regexp.MustCompile(`(?im)(["']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|id[_-]?token|token|client[_-]?secret|secret|password|passwd|private[_-]?key)["']?\s*[:=]\s*')[^'\r\n]{4,}(')`)
	yamlKVRE         = regexp.MustCompile(`(?im)^(\s*(?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|id[_-]?token|token|client[_-]?secret|secret|password|passwd|private[_-]?key)\s*:\s*)[^\s#][^\r\n]*`)
	authHeaderRE     = regexp.MustCompile(`(?im)\b(Authorization\s*:\s*(?:Bearer|Basic)\s+)[A-Za-z0-9._~+/=-]{8,}`)
	bearerTokenRE    = regexp.MustCompile(`(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}`)
	urlUserinfoRE    = regexp.MustCompile(`(?i)\b([a-z][a-z0-9+.-]*://)([^/\s@]+@)`)
	queryParamRE     = regexp.MustCompile(`(?i)([?&](?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|id[_-]?token|token|password|passwd|pwd)=)[^&#\s]+`)
	prefixedTokenRE  = regexp.MustCompile(`\b(?:sk-[A-Za-z0-9_-]{20,}|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|ya29\.[A-Za-z0-9._-]{8,}|AKIA[0-9A-Z]{16}|xox[a-z]-[A-Za-z0-9-]{20,}|xapp-[A-Za-z0-9-]{20,})\b`)
	jwtRE            = regexp.MustCompile(`\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b`)
	longTokenRE      = regexp.MustCompile(`\b[A-Za-z0-9][A-Za-z0-9_+-]{39,}\b`)
	emailRE          = regexp.MustCompile(`\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b`)
	phoneRE          = regexp.MustCompile(`(?:\+?\d[\d .()/\-]{8,}\d)`)
	unixPathRE       = regexp.MustCompile(`/(?:Users|home|tmp|var|data|workspace|workspaces|repo|private|mnt|opt|srv|Volumes|nix|usr|etc|media|Applications)(?:/[^\s"'<>()[\]{}]+)+`)
	windowsPathRE    = regexp.MustCompile(`[A-Za-z]:\\[^\s"'<>|]+(?:\\[^\s"'<>|]+)*`)
	privateKeyRE     = regexp.MustCompile(`(?is)-----BEGIN [^-]*` + regexp.QuoteMeta("PRIVATE"+" KEY") + `-----.*?-----END [^-]*` + regexp.QuoteMeta("PRIVATE"+" KEY") + `-----`)
)
