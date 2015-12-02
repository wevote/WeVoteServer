var fs = require("fs");
var path = require("path");
var html = fs.readFileSync(path.resolve(__dirname, "../app/index.html"), "utf-8");

function AppREnderer(options) {
  this.html = html.replace("SCRIPT_URL", options.scriptUrl);
}

AppREnderer.prototype.render = function(_path, _readItems, callback) {
  callback(null, this.html);
};

module.exports = AppREnderer;
