import type { Plugin } from "@opencode-ai/plugin";

const FILE_TOOLS = new Set(["Read", "Write", "Edit", "Glob", "Grep"]);
const FILE_KEYS = ["filePath", "file_path", "path", "file", "pattern"];
const MAX_TEXT = 8000;
const DEBUG = process.env.OPENCODE_POWERMEM_DEBUG === "1";

let activeSessionId: string | null = null;
let projectPath: string | null = null;
let configuredEnvFile: string | null = null;
const stashedFiles = new Map<string, Set<string>>();
const seenToolCalls = new Map<string, Set<string>>();
const contextInjectedSessions = new Set<string>();

function log(message: string): void {
  if (DEBUG) console.error(`[powermem] ${message}`);
}

function sessionFiles(sessionId: string): Set<string> {
  let files = stashedFiles.get(sessionId);
  if (!files) {
    files = new Set<string>();
    stashedFiles.set(sessionId, files);
  }
  return files;
}

function toolCalls(sessionId: string): Set<string> {
  let calls = seenToolCalls.get(sessionId);
  if (!calls) {
    calls = new Set<string>();
    seenToolCalls.set(sessionId, calls);
  }
  return calls;
}

function safeText(value: unknown, max = MAX_TEXT): string {
  if (typeof value === "string") return value.slice(0, max);
  if (value == null) return "";
  try {
    return JSON.stringify(value).slice(0, max);
  } catch {
    return String(value).slice(0, max);
  }
}

function extractFilePaths(args: Record<string, unknown>): string[] {
  const files: string[] = [];
  for (const key of FILE_KEYS) {
    const value = args[key];
    if (typeof value === "string" && value.length > 0) files.push(value);
  }
  return files;
}

function metadata(event: string, extra: Record<string, unknown> = {}): string {
  return JSON.stringify({
    source: "opencode-plugin",
    event,
    cwd: projectPath || process.cwd(),
    ...extra,
  });
}

async function readPluginEnvFile(ctx: unknown): Promise<string | null> {
  const direct = process.env.POWERMEM_ENV_FILE;
  if (direct && direct.trim()) return direct.trim();

  const pluginConfig = (ctx as any)?.config?.powermem;
  if (pluginConfig && typeof pluginConfig.envFile === "string" && pluginConfig.envFile.trim()) {
    return pluginConfig.envFile.trim();
  }

  const configPath = `${process.env.HOME || ""}/.config/opencode/plugins/powermem-config.json`;
  try {
    const file = Bun.file(configPath);
    if (!(await file.exists())) return null;
    const data = await file.json();
    if (data && typeof data.envFile === "string" && data.envFile.trim()) {
      return data.envFile.trim();
    }
  } catch (error) {
    log(`failed to read plugin config: ${safeText(error, 500)}`);
  }
  return null;
}

function pmemEnv(): Record<string, string> {
  const envFile = configuredEnvFile || process.env.POWERMEM_ENV_FILE || "";
  return {
    ...process.env,
    POWERMEM_ENV_FILE: envFile,
  };
}

async function runPmem(args: string[], timeoutMs = 5000): Promise<void> {
  let proc: ReturnType<typeof Bun.spawn> | null = null;
  const timer = setTimeout(() => {
    try {
      proc?.kill();
    } catch (error) {
      log(`failed to kill timed out pmem: ${safeText(error, 500)}`);
    }
  }, timeoutMs);
  try {
    proc = Bun.spawn(["pmem", ...args], {
      stdout: "ignore",
      stderr: DEBUG ? "inherit" : "ignore",
      env: pmemEnv(),
    });
    await proc.exited;
  } catch (error) {
    log(`pmem failed: ${safeText(error, 500)}`);
  } finally {
    clearTimeout(timer);
  }
}

async function addMemory(
  event: string,
  sessionId: string,
  content: string,
  extra: Record<string, unknown> = {},
): Promise<void> {
  const text = content.trim();
  if (!text) return;
  await runPmem([
    "memory",
    "add",
    text,
    "--agent-id",
    "opencode",
    "--run-id",
    sessionId,
    "--metadata",
    metadata(event, extra),
    "--memory-type",
    "short_term",
    "--no-infer",
  ]);
}

async function recallContext(query: string): Promise<string | null> {
  const proc = Bun.spawn(
    ["pmem", "memory", "search", query, "--agent-id", "opencode", "--limit", "5", "--json"],
    {
      stdout: "pipe",
      stderr: DEBUG ? "inherit" : "ignore",
      env: pmemEnv(),
    },
  );
  const output = await new Response(proc.stdout).text();
  await proc.exited;
  const text = output.trim();
  if (!text || text === "[]" || text === "{}") return null;
  return text.slice(0, 6000);
}

export const PowerMemCapturePlugin: Plugin = async (ctx) => {
  projectPath = ctx.worktree || ctx.project?.id || process.cwd();
  configuredEnvFile = await readPluginEnvFile(ctx);

  return {
    event: async ({ event }) => {
      const type = event.type;
      const props = (event as any).properties || {};

      if (type === "session.created") {
        const info = props.info as Record<string, unknown> | undefined;
        const sessionId = String(info?.id || props.sessionID || Date.now());
        activeSessionId = sessionId;
        await addMemory("session.created", sessionId, `OpenCode session started in ${projectPath}.`, {
          model: info?.model,
        });
        return;
      }

      const sessionId = String(
        props.sessionID || props.sessionId || activeSessionId || Date.now(),
      );

      if (type === "chat.message") {
        await addMemory("chat.message", sessionId, `OpenCode user prompt:\n\n${safeText(props)}`);
        return;
      }

      if (type === "tool.execute.before") {
        const tool = String(props.tool || props.name || "");
        const args = (props.args || props.parameters || {}) as Record<string, unknown>;
        if (FILE_TOOLS.has(tool)) {
          for (const file of extractFilePaths(args)) sessionFiles(sessionId).add(file);
        }
        await addMemory("tool.execute.before", sessionId, `OpenCode tool start: ${tool}\n\n${safeText(args)}`, {
          tool,
        });
        return;
      }

      if (type === "message.part.updated") {
        const part = props.part as Record<string, unknown> | undefined;
        const partType = String(part?.type || "");
        const callId = String(part?.id || part?.callID || "");
        if (callId) {
          const calls = toolCalls(sessionId);
          if (calls.has(callId)) return;
          calls.add(callId);
        }
        if (partType === "tool") {
          await addMemory("message.part.updated", sessionId, `OpenCode tool update:\n\n${safeText(part)}`);
        } else if (partType === "file") {
          const path = String(part?.path || "");
          if (path) sessionFiles(sessionId).add(path);
        } else if (["patch", "reasoning", "compaction", "step-finish", "subtask"].includes(partType)) {
          await addMemory(`message.part.${partType}`, sessionId, safeText(part));
        }
        return;
      }

      if (type === "file.edited") {
        const path = String(props.path || props.file || "");
        if (path) sessionFiles(sessionId).add(path);
        await addMemory("file.edited", sessionId, `OpenCode edited file: ${path}`);
        return;
      }

      if (
        [
          "session.idle",
          "session.status",
          "session.compacted",
          "session.updated",
          "session.diff",
          "session.deleted",
          "session.error",
          "message.updated",
          "message.removed",
          "permission.updated",
          "permission.replied",
          "todo.updated",
          "command.executed",
          "chat.params",
          "config",
        ].includes(type)
      ) {
        await addMemory(type, sessionId, `OpenCode event ${type}:\n\n${safeText(props)}`);
      }
    },

    "experimental.chat.system.transform": async ({ sessionID, system }) => {
      if (contextInjectedSessions.has(sessionID)) return { system };
      contextInjectedSessions.add(sessionID);
      const query = `${projectPath || ""} recent context`;
      const context = await recallContext(query);
      if (!context) return { system };
      return {
        system: [
          ...system,
          {
            type: "text",
            text: `PowerMem recalled context. Use only when relevant:\n\n${context}`,
          },
        ],
      };
    },
  };
};

export default PowerMemCapturePlugin;
