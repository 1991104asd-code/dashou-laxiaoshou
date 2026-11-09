// 从 index.html 里读出游戏会说的所有台词，输出 [{ key, text }]，交给 make_voice.py 合成。
// 用法：node tools/voice-lines.js > lines.json
// 台词规则写在 index.html 的 @voice-data 区块里，游戏和这个工具共用同一份规则和 voiceKey()。
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const m = html.match(/\/\* @voice-data:start[^*]*\*\/([\s\S]*?)\/\* @voice-data:end \*\//);
if (!m) { console.error('index.html 里找不到 @voice-data 区块'); process.exit(1); }

const ctx = vm.createContext({});
vm.runInContext(m[1] + '\n;this.out = allVoiceLines().map(t => ({ key: voiceKey(t), text: t }));', ctx);

const keys = new Set();
for (const l of ctx.out) {
  if (keys.has(l.key)) { console.error('台词文件名冲突：' + l.text); process.exit(1); }
  keys.add(l.key);
}
process.stdout.write(JSON.stringify(ctx.out, null, 1) + '\n');
console.error(`共 ${ctx.out.length} 句台词`);
