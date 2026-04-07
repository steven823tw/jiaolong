// jiaolong-memory hook - 每次消息前注入相关记忆
const { execSync } = require('child_process');
const path = require('path');

module.exports = async function({ message }) {
  if (!message || message.trim().length < 2) return {};
  if (message.trim().startsWith('/')) return {};

  try {
    const hookScript = path.join(process.env.HOME || '/root', '.openclaw/workspace/evolution_framework/hooks/memory_inject_hook.py');
    const input = JSON.stringify({ message, max_memories: 5 });
    const result = execSync(`echo '${input.replace(/'/g, "'\\''")}' | python3 ${hookScript}`, {
      encoding: 'utf-8',
      timeout: 10000
    });
    const parsed = JSON.parse(result.trim());
    if (parsed.success && parsed.context) {
      return { inject: parsed.context };
    }
  } catch (e) {
    // Silent fail - don't block conversation
  }
  return {};
};
