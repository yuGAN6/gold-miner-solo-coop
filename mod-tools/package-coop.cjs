const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const u = require('./unpack-flash.cjs');
const work = path.resolve(__dirname, '../mod-work');
const out = path.join(work, 'patched');
fs.mkdirSync(out, {recursive: true});
const hashes = {...u.hashes};
const files = u.opened.names().map(name => {
  let data = u.opened.read(name);
  if (name === 'rf.swf' || name.endsWith('/rf.swf')) {
    data = fs.readFileSync(path.join(work, 'coop-swf', name));
    hashes[name] = crypto.createHash('sha256').update(data).digest('hex');
  }
  return {name, data};
});
const packed = u.pack.encode(files, u.key);
const verify = u.pack.open(packed, u.key);
for (const file of files) {
  if (!verify.read(file.name).equals(file.data)) throw new Error('Pack verification failed: ' + file.name);
}
const patchedMain = u.main.replace(/SWF_SHA_BAKED=(.*?),SWF_PACK_KEY_B64=/,
  'SWF_SHA_BAKED=' + JSON.stringify(hashes) + ',SWF_PACK_KEY_B64=');
if (patchedMain === u.main) throw new Error('Hash table replacement failed');
fs.writeFileSync(path.join(out, 'electron-main.js'), patchedMain);
fs.writeFileSync(path.join(out, 'swf.pack'), packed);
fs.writeFileSync(path.join(work, 'coop-hashes.json'), JSON.stringify(hashes, null, 2));
console.log('Repacked and verified', files.length, 'resources; updated four rf.swf hashes.');
