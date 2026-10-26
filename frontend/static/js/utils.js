/*
 * utils.js: small helpers shared by every page script.
 * Loaded first, so it must not depend on any other script.
 */
(function (global) {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";

  // ---------- DOM helpers ----------
  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function clear(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  // Builds an element. options: className, text, attrs. children: nodes or strings.
  function el(tag, options, children) {
    var node = document.createElement(tag);
    var opts = options || {};
    if (opts.className) {
      node.className = opts.className;
    }
    if (opts.text !== undefined && opts.text !== null) {
      node.textContent = String(opts.text);
    }
    if (opts.attrs) {
      Object.keys(opts.attrs).forEach(function (name) {
        var value = opts.attrs[name];
        if (value !== undefined && value !== null && value !== false) {
          node.setAttribute(name, value === true ? "" : value);
        }
      });
    }
    (children || []).forEach(function (child) {
      if (child === null || child === undefined || child === false) {
        return;
      }
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  // Creates an <svg> that points at a symbol in the sprite defined in base.html.
  function icon(name, className) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", "icon" + (className ? " " + className : ""));
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS(SVG_NS, "use");
    use.setAttribute("href", "#i-" + name);
    svg.appendChild(use);
    return svg;
  }

  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var args = arguments;
      var context = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(context, args);
      }, delay || 350);
    };
  }

  // ---------- Dates ----------
  function parseDate(value) {
    if (!value) {
      return null;
    }
    var dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (dateOnly) {
      return new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]));
    }
    var parsed = new Date(value);
    return isNaN(parsed.getTime()) ? null : parsed;
  }

  function formatDate(value) {
    var date = parseDate(value);
    return date ? date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
  }

  function formatDateTime(value) {
    var date = parseDate(value);
    return date
      ? date.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
      : "";
  }

  function daysUntil(value) {
    var date = parseDate(value);
    if (!date) {
      return null;
    }
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    return Math.round((target.getTime() - today.getTime()) / 86400000);
  }

  function timeAgo(value) {
    var date = parseDate(value);
    if (!date) {
      return "";
    }
    var seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) {
      return "just now";
    }
    var minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
      return minutes + (minutes === 1 ? " minute ago" : " minutes ago");
    }
    var hours = Math.floor(minutes / 60);
    if (hours < 24) {
      return hours + (hours === 1 ? " hour ago" : " hours ago");
    }
    var days = Math.floor(hours / 24);
    if (days < 30) {
      return days + (days === 1 ? " day ago" : " days ago");
    }
    return formatDate(value);
  }

  function deadlineInfo(deadline) {
    var days = daysUntil(deadline);
    if (days === null) {
      return { text: "No deadline", level: "none" };
    }
    if (days < 0) {
      return { text: "Closed", level: "past" };
    }
    if (days === 0) {
      return { text: "Closes today", level: "urgent" };
    }
    if (days === 1) {
      return { text: "Closes tomorrow", level: "urgent" };
    }
    if (days <= 3) {
      return { text: "Closes in " + days + " days", level: "urgent" };
    }
    return { text: "Closes in " + days + " days", level: "normal" };
  }

  // ---------- Text helpers ----------
  function initials(name) {
    var parts = String(name || "").trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) {
      return "?";
    }
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  // Picks one of 8 gradient colours deterministically from a name.
  function avatarClass(name) {
    var text = String(name || "");
    var hash = 0;
    for (var i = 0; i < text.length; i += 1) {
      hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
    }
    return "avatar--" + (hash % 8);
  }

  function formatNumber(value) {
    return Number(value).toLocaleString("en-US");
  }

  // Returns the URL only when it is a normal http(s) link, otherwise null.
  function safeUrl(url) {
    if (!url) {
      return null;
    }
    try {
      var parsed = new URL(url, window.location.origin);
      return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
    } catch (error) {
      return null;
    }
  }

  // ---------- Notifications ----------
  function toast(message, type) {
    var container = document.getElementById("toast-container");
    if (!container) {
      return;
    }
    var node = el("div", { className: "toast toast--" + (type || "info"), text: message, attrs: { role: "status" } });
    container.appendChild(node);
    setTimeout(function () {
      node.classList.add("is-leaving");
      setTimeout(function () {
        if (node.parentNode) {
          node.parentNode.removeChild(node);
        }
      }, 300);
    }, 4000);
  }

  // ---------- Forms ----------
  function flattenMessages(value) {
    if (value === null || value === undefined) {
      return [];
    }
    if (typeof value === "string") {
      return [value];
    }
    if (Array.isArray(value)) {
      return value.reduce(function (all, item) {
        return all.concat(flattenMessages(item));
      }, []);
    }
    if (typeof value === "object") {
      return Object.keys(value).reduce(function (all, key) {
        return all.concat(flattenMessages(value[key]));
      }, []);
    }
    return [String(value)];
  }

  function clearFormErrors(form) {
    qsa("[data-error-for]", form).forEach(function (node) {
      node.textContent = "";
    });
    qsa(".is-invalid", form).forEach(function (node) {
      node.classList.remove("is-invalid");
    });
    var banner = qs("[data-form-error]", form);
    if (banner) {
      banner.hidden = true;
      banner.textContent = "";
    }
  }

  // Shows API validation errors next to the matching fields, and a banner above the form.
  function showFormErrors(form, error) {
    clearFormErrors(form);
    var data = error && error.data;
    var general = (error && error.message) || "Something went wrong. Please try again.";
    var matched = false;

    if (data && typeof data === "object" && !Array.isArray(data)) {
      Object.keys(data).forEach(function (field) {
        var slot = form.querySelector('[data-error-for="' + field + '"]');
        if (!slot) {
          return;
        }
        slot.textContent = flattenMessages(data[field]).join(" ");
        matched = true;
        var control = form.elements.namedItem(field);
        if (control && control.classList) {
          control.classList.add("is-invalid");
        }
      });
    }
    if (matched) {
      general = "Please fix the highlighted fields.";
    }

    var banner = qs("[data-form-error]", form);
    if (banner) {
      banner.textContent = general;
      banner.hidden = false;
    }
  }

  function setLoading(button, loading, loadingText) {
    if (!button) {
      return;
    }
    if (loading) {
      button.dataset.label = button.textContent;
      button.disabled = true;
      button.classList.add("is-loading");
      if (loadingText) {
        button.textContent = loadingText;
      }
    } else {
      button.disabled = false;
      button.classList.remove("is-loading");
      if (button.dataset.label !== undefined) {
        button.textContent = button.dataset.label;
        delete button.dataset.label;
      }
    }
  }

  // ---------- URL ----------
  function getParams() {
    return new URLSearchParams(window.location.search);
  }

  function replaceUrlParams(params) {
    var query = params.toString();
    window.history.replaceState({}, "", window.location.pathname + (query ? "?" + query : ""));
  }

  // ---------- Pagination ----------
  function pageNumbers(current, total) {
    var wanted = [1, total, current - 1, current, current + 1].filter(function (n) {
      return n >= 1 && n <= total;
    });
    var unique = wanted.filter(function (n, index) {
      return wanted.indexOf(n) === index;
    });
    unique.sort(function (a, b) {
      return a - b;
    });
    var output = [];
    var previous = 0;
    unique.forEach(function (n) {
      if (n - previous > 1) {
        output.push("...");
      }
      output.push(n);
      previous = n;
    });
    return output;
  }

  // state: { page, totalPages }. onChange receives the new page number.
  function renderPagination(nav, state, onChange) {
    if (!nav) {
      return;
    }
    if (!state.totalPages || state.totalPages <= 1) {
      nav.hidden = true;
      return;
    }
    nav.hidden = false;
    var prev = qs('[data-page="prev"]', nav);
    var next = qs('[data-page="next"]', nav);
    var pages = qs("[data-pages]", nav);

    prev.disabled = state.page <= 1;
    next.disabled = state.page >= state.totalPages;
    prev.onclick = function () {
      onChange(state.page - 1);
    };
    next.onclick = function () {
      onChange(state.page + 1);
    };

    clear(pages);
    pageNumbers(state.page, state.totalPages).forEach(function (item) {
      if (item === "...") {
        pages.appendChild(el("span", { className: "pagination__gap", text: "..." }));
        return;
      }
      var button = el("button", {
        className: "pagination__page" + (item === state.page ? " is-active" : ""),
        text: item,
        attrs: { type: "button", "aria-label": "Page " + item },
      });
      if (item === state.page) {
        button.setAttribute("aria-current", "page");
      }
      button.addEventListener("click", function () {
        onChange(item);
      });
      pages.appendChild(button);
    });
  }

  // ---------- Page behaviour that every page needs ----------
  function initNavbar() {
    var toggle = qs("[data-nav-toggle]");
    var menu = qs("[data-nav-menu]");
    if (!toggle || !menu) {
      return;
    }
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("is-open");
      toggle.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  document.addEventListener("DOMContentLoaded", initNavbar);

  // "Show / Hide" buttons next to password fields.
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-toggle-password]");
    if (!button) {
      return;
    }
    var input = button.parentElement.querySelector("input");
    if (!input) {
      return;
    }
    var show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "Hide" : "Show";
  });

  global.Utils = {
    qs: qs,
    qsa: qsa,
    clear: clear,
    el: el,
    icon: icon,
    debounce: debounce,
    parseDate: parseDate,
    formatDate: formatDate,
    formatDateTime: formatDateTime,
    daysUntil: daysUntil,
    timeAgo: timeAgo,
    deadlineInfo: deadlineInfo,
    initials: initials,
    avatarClass: avatarClass,
    formatNumber: formatNumber,
    safeUrl: safeUrl,
    toast: toast,
    clearFormErrors: clearFormErrors,
    showFormErrors: showFormErrors,
    setLoading: setLoading,
    getParams: getParams,
    replaceUrlParams: replaceUrlParams,
    renderPagination: renderPagination,
  };
})(window);