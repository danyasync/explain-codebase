const { findUser } = require("../services/userService");

function getUser(req, res) {
  res.json(findUser(req.params.id));
}

module.exports = { getUser };
