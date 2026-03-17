const { getUser } = require("../controllers/userController");

module.exports = function userRoutes(app) {
  app.get("/:id", getUser);
};
