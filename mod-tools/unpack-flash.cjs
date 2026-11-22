const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '../mod-work/original-app');
const main = fs.readFileSync(path.join(root, 'electron-main.js'), 'utf8');

function functionSource(source, name) {
  const start = source.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('Missing function ' + name);
  let i = source.indexOf('{', start), depth = 0, quote = null;
  for (; i < source.length; i++) {
    const c = source[i];
    if (quote) { if (c === '\\') i++; else if (c === quote) quote = null; }
    else if (c === "'" || c === '"' || c === '`') quote = c;
    else if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error('Unbalanced function');
}

const context = vm.createContext({});
const functions = ['gmc981b0_t','gmc981b0_Y','gmc981b0_m','gmc981b0_n'];
const bootstrap = main.slice(main.indexOf('(function'), main.indexOf('const {app,'));
vm.runInContext(functions.map(n => functionSource(main, n)).join('\n') + '\n' + bootstrap, context, {timeout: 5000});
const keyExpression = main.match(/SWF_PACK_KEY_B64=(.*?),__GMT_DIAG_KEY_B64__/)[1];
const key = Buffer.from(vm.runInContext(keyExpression, context), 'base64');
const hashes = vm.runInContext('(' + main.match(/SWF_SHA_BAKED=(.*?),SWF_PACK_KEY_B64=/)[1] + ')', context);
const pack = require(path.join(root, 'main/swf-pack.js'));
const opened = pack.open(fs.readFileSync(path.join(root, 'swf.pack')), key);
console.log('Pack API:', Object.keys(pack), 'Opened API:', Object.keys(opened));
fs.writeFileSync(path.resolve(__dirname, '../mod-work/original-hashes.json'), JSON.stringify(hashes, null, 2));
module.exports = {root, main, key, hashes, pack, opened, context, functionSource};
