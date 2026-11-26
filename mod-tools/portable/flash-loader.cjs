/* GOLDMINER_COOP_LOADER_BEGIN */
(function () {
  const fs = require('fs');
  const path = require('path');
  const crypto = require('crypto');
  const originalOpen = module.exports.open;
  const directory = path.join(process.resourcesPath || path.resolve(__dirname, '../..'), 'goldminer-solo-coop');
  const supported = new Set(['rf.swf', 'l10n-cjk/rf.swf', 'l10n-latin/rf.swf', 'l10n-pad/rf.swf']);
  module.exports.open = function () {
    const pack = originalOpen.apply(this, arguments);
    function override(name) {
      if (!supported.has(name)) return null;
      const file = path.join(directory, name);
      return fs.existsSync(file) ? fs.readFileSync(file) : null;
    }
    return Object.assign({}, pack, {
      read: function (name) { return override(name) || pack.read(name); },
      sha256: function (name) {
        const bytes = override(name);
        return bytes ? crypto.createHash('sha256').update(bytes).digest('hex') : pack.sha256(name);
      }
    });
  };
}());
/* GOLDMINER_COOP_LOADER_END */
