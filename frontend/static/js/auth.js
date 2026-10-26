/*
 * auth.js: token storage, login state, and the login / register pages.
 * Needs Utils (utils.js) and Api (api.js) at call time.
 */
(function (global) {
  "use strict";

  var KEYS = { access: "kjp_access", refresh: "kjp_refresh", user: "kjp_user" };

  function read(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function write(key, value) {
    try {
      if (value === null || value === undefined) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    } catch (error) {
      /* storage can be blocked (private mode); the user simply stays logged out */
    }
  }

  var Auth = {
    getAccess: function () {
      return read(KEYS.access);
    },

    getRefresh: function () {
      return read(KEYS.refresh);
    },

    setTokens: function (tokens) {
      if (tokens.access) {
        write(KEYS.access, tokens.access);
      }
      if (tokens.refresh) {
        write(KEYS.refresh, tokens.refresh);
      }
    },

    getUser: function () {
      var raw = read(KEYS.user);
      if (!raw) {
        return null;
      }
      try {
        return JSON.parse(raw);
      } catch (error) {
        return null;
      }
    },

    setUser: function (user) {
      write(KEYS.user, user ? JSON.stringify(user) : null);
      Auth.syncNavbar();
    },

    clear: function () {
      write(KEYS.access, null);
      write(KEYS.refresh, null);
      write(KEYS.user, null);
    },

    isLoggedIn: function () {
      return Boolean(Auth.getRefresh());
    },

    // Only allow redirects to paths on this site (blocks open-redirect links).
    safeNext: function (value) {
      if (!value || typeof value !== "string") {
        return null;
      }
      if (value.charAt(0) !== "/" || value.charAt(1) === "/" || value.charAt(1) === "\\") {
        return null;
      }
      return value;
    },

    loginUrl: function () {
      return "/login/?next=" + encodeURIComponent(window.location.pathname + window.location.search);
    },

    requireLogin: function () {
      if (!Auth.isLoggedIn()) {
        window.location.replace(Auth.loginUrl());
        return false;
      }
      return true;
    },

    redirectIfLoggedIn: function () {
      if (Auth.isLoggedIn()) {
        window.location.replace(Auth.safeNext(Utils.getParams().get("next")) || "/dashboard/");
        return true;
      }
      return false;
    },

    login: async function (identifier, password) {
      var data = await Api.post("auth/login/", { username: identifier, password: password }, { auth: false });
      Auth.setTokens({ access: data.access, refresh: data.refresh });
      Auth.setUser(data.user);
      return data.user;
    },

    logout: async function () {
      var refresh = Auth.getRefresh();
      try {
        if (refresh) {
          await Api.post("auth/logout/", { refresh: refresh }, { noRedirect: true });
        }
      } catch (error) {
        /* log out locally even if the server call fails */
      }
      Auth.clear();
      window.location.href = "/";
    },

    // Updates the menu: guest or user links, the user's name and initials.
    syncNavbar: function () {
      document.documentElement.setAttribute("data-auth", Auth.isLoggedIn() ? "user" : "guest");
      var user = Auth.getUser();
      var shortName = user ? user.first_name || user.username : "Account";
      var fullName = user ? [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username : "U";
      Utils.qsa("[data-user-name]").forEach(function (node) {
        node.textContent = shortName;
      });
      Utils.qsa("[data-user-initials]").forEach(function (node) {
        node.textContent = Utils.initials(fullName);
      });
    },

    // If we hold tokens but no cached user (for example after a restart), fetch it once.
    ensureUser: async function () {
      if (!Auth.isLoggedIn() || Auth.getUser()) {
        return;
      }
      try {
        var user = await Api.get("auth/me/", null, { noRedirect: true });
        Auth.setUser(user);
      } catch (error) {
        Auth.syncNavbar();
      }
    },

    initLoginPage: function () {
      if (Auth.redirectIfLoggedIn()) {
        return;
      }
      var form = Utils.qs("#login-form");
      if (!form) {
        return;
      }
      form.addEventListener("submit", async function (event) {
        event.preventDefault();
        Utils.clearFormErrors(form);
        var button = Utils.qs('button[type="submit"]', form);
        var identifier = form.elements.namedItem("username").value.trim();
        var password = form.elements.namedItem("password").value;

        if (!identifier || !password) {
          Utils.showFormErrors(form, { message: "Enter your username (or email) and your password." });
          return;
        }

        Utils.setLoading(button, true, "Logging in...");
        try {
          await Auth.login(identifier, password);
          window.location.href = Auth.safeNext(Utils.getParams().get("next")) || "/dashboard/";
        } catch (error) {
          Utils.showFormErrors(form, error);
          Utils.setLoading(button, false);
        }
      });
    },

    initRegisterPage: function () {
      if (Auth.redirectIfLoggedIn()) {
        return;
      }
      var form = Utils.qs("#register-form");
      if (!form) {
        return;
      }
      form.addEventListener("submit", async function (event) {
        event.preventDefault();
        Utils.clearFormErrors(form);
        var button = Utils.qs('button[type="submit"]', form);

        var payload = {
          username: form.elements.namedItem("username").value.trim(),
          email: form.elements.namedItem("email").value.trim(),
          password: form.elements.namedItem("password").value,
          password_confirm: form.elements.namedItem("password_confirm").value,
          role: "job_seeker",
        };
        var firstName = form.elements.namedItem("first_name").value.trim();
        var lastName = form.elements.namedItem("last_name").value.trim();
        if (firstName) {
          payload.first_name = firstName;
        }
        if (lastName) {
          payload.last_name = lastName;
        }

        if (payload.password !== payload.password_confirm) {
          Utils.showFormErrors(form, {
            message: "Passwords do not match.",
            data: { password_confirm: ["Passwords do not match."] },
          });
          return;
        }

        Utils.setLoading(button, true, "Creating account...");
        try {
          await Api.post("auth/register/", payload, { auth: false });
          await Auth.login(payload.username, payload.password);
          window.location.href = Auth.safeNext(Utils.getParams().get("next")) || "/dashboard/";
        } catch (error) {
          Utils.showFormErrors(form, error);
          Utils.setLoading(button, false);
        }
      });
    },
  };

  document.addEventListener("click", function (event) {
    var button = event.target.closest('[data-action="logout"]');
    if (button) {
      event.preventDefault();
      Auth.logout();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    Auth.syncNavbar();
    Auth.ensureUser();
  });

  global.Auth = Auth;
})(window);