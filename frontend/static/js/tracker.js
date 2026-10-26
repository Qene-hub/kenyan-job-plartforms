/*
 * tracker.js: dashboard, saved jobs and applications pages.
 * The saved jobs page also needs jobs.js (for the shared job card).
 */
(function (global) {
  "use strict";

  var qs = Utils.qs;
  var qsa = Utils.qsa;
  var el = Utils.el;
  var icon = Utils.icon;
  var clear = Utils.clear;

  var STATUSES = [
    { value: "saved", label: "Saved" },
    { value: "applied", label: "Applied" },
    { value: "assessment", label: "Assessment" },
    { value: "interview", label: "Interview" },
    { value: "offer", label: "Offer" },
    { value: "rejected", label: "Rejected" },
  ];

  function statusLabel(value) {
    for (var i = 0; i < STATUSES.length; i += 1) {
      if (STATUSES[i].value === value) {
        return STATUSES[i].label;
      }
    }
    return value;
  }

  function statusPill(value) {
    return el("span", { className: "status status--" + value, text: statusLabel(value) });
  }

  function jobAvatar(job) {
    return el("a", {
      className: "avatar " + Utils.avatarClass(job.company.name),
      text: Utils.initials(job.company.name),
      attrs: { href: "/jobs/" + job.id + "/", "aria-hidden": "true", tabindex: "-1" },
    });
  }

  function showError(box, error) {
    if (!box) {
      return;
    }
    var text = qs("[data-error-text]", box);
    if (text) {
      text.textContent = error.message;
    }
    box.hidden = false;
  }

  // ---------- Dashboard ----------
  function listItem(job, side) {
    var url = "/jobs/" + job.id + "/";
    return el("li", { className: "list-item" }, [
      jobAvatar(job),
      el("div", { className: "list-item__body" }, [
        el("a", { className: "list-item__title", text: job.title, attrs: { href: url } }),
        el("p", { className: "list-item__sub", text: job.company.name }),
      ]),
      side,
    ]);
  }

  async function initDashboard() {
    if (!Auth.requireLogin()) {
      return;
    }
    var nameNode = qs("[data-user-firstname]");
    function setName(user) {
      if (nameNode && user) {
        nameNode.textContent = user.first_name || user.username;
      }
    }
    setName(Auth.getUser());
    Api.get("auth/me/", null, { noRedirect: true })
      .then(function (user) {
        Auth.setUser(user);
        setName(user);
      })
      .catch(function () {});

    var recentList = qs("#recent-applications");
    var savedList = qs("#recent-saved");

    try {
      var results = await Promise.all([
        Api.get("applications/summary/"),
        Api.get("applications/", { page_size: 5 }),
        Api.get("saved-jobs/", { page_size: 4 }),
      ]);
      var summary = results[0];

      var values = {
        total: summary.total,
        applied: summary.by_status.applied,
        assessment: summary.by_status.assessment,
        interview: summary.by_status.interview,
        offer: summary.by_status.offer,
        saved_jobs: summary.saved_jobs,
      };
      Object.keys(values).forEach(function (key) {
        qsa('[data-stat="' + key + '"]').forEach(function (node) {
          node.textContent = String(values[key]);
        });
      });

      if (summary.follow_ups_due > 0) {
        qs("[data-followup-count]").textContent = String(summary.follow_ups_due);
        qs("#followup-banner").hidden = false;
      }

      clear(recentList);
      if (results[1].results.length === 0) {
        recentList.appendChild(el("li", { className: "list-empty", text: "You are not tracking any applications yet." }));
      }
      results[1].results.forEach(function (application) {
        var side = el("div", { className: "list-item__side" }, [
          statusPill(application.status),
          el("span", { text: application.applied_date ? "Applied " + Utils.formatDate(application.applied_date) : "Updated " + Utils.timeAgo(application.updated_at) }),
        ]);
        recentList.appendChild(listItem(application.job, side));
      });

      clear(savedList);
      if (results[2].results.length === 0) {
        savedList.appendChild(el("li", { className: "list-empty", text: "You have not saved any jobs yet." }));
      }
      results[2].results.forEach(function (item) {
        var side = el("div", { className: "list-item__side" }, [
          el("span", { text: item.job.salary_display || item.job.county_display || "" }),
        ]);
        savedList.appendChild(listItem(item.job, side));
      });
    } catch (error) {
      Utils.toast(error.message, "error");
      showError(qs("#dashboard-error"), error);
      clear(recentList);
      clear(savedList);
    }
  }

  // ---------- Saved jobs ----------
  function initSaved() {
    if (!Auth.requireLogin()) {
      return;
    }
    var grid = qs("#saved-grid");
    var emptyEl = qs("#saved-empty");
    var errorEl = qs("#saved-error");
    var nav = qs("[data-pagination]");
    var PAGE_SIZE = 12;
    var page = 1;

    function buildCard(item) {
      var card = Jobs.renderCard(item.job, {
        onUnsave: function () {
          load();
        },
      });
      var trackButton = el("button", { className: "btn btn--secondary btn--sm", attrs: { type: "button" } }, [
        icon("check-circle"),
        el("span", { text: "Track application" }),
      ]);
      trackButton.addEventListener("click", async function () {
        trackButton.disabled = true;
        try {
          await Api.post("applications/", { job_id: item.job.id });
          Utils.toast("Added to your application tracker.", "success");
          qs("span", trackButton).textContent = "In your tracker";
        } catch (error) {
          Utils.toast(error.message, "error");
          if (/already/i.test(error.message)) {
            qs("span", trackButton).textContent = "In your tracker";
          } else {
            trackButton.disabled = false;
          }
        }
      });
      card.appendChild(el("div", { className: "job-card__extra" }, [trackButton]));
      return card;
    }

    async function load() {
      emptyEl.hidden = true;
      errorEl.hidden = true;
      clear(grid);
      Jobs.renderSkeletons(grid, 6);
      try {
        var data = await Api.get("saved-jobs/", { page_size: PAGE_SIZE, page: page });
        if (data.results.length === 0 && page > 1) {
          page -= 1;
          return load();
        }
        clear(grid);
        if (data.count === 0) {
          emptyEl.hidden = false;
          Utils.renderPagination(nav, { page: 1, totalPages: 0 });
          return null;
        }
        data.results.forEach(function (item) {
          Jobs.markSaved(item.job.id, item.id);
          grid.appendChild(buildCard(item));
        });
        Utils.renderPagination(nav, { page: page, totalPages: Math.ceil(data.count / PAGE_SIZE) }, function (next) {
          page = next;
          load();
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      } catch (error) {
        clear(grid);
        showError(errorEl, error);
        Utils.renderPagination(nav, { page: 1, totalPages: 0 });
      }
      return null;
    }

    qsa('[data-action="retry"]').forEach(function (button) {
      button.addEventListener("click", load);
    });
    load();
  }

  // ---------- Applications ----------
  function initApplications() {
    if (!Auth.requireLogin()) {
      return;
    }
    var PAGE_SIZE = 10;
    var listEl = qs("#applications-list");
    var emptyEl = qs("#applications-empty");
    var errorEl = qs("#applications-error");
    var tabsEl = qs("#status-tabs");
    var nav = qs("[data-pagination]");
    var dialog = qs("#notes-dialog");
    var notesListEl = qs("#notes-list");
    var noteForm = qs("#note-form");

    var requested = Utils.getParams().get("status") || "";
    var status = STATUSES.some(function (s) {
      return s.value === requested;
    })
      ? requested
      : "";
    var page = 1;
    var notesApp = null;
    var notesCountNode = null;

    function syncUrl() {
      var params = new URLSearchParams();
      if (status) {
        params.set("status", status);
      }
      Utils.replaceUrlParams(params);
    }

    function renderTabs(summary) {
      clear(tabsEl);
      var tabs = [{ value: "", label: "All", count: summary.total }].concat(
        STATUSES.map(function (s) {
          return { value: s.value, label: s.label, count: summary.by_status[s.value] || 0 };
        })
      );
      tabs.forEach(function (tab) {
        var button = el(
          "button",
          { className: "tab" + (tab.value === status ? " is-active" : ""), attrs: { type: "button" } },
          [el("span", { text: tab.label }), el("span", { className: "tab__count", text: tab.count })]
        );
        button.addEventListener("click", function () {
          status = tab.value;
          page = 1;
          syncUrl();
          loadSummary();
          load();
        });
        tabsEl.appendChild(button);
      });
    }

    async function loadSummary() {
      try {
        renderTabs(await Api.get("applications/summary/"));
      } catch (error) {
        Utils.toast(error.message, "error");
      }
    }

    function field(labelText, control) {
      return el("label", { className: "field-inline" }, [el("span", { text: labelText }), control]);
    }

    function renderApplication(application) {
      var job = application.job;
      var url = "applications/" + application.id + "/";
      var pill = statusPill(application.status);
      var currentStatus = application.status;
      var currentFollowUp = application.follow_up_date || "";

      var select = el("select", {
        className: "form-control form-control--sm",
        attrs: { "aria-label": "Status for " + job.title },
      });
      STATUSES.forEach(function (s) {
        var option = el("option", { text: s.label, attrs: { value: s.value } });
        if (s.value === application.status) {
          option.selected = true;
        }
        select.appendChild(option);
      });
      select.addEventListener("change", async function () {
        select.disabled = true;
        try {
          var updated = await Api.patch(url, { status: select.value });
          currentStatus = updated.status;
          pill.className = "status status--" + updated.status;
          pill.textContent = statusLabel(updated.status);
          Utils.toast("Status changed to " + statusLabel(updated.status) + ".", "success");
          loadSummary();
          if (status && status !== updated.status) {
            load();
          }
        } catch (error) {
          select.value = currentStatus;
          Utils.toast(error.message, "error");
        } finally {
          select.disabled = false;
        }
      });

      var followUp = el("input", {
        className: "form-control form-control--sm",
        attrs: { type: "date", value: currentFollowUp, "aria-label": "Follow-up date for " + job.title },
      });
      followUp.addEventListener("change", async function () {
        try {
          await Api.patch(url, { follow_up_date: followUp.value || null });
          currentFollowUp = followUp.value;
          Utils.toast("Follow-up date saved.", "success");
          loadSummary();
        } catch (error) {
          followUp.value = currentFollowUp;
          Utils.toast(error.message, "error");
        }
      });

      var countNode = el("span", { className: "notes-count", text: application.notes_count });
      var notesButton = el("button", { className: "btn btn--ghost btn--sm", attrs: { type: "button" } }, [
        icon("message-square"),
        el("span", { text: "Notes" }),
        countNode,
      ]);
      notesButton.addEventListener("click", function () {
        openNotes(application, countNode);
      });

      var deleteButton = el(
        "button",
        { className: "btn btn--danger btn--sm", attrs: { type: "button", "aria-label": "Stop tracking " + job.title } },
        [icon("trash")]
      );
      deleteButton.addEventListener("click", async function () {
        if (!window.confirm("Stop tracking this application? Its notes will be deleted too.")) {
          return;
        }
        deleteButton.disabled = true;
        try {
          await Api.del(url);
          Utils.toast("Application removed.", "info");
          loadSummary();
          load();
        } catch (error) {
          Utils.toast(error.message, "error");
          deleteButton.disabled = false;
        }
      });

      var meta = el("div", { className: "app-row__meta" }, [
        pill,
        el("span", {
          text: application.applied_date ? "Applied " + Utils.formatDate(application.applied_date) : "Not applied yet",
        }),
        el("span", { text: "Updated " + Utils.timeAgo(application.updated_at) }),
      ]);

      return el("article", { className: "app-row" }, [
        el("div", { className: "app-row__main" }, [
          jobAvatar(job),
          el("div", { className: "app-row__info" }, [
            el("a", { className: "app-row__title", text: job.title, attrs: { href: "/jobs/" + job.id + "/" } }),
            el("p", { className: "app-row__sub", text: job.company.name }),
            meta,
          ]),
        ]),
        el("div", { className: "app-row__controls" }, [
          field("Status", select),
          field("Follow up", followUp),
          notesButton,
          deleteButton,
        ]),
      ]);
    }

    function renderRowSkeletons() {
      for (var i = 0; i < 3; i += 1) {
        listEl.appendChild(el("div", { className: "skeleton skeleton-row", attrs: { "aria-hidden": "true" } }));
      }
    }

    async function load() {
      emptyEl.hidden = true;
      errorEl.hidden = true;
      clear(listEl);
      renderRowSkeletons();
      try {
        var params = { page_size: PAGE_SIZE, page: page };
        if (status) {
          params.status = status;
        }
        var data = await Api.get("applications/", params);
        if (data.results.length === 0 && page > 1) {
          page -= 1;
          return load();
        }
        clear(listEl);
        if (data.count === 0) {
          qs("[data-empty-title]", emptyEl).textContent = status ? "Nothing with status " + statusLabel(status) : "No applications yet";
          qs("[data-empty-text]", emptyEl).textContent = status
            ? "Change the status of an application to see it here."
            : "Open any job and choose Track application to add it here.";
          emptyEl.hidden = false;
          Utils.renderPagination(nav, { page: 1, totalPages: 0 });
          return null;
        }
        data.results.forEach(function (application) {
          listEl.appendChild(renderApplication(application));
        });
        Utils.renderPagination(nav, { page: page, totalPages: Math.ceil(data.count / PAGE_SIZE) }, function (next) {
          page = next;
          load();
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      } catch (error) {
        clear(listEl);
        showError(errorEl, error);
        Utils.renderPagination(nav, { page: 1, totalPages: 0 });
      }
      return null;
    }

    // ----- Notes dialog -----
    function renderNotes(notes) {
      clear(notesListEl);
      if (notesCountNode) {
        notesCountNode.textContent = String(notes.length);
      }
      if (notes.length === 0) {
        notesListEl.appendChild(el("li", { className: "list-empty", text: "No notes yet." }));
        return;
      }
      notes.forEach(function (note) {
        var remove = el("button", { className: "icon-btn", attrs: { type: "button", "aria-label": "Delete note" } }, [icon("trash")]);
        remove.addEventListener("click", async function () {
          remove.disabled = true;
          try {
            await Api.del("applications/" + notesApp.id + "/notes/" + note.id + "/");
            await refreshNotes();
          } catch (error) {
            Utils.toast(error.message, "error");
            remove.disabled = false;
          }
        });
        notesListEl.appendChild(
          el("li", { className: "note" }, [
            el("div", {}, [
              el("p", { className: "note__body", text: note.body }),
              el("span", { className: "note__date", text: Utils.formatDateTime(note.created_at) }),
            ]),
            remove,
          ])
        );
      });
    }

    async function refreshNotes() {
      try {
        renderNotes(await Api.get("applications/" + notesApp.id + "/notes/"));
      } catch (error) {
        clear(notesListEl);
        notesListEl.appendChild(el("li", { className: "list-empty", text: error.message }));
      }
    }

    async function openNotes(application, countNode) {
      notesApp = application;
      notesCountNode = countNode;
      qs("[data-notes-title]", dialog).textContent = application.job.title + " at " + application.job.company.name;
      noteForm.reset();
      Utils.clearFormErrors(noteForm);
      clear(notesListEl);
      notesListEl.appendChild(el("li", { className: "list-empty", text: "Loading notes..." }));
      if (!dialog.open) {
        dialog.showModal();
      }
      await refreshNotes();
    }

    noteForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      Utils.clearFormErrors(noteForm);
      var body = noteForm.elements.namedItem("body").value.trim();
      if (!body) {
        Utils.showFormErrors(noteForm, { message: "Write a note first.", data: { body: ["Write a note first."] } });
        return;
      }
      var submit = qs('button[type="submit"]', noteForm);
      submit.disabled = true;
      try {
        await Api.post("applications/" + notesApp.id + "/notes/", { body: body });
        noteForm.reset();
        await refreshNotes();
      } catch (error) {
        Utils.showFormErrors(noteForm, error);
      } finally {
        submit.disabled = false;
      }
    });

    qsa("[data-close-dialog]", dialog).forEach(function (button) {
      button.addEventListener("click", function () {
        dialog.close();
      });
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        dialog.close();
      }
    });
    qsa('[data-action="retry"]').forEach(function (button) {
      button.addEventListener("click", function () {
        loadSummary();
        load();
      });
    });

    loadSummary();
    load();
  }

  global.Tracker = {
    initDashboard: initDashboard,
    initSaved: initSaved,
    initApplications: initApplications,
  };
})(window);