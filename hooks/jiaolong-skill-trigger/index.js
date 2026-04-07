// jiaolong-skill-trigger hook - 自动检测Skill触发词
const { execSync } = require('child_process');
const path = require('path');

module.exports = async function({ message }) {
  if (!message || message.trim().length < 2) return {};

  try {
    const triggerScript = path.join(process.env.HOME || '/root', '.openclaw/workspace/evolution_framework/skill_trigger.py');
    const input = JSON.stringify({ message });
    const result = execSync(`echo '${input.replace(/'/g, "'\\''")}' | python3 ${triggerScript}`, {
      encoding: 'utf-8',
      timeout: 5000
    });
    const parsed = JSON.parse(result.trim());
    if (parsed.success && parsed.skill) {
      return { trigger: parsed.skill, reason: parsed.reason };
    }
  } catch (e) {
    // Silent fail
  }
  return {};
};
