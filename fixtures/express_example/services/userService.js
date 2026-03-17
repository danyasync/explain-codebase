const { loadUser } = require("../repositories/userRepository");

function findUser(id) {
  return loadUser(id);
}

module.exports = { findUser };
