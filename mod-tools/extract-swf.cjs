const fs = require('fs');
const path = require('path');
const {opened} = require('./unpack-flash.cjs');
for (const name of opened.names()) {
  if (!name.endsWith('.swf')) continue;
  const output = path.resolve(__dirname, '../mod-work/swf', name);
  fs.mkdirSync(path.dirname(output), {recursive:true});
  fs.writeFileSync(output, opened.read(name));
  console.log(name);
}
