/*
 * alerts.js: create, pause and delete job alerts.
 */
(function (global) {
  "use strict";

  var qs = Utils.qs;
  var qsa = Utils.qsa;
  var el = Utils.el;
  var clear = Utils.clear;
  var icon = Utils.icon;

  function fillSelect(select, options, labels) {
    (options || []).forEach(function (option) {
      select.appendChild(el("option", { text: option.label, attrs: { value: option.value } }));
      labels[option.value] = option.label;
    });
  }

  function buildPayload(form) {
    function value(name) {
      return form.elements.namedItem(name).value.trim();
    }
    var payload = { name: value("name"), frequency: value("frequency") };
    ["query", "county", "job_type", "work_mode", "experience_level"].forEach(function (key) {
      if (value(key)) {
        payload[key] = value(key);
      }
    });
    var skills = value("skills")
      .split(",")
      .map(function (part) {
        return part.trim();
      })
      .filter(Boolean);
    if (skills.length > 0) {
      payload.skills = skills;
    }
    var salary = parseInt(value("min_salary"), 10);
    if (salary > 0) {
      payload.min_salary = salary;
    }
    return payload;
  }

  async function initAlerts() {
    if (!Auth.requireLogin()) {
      return;
    }
    var form = qs("#alert-form");
    var listEl = qs("#alerts-list");
    var emptyEl = qs("#alerts-empty");
    var errorEl = qs("#alerts-error");
    var labels = { county: {}, job_type: {}, work_mode: {}, experience_level: {} };

    try {
      var meta = await Api.get("meta/", null, { auth: false });
      fillSelect(form.elements.namedItem("county"), meta.counties, labels.county);
      fillSelect(form.elements.namedItem("job_type"), meta.job_types, labels.job_type);
      fillSelect(form.elements.namedItem("work_mode"), meta.work_modes, labels.work_mode);
      fillSelect(form.elements.namedItem("experience_level"), meta.experience_levels, labels.experience_level);
    } catch (error) {
      /* the selects stay on "Any"; saved alerts still show their raw values */
    }

    function label(group, value) {
      return labels[group][value] || value;
    }

    function criteria(alert) {
      var chips = [];
      if (alert.query) {
        chips.push("Keywords: " + alert.query);
      }
      if (alert.county) {
        chips.push("County: " + label("county", alert.county));
      }
      if (alert.job_type) {
        chips.push("Type: " + label("job_type", alert.job_type));
      }
      if (alert.work_mode) {
        chips.push("Mode: " + label("work_mode", alert.work_mode));
      }
      if (alert.experience_level) {
        chips.push("Level: " + label("experience_level", alert.experience_level));
      }
      if (alert.skills && alert.skills.length > 0) {
        chips.push("Skills: " + alert.skills.join(", "));
      }
      if (alert.min_salary) {
        chips.push("Min salary: KES " + Utils.formatNumber(alert.min_salary));
      }
      return chips;
    }

    function renderAlert(alert) {
      var url = "alerts/" + alert.id + "/";

      var checkbox = el("input", { attrs: { type: "checkbox", "aria-label": "Alert active" } });
      checkbox.checked = alert.is_active;
      var toggle = el("label", { className: "switch" }, [
        checkbox,
        el("span", { className: "switch__track" }),
        el("span", { className: "sr-only", text: "Active" }),
      ]);

      var card = el("article", { className: "alert-card" + (alert.is_active ? "" : " is-paused") });

      checkbox.addEventListener("change", async function () {
        checkbox.disabled = true;
        try {
          var updated = await Api.patch(url, { is_active: checkbox.checked });
          card.classList.toggle("is-paused", !updated.is_active);
          Utils.toast(updated.is_active ? "Alert resumed." : "Alert paused.", "success");
        } catch (error) {
          checkbox.checked = !checkbox.checked;
          Utils.toast(error.message, "error");
        } finally {
          checkbox.disabled = false;
        }
      });

      var remove = el("button", { className: "btn btn--danger btn--sm", attrs: { type: "button", "aria-label": "Delete alert " + alert.name } }, [
        icon("trash"),
      ]);
      remove.addEventListener("click", async function () {
        if (!window.confirm('Delete the alert "' + alert.name + '"?')) {
          return;
        }
        remove.disabled = true;
        try {
          await Api.del(url);
          Utils.toast("Alert deleted.", "info");
          load();
        } catch (error) {
          Utils.toast(error.message, "error");
          remove.disabled = false;
        }
      });

      var chips = criteria(alert).map(function (text) {
        return el("span", { className: "chip chip--static", text: text });
      });

      card.appendChild(
        el("div", { className: "alert-card__head" }, [
          el("h3", { text: alert.name }),
          el("span", { className: "badge badge--full_time", text: alert.frequency === "weekly" ? "Weekly" : "Daily" }),
        ])
      );
      card.appendChild(el("div", { className: "alert-card__chips" }, chips));
      card.appendChild(
        el("div", { className: "alert-card__foot" }, [
          el("span", { text: alert.last_sent_at ? "Last sent " + Utils.timeAgo(alert.last_sent_at) : "Not sent yet" }),
          el("div", { className: "alert-card__actions" }, [toggle, remove]),
        ])
      );
      return card;
    }

    async function load() {
      emptyEl.hidden = true;
      errorEl.hidden = true;
      clear(listEl);
      try {
        var data = await Api.get("alerts/", { page_size: 50 });
        if (data.results.length === 0) {
          emptyEl.hidden = false;
          return;
        }
        data.results.forEach(function (alert) {
          listEl.appendChild(renderAlert(alert));
        });
      } catch (error) {
        qs("[data-error-text]", errorEl).textContent = error.message;
        errorEl.hidden = false;
      }
    }

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      Utils.clearFormErrors(form);
      var payload = buildPayload(form);
      if (!payload.name) {
        Utils.showFormErrors(form, { message: "Give your alert a name.", data: { name: ["Give your alert a name."] } });
        return;
      }
      var submit = qs('button[type="submit"]', form);
      Utils.setLoading(submit, true, "Creating...");
      try {
        await Api.post("alerts/", payload);
        form.reset();
        Utils.toast("Alert created.", "success");
        await load();
      } catch (error) {
        Utils.showFormErrors(form, error);
      } finally {
        Utils.setLoading(submit, false);
      }
    });

    qsa('[data-action="retry"]').forEach(function (button) {
      button.addEventListener("click", load);
    });

    load();
  }

  global.Alerts = { initAlerts: initAlerts };
})(window);