/*
 * api.js: the single fetch wrapper used for every API call.
 * Public endpoints pass { auth: false } so a stale token can never block them.
 */
(function (global) {
  "use strict";

  var BASE = "/api/v1/";
  var refreshing = null;

  function flatten(value) {
    if (value === null || value === undefined) {
      return [];
    }
    if (typeof value === "string") {
      return [value];
    }
    if (Array.isArray(value)) {
      return value.reduce(function (all, item) {
        return all.concat(flatten(item));
      }, []);
    }
    if (typeof value === "object") {
      return Object.keys(value).reduce(function (all, key) {
        return all.concat(flatten(value[key]));
      }, []);
    }
    return [String(value)];
  }

  function describeError(status, data) {
    if (status === 0) {
      return "Cannot reach the server. Check your connection and try again.";
    }
    if (status === 429) {
      return "Too many requests. Please wait a moment and try again.";
    }
    if (status >= 500) {
      return "The server had a problem. Please try again shortly.";
    }
    if (data && typeof data === "object") {
      if (typeof data.detail === "string") {
        return data.detail;
      }
      var messages = flatten(data);
      if (messages.length > 0) {
        return messages[0];
      }
    }
    return "Request failed (" + status + ").";
  }

  function ApiError(status, data) {
    this.name = "ApiError";
    this.status = status;
    this.data = data;
    this.message = describeError(status, data);
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  function buildUrl(path, params) {
    var url = path.charAt(0) === "/" ? path : BASE + path;
    if (!params) {
      return url;
    }
    var query = new URLSearchParams();
    if (params instanceof URLSearchParams) {
      params.forEach(function (value, key) {
        query.append(key, value);
      });
    } else {
      Object.keys(params).forEach(function (key) {
        var value = params[key];
        if (value === undefined || value === null || value === "") {
          return;
        }
        if (Array.isArray(value)) {
          value.forEach(function (item) {
            query.append(key, item);
          });
        } else {
          query.append(key, value);
        }
      });
    }
    var text = query.toString();
    return text ? url + "?" + text : url;
  }

  // Exchanges the refresh token for a new pair. Shared by all requests that fail at once.
  function refreshTokens() {
    if (refreshing) {
      return refreshing;
    }
    var refresh = Auth.getRefresh();
    if (!refresh) {
      return Promise.resolve(false);
    }
    refreshing = fetch(BASE + "auth/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh: refresh }),
    })
      .then(function (response) {
        if (!response.ok) {
          return false;
        }
        return response.json().then(function (data) {
          Auth.setTokens({ access: data.access, refresh: data.refresh || refresh });
          return true;
        });
      })
      .catch(function () {
        return false;
      })
      .then(function (result) {
        refreshing = null;
        return result;
      });
    return refreshing;
  }

  async function request(method, path, options) {
    var opts = options || {};
    var useAuth = opts.auth !== false;
    var url = buildUrl(path, opts.params);

    function send() {
      var headers = { Accept: "application/json" };
      var body;
      if (typeof FormData !== "undefined" && opts.body instanceof FormData) {
        body = opts.body;
      } else if (opts.body !== undefined) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(opts.body);
      }
      var token = Auth.getAccess();
      if (useAuth && token) {
        headers.Authorization = "Bearer " + token;
      }
      return fetch(url, { method: method, headers: headers, body: body });
    }

    var response;
    try {
      response = await send();
    } catch (error) {
      throw new ApiError(0, null);
    }

    if (response.status === 401 && useAuth && Auth.getRefresh()) {
      var refreshed = await refreshTokens();
      if (refreshed) {
        try {
          response = await send();
        } catch (error) {
          throw new ApiError(0, null);
        }
      } else {
        Auth.clear();
        if (!opts.noRedirect) {
          window.location.replace(Auth.loginUrl());
        }
        throw new ApiError(401, { detail: "Your session has expired. Please log in again." });
      }
    }

    var data = null;
    if (response.status !== 204 && response.status !== 205) {
      var type = response.headers.get("content-type") || "";
      if (type.indexOf("application/json") !== -1) {
        try {
          data = await response.json();
        } catch (error) {
          data = null;
        }
      }
    }

    if (!response.ok) {
      throw new ApiError(response.status, data);
    }
    return data;
  }

  global.Api = {
    ApiError: ApiError,
    request: request,
    get: function (path, params, options) {
      return request("GET", path, Object.assign({}, options, { params: params }));
    },
    post: function (path, body, options) {
      return request("POST", path, Object.assign({}, options, { body: body }));
    },
    patch: function (path, body, options) {
      return request("PATCH", path, Object.assign({}, options, { body: body }));
    },
    del: function (path, options) {
      return request("DELETE", path, options || {});
    },
  };
})(window);