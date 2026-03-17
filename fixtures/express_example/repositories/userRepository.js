const fs = require("fs");

function loadUser(id) {
  return { id, source: fs.readFileSync("users.json", "utf-8") };
}

module.exports = { loadUser };
