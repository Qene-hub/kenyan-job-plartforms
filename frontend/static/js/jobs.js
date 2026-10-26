/*
 * jobs.js: home page, job list with filters, job detail, and the shared job card.
 * Needs utils.js, auth.js and api.js loaded first.
 */
(function (global) {
  "use strict";

  var qs = Utils.qs;
  var qsa = Utils.qsa;
  var el = Utils.el;
  var icon = Utils.icon;
  var clear = Utils.clear;

  // jobId -> saved-job id, for the logged-in user
  var savedMap = new Map();

  var SOURCE_LABELS = {
    manual: "Added by our team",
    employer: "Submitted by the employer",
    adzuna: "Adzuna",
  };

  // ---------- Shared helpers ----------
  function badge(text, className) {
    return el("span", { className: "badge " + className, text: text });
  }

  function fillSelect(select, options) {
    if (!select) {
      return;
    }
    (options || []).forEach(function (option) {
      select.appendChild(el("option", { text: option.label, attrs: { value: option.value } }));
    });
  }

  function renderSkeletons(container, count) {
    for (var i = 0; i < count; i += 1) {
      container.appendChild(
        el("div", { className: "skeleton-card", attrs: { "aria-hidden": "true" } }, [
          el("div", { className: "skeleton skeleton--title" }),
          el("div", { className: "skeleton skeleton--line" }),
          el("div", { className: "skeleton skeleton--line skeleton--short" }),
          el("div", { className: "skeleton skeleton--line" }),
        ])
      );
    }
  }

  function setSavedState(button, saved) {
    button.classList.toggle("is-saved", saved);
    button.setAttribute("aria-pressed", String(saved));
    if (button.querySelector("[data-save-label]")) {
      button.querySelector("[data-save-label]").textContent = saved ? "Saved" : "Save";
    } else {
      button.setAttribute("aria-label", saved ? "Remove from saved jobs" : "Save job");
    }
  }

  async function loadSavedMap() {
    savedMap = new Map();
    if (!Auth.isLoggedIn()) {
      return;
    }
    try {
      var data = await Api.get("saved-jobs/", { page_size: 100 }, { noRedirect: true });
      data.results.forEach(function (item) {
        savedMap.set(item.job.id, item.id);
      });
    } catch (error) {
      Auth.syncNavbar();
    }
  }

  async function toggleSave(jobId, button, onUnsave) {
    if (!Auth.isLoggedIn()) {
      Utils.toast("Log in to save jobs.", "info");
      setTimeout(function () {
        window.location.assign(Auth.loginUrl());
      }, 700);
      return;
    }
    button.disabled = true;
    try {
      if (savedMap.has(jobId)) {
        await Api.del("saved-jobs/" + savedMap.get(jobId) + "/");
        savedMap.delete(jobId);
        setSavedState(button, false);
        Utils.toast("Removed from your saved jobs.", "info");
        if (onUnsave) {
          onUnsave(jobId);
        }
      } else {
        var saved = await Api.post("saved-jobs/", { job_id: jobId });
        savedMap.set(jobId, saved.id);
        setSavedState(button, true);
        Utils.toast("Job saved.", "success");
      }
    } catch (error) {
      Utils.toast(error.message, "error");
    } finally {
      button.disabled = false;
    }
  }

  // ---------- Job card ----------
  function renderCard(job, options) {
    var opts = options || {};
    var template = document.getElementById("job-card-template");
    var card = template.content.firstElementChild.cloneNode(true);
    var url = "/jobs/" + job.id + "/";
    var company = job.company || { name: "Company" };

    var avatar = qs('[data-field="avatar"]', card);
    avatar.textContent = Utils.initials(company.name);
    avatar.classList.add(Utils.avatarClass(company.name));
    avatar.setAttribute("href", url);

    var title = qs('[data-field="title"]', card);
    title.textContent = job.title;
    title.setAttribute("href", url);

    qs('[data-field="company"]', card).textContent = company.name;

    var location = [job.location_detail, job.county_display].filter(Boolean).join(", ") || "Kenya";
    qs('[data-field="location"]', card).textContent = location;
    qs('[data-field="posted"]', card).textContent = job.published_at ? "Posted " + Utils.timeAgo(job.published_at) : "";

    var badges = qs('[data-field="badges"]', card);
    badges.appendChild(badge(job.job_type_display, "badge--" + job.job_type));
    badges.appendChild(badge(job.work_mode_display, "badge--" + job.work_mode));
    if (job.experience_level_display) {
      badges.appendChild(badge(job.experience_level_display, "badge--level"));
    }

    var skillsBox = qs('[data-field="skills"]', card);
    var skills = job.skills || [];
    skills.slice(0, 4).forEach(function (name) {
      skillsBox.appendChild(el("span", { className: "chip chip--static", text: name }));
    });
    if (skills.length > 4) {
      skillsBox.appendChild(el("span", { className: "chip chip--static chip--more", text: "+" + (skills.length - 4) }));
    }
    if (skills.length === 0) {
      skillsBox.hidden = true;
    }

    var salary = qs('[data-field="salary"]', card);
    if (job.salary_display) {
      salary.textContent = job.salary_display;
    } else {
      salary.textContent = "Salary not disclosed";
      salary.classList.add("is-muted");
    }

    var info = Utils.deadlineInfo(job.deadline);
    var deadline = qs('[data-field="deadline"]', card);
    deadline.textContent = info.text;
    deadline.classList.add("deadline--" + info.level);

    var saveButton = qs('[data-action="save"]', card);
    setSavedState(saveButton, savedMap.has(job.id));
    saveButton.addEventListener("click", function () {
      toggleSave(job.id, saveButton, opts.onUnsave);
    });

    return card;
  }

  // ---------- Home page ----------
  function countUp(node, target) {
    var total = Number(target) || 0;
    if (total === 0) {
      node.textContent = "0";
      return;
    }
    var duration = 700;
    var start = null;
    function step(timestamp) {
      if (start === null) {
        start = timestamp;
      }
      var progress = Math.min((timestamp - start) / duration, 1);
      node.textContent = Utils.formatNumber(Math.round(total * progress));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    }
    window.requestAnimationFrame(step);
  }

  async function loadStats() {
    var targets = { jobs: "jobs/", companies: "companies/" };
    await Promise.all(
      Object.keys(targets).map(async function (key) {
        var node = qs('[data-stat="' + key + '"]');
        if (!node) {
          return;
        }
        try {
          var data = await Api.get(targets[key], { page_size: 1 }, { auth: false });
          countUp(node, data.count);
        } catch (error) {
          node.textContent = "-";
        }
      })
    );
  }

  async function loadLatest() {
    var container = qs("#latest-jobs");
    var empty = qs("#latest-empty");
    clear(container);
    renderSkeletons(container, 6);
    try {
      var data = await Api.get("jobs/", { page_size: 6, ordering: "-published_at" }, { auth: false });
      clear(container);
      if (data.results.length === 0) {
        empty.hidden = false;
        return;
      }
      data.results.forEach(function (job) {
        container.appendChild(renderCard(job));
      });
    } catch (error) {
      clear(container);
      container.appendChild(el("p", { className: "text-muted", text: "We could not load the latest jobs: " + error.message }));
    }
  }

  async function initHome() {
    var countySelect = qs("#hero-county");
    var metaPromise = Api.get("meta/", null, { auth: false }).catch(function () {
      return null;
    });
    loadStats();
    var savedPromise = loadSavedMap();

    var meta = await metaPromise;
    if (meta) {
      fillSelect(countySelect, meta.counties);
    }
    await savedPromise;
    loadLatest();
  }

  // ---------- Job list page ----------
  function buildChecks(container, group, options) {
    options.forEach(function (option) {
      var input = el("input", { attrs: { type: "checkbox", name: group, value: option.value } });
      container.appendChild(el("label", { className: "check" }, [input, el("span", { text: option.label })]));
    });
  }

  function readFilters(form) {
    var params = new URLSearchParams();
    var search = form.elements.namedItem("search").value.trim();
    if (search) {
      params.set("search", search);
    }
    var county = form.elements.namedItem("county").value;
    if (county) {
      params.set("county", county);
    }
    ["job_type", "work_mode", "experience_level"].forEach(function (group) {
      qsa('input[name="' + group + '"]:checked', form).forEach(function (input) {
        params.append(group, input.value);
      });
    });
    var minSalary = form.elements.namedItem("min_salary").value;
    if (minSalary && Number(minSalary) > 0) {
      params.set("min_salary", minSalary);
    }
    var posted = form.elements.namedItem("posted_within").value;
    if (posted) {
      params.set("posted_within", posted);
    }
    var ordering = form.elements.namedItem("ordering").value;
    if (ordering && ordering !== "-published_at") {
      params.set("ordering", ordering);
    }
    return params;
  }

  function applyParams(form, params) {
    form.elements.namedItem("search").value = params.get("search") || "";
    form.elements.namedItem("county").value = params.get("county") || "";
    form.elements.namedItem("min_salary").value = params.get("min_salary") || "";
    form.elements.namedItem("posted_within").value = params.get("posted_within") || "";
    form.elements.namedItem("ordering").value = params.get("ordering") || "-published_at";
    ["job_type", "work_mode", "experience_level"].forEach(function (group) {
      var selected = params.getAll(group);
      qsa('input[name="' + group + '"]', form).forEach(function (input) {
        input.checked = selected.indexOf(input.value) !== -1;
      });
    });
  }

  async function initList() {
    var form = qs("#filters-form");
    if (!form) {
      return;
    }
    var resultsEl = qs("#results");
    var countEl = qs("#results-count");
    var emptyEl = qs("#results-empty");
    var errorEl = qs("#results-error");
    var errorText = qs("[data-error-text]", errorEl);
    var nav = qs("[data-pagination]");
    var panel = qs("#filters-panel");
    var PAGE_SIZE = 12;
    var page = 1;
    var requestId = 0;

    var params = Utils.getParams();
    var metaPromise = Api.get("meta/", null, { auth: false }).catch(function () {
      return null;
    });
    var savedPromise = loadSavedMap();

    var meta = await metaPromise;
    if (meta) {
      fillSelect(form.elements.namedItem("county"), meta.counties);
      var groups = {
        job_type: meta.job_types,
        work_mode: meta.work_modes,
        experience_level: meta.experience_levels,
      };
      qsa("[data-group]", form).forEach(function (box) {
        var key = box.getAttribute("data-group");
        buildChecks(box, key, groups[key] || []);
      });
    }
    applyParams(form, params);
    page = parseInt(params.get("page"), 10) || 1;
    await savedPromise;

    function showResults(data) {
      clear(resultsEl);
      var total = data.count;
      countEl.textContent = total === 0 ? "No jobs found" : total + (total === 1 ? " job found" : " jobs found");
      if (total === 0) {
        emptyEl.hidden = false;
        Utils.renderPagination(nav, { page: 1, totalPages: 0 });
        return;
      }
      data.results.forEach(function (job) {
        resultsEl.appendChild(renderCard(job));
      });
      Utils.renderPagination(nav, { page: page, totalPages: Math.ceil(total / PAGE_SIZE) }, function (next) {
        page = next;
        load();
        resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }

    async function load() {
      var filters = readFilters(form);
      var query = new URLSearchParams(filters);
      query.set("page", String(page));
      query.set("page_size", String(PAGE_SIZE));

      var urlParams = new URLSearchParams(filters);
      if (page > 1) {
        urlParams.set("page", String(page));
      }
      Utils.replaceUrlParams(urlParams);

      requestId += 1;
      var current = requestId;
      emptyEl.hidden = true;
      errorEl.hidden = true;
      clear(resultsEl);
      renderSkeletons(resultsEl, 6);
      countEl.textContent = "Searching...";

      try {
        var data = await Api.get("jobs/", query, { auth: false });
        if (current !== requestId) {
          return;
        }
        showResults(data);
      } catch (error) {
        if (current !== requestId) {
          return;
        }
        if (error.status === 404 && page > 1) {
          page = 1;
          load();
          return;
        }
        clear(resultsEl);
        countEl.textContent = "";
        errorText.textContent = error.message;
        errorEl.hidden = false;
        Utils.renderPagination(nav, { page: 1, totalPages: 0 });
      }
    }

    function reload() {
      page = 1;
      load();
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      reload();
    });
    form.addEventListener("change", function (event) {
      if (event.target.hasAttribute("data-live-text")) {
        return;
      }
      reload();
    });
    form.addEventListener(
      "input",
      Utils.debounce(function (event) {
        if (event.target.hasAttribute("data-live-text")) {
          reload();
        }
      }, 450)
    );

    qsa('[data-action="clear-filters"]').forEach(function (button) {
      button.addEventListener("click", function () {
        form.reset();
        reload();
      });
    });
    qsa('[data-action="retry"]').forEach(function (button) {
      button.addEventListener("click", load);
    });
    var toggle = qs("[data-filters-toggle]");
    if (toggle && panel) {
      toggle.addEventListener("click", function () {
        panel.classList.toggle("is-open");
      });
    }

    load();
  }

  // ---------- Job detail page ----------
  function addRow(list, label, value) {
    if (!value) {
      return;
    }
    list.appendChild(el("div", { className: "overview__row" }, [el("dt", { text: label }), el("dd", { text: value })]));
  }

  function setTracked(button) {
    button.disabled = true;
    var label = qs("span", button);
    if (label) {
      label.textContent = "In your tracker";
    }
  }

  function renderDetail(job) {
    var root = qs("#job-detail");
    var company = job.company;
    document.title = job.title + " at " + company.name + " | Kenya Job Platform";

    var avatar = qs('[data-field="avatar"]', root);
    avatar.textContent = Utils.initials(company.name);
    avatar.classList.add(Utils.avatarClass(company.name));

    qs('[data-field="title"]', root).textContent = job.title;

    var companyNode = qs('[data-field="company"]', root);
    var site = Utils.safeUrl(company.website);
    clear(companyNode);
    if (site) {
      companyNode.appendChild(el("a", { text: company.name, attrs: { href: site, target: "_blank", rel: "noopener noreferrer" } }));
    } else {
      companyNode.textContent = company.name;
    }

    var badges = qs('[data-field="badges"]', root);
    badges.appendChild(badge(job.job_type_display, "badge--" + job.job_type));
    badges.appendChild(badge(job.work_mode_display, "badge--" + job.work_mode));
    if (job.experience_level_display) {
      badges.appendChild(badge(job.experience_level_display, "badge--level"));
    }

    qs('[data-field="description"]', root).textContent = job.description;

    var requirementsSection = qs('[data-field-section="requirements"]', root);
    if (job.requirements) {
      qs('[data-field="requirements"]', root).textContent = job.requirements;
    } else {
      requirementsSection.hidden = true;
    }

    var skillsSection = qs('[data-field-section="skills"]', root);
    var skillsBox = qs('[data-field="skills"]', root);
    if (job.skills && job.skills.length > 0) {
      job.skills.forEach(function (name) {
        skillsBox.appendChild(
          el("a", { className: "chip", text: name, attrs: { href: "/jobs/?search=" + encodeURIComponent(name) } })
        );
      });
    } else {
      skillsSection.hidden = true;
    }

    var apply = qs('[data-field="apply"]', root);
    var applyUrl = Utils.safeUrl(job.application_url);
    if (applyUrl) {
      apply.setAttribute("href", applyUrl);
    } else if (job.application_email) {
      apply.setAttribute("href", "mailto:" + job.application_email);
      apply.removeAttribute("target");
      qs("span", apply).textContent = "Apply by email";
    } else {
      apply.hidden = true;
    }

    var overview = qs('[data-field="overview"]', root);
    var info = Utils.deadlineInfo(job.deadline);
    addRow(overview, "Location", [job.location_detail, job.county_display].filter(Boolean).join(", ") || "Kenya");
    addRow(overview, "Job type", job.job_type_display);
    addRow(overview, "Work mode", job.work_mode_display);
    addRow(overview, "Experience", job.experience_level_display);
    addRow(overview, "Salary", job.salary_display || "Not disclosed");
    addRow(overview, "Deadline", job.deadline ? Utils.formatDate(job.deadline) + " (" + info.text.toLowerCase() + ")" : "No deadline");
    addRow(overview, "Posted", Utils.formatDate(job.published_at));

    var sourceBox = qs('[data-field-section="source"]', root);
    var source = (job.sources || [])[0];
    if (source) {
      qs('[data-field="source-name"]', root).textContent = SOURCE_LABELS[source.name] || source.name;
      var verified = qs('[data-field="source-verified"]', root);
      if (source.last_verified_at) {
        verified.textContent = "Last verified on " + Utils.formatDate(source.last_verified_at);
      } else {
        verified.hidden = true;
      }
      var link = qs('[data-field="source-link"]', root);
      var sourceUrl = Utils.safeUrl(source.source_url);
      if (sourceUrl) {
        link.setAttribute("href", sourceUrl);
      } else {
        link.hidden = true;
      }
    } else {
      sourceBox.hidden = true;
    }

    var saveButton = qs('[data-action="save"]', root);
    setSavedState(saveButton, savedMap.has(job.id));
    saveButton.addEventListener("click", function () {
      toggleSave(job.id, saveButton);
    });

    var trackButton = qs('[data-action="track"]', root);
    trackButton.addEventListener("click", async function () {
      if (!Auth.isLoggedIn()) {
        Utils.toast("Log in to track your applications.", "info");
        setTimeout(function () {
          window.location.assign(Auth.loginUrl());
        }, 700);
        return;
      }
      trackButton.disabled = true;
      try {
        await Api.post("applications/", { job_id: job.id });
        Utils.toast("Added to your application tracker.", "success");
        setTracked(trackButton);
      } catch (error) {
        Utils.toast(error.message, "error");
        if (/already/i.test(error.message)) {
          setTracked(trackButton);
        } else {
          trackButton.disabled = false;
        }
      }
    });

    var shareButton = qs('[data-action="share"]', root);
    shareButton.addEventListener("click", async function () {
      try {
        await navigator.clipboard.writeText(window.location.href);
        Utils.toast("Link copied.", "success");
      } catch (error) {
        window.prompt("Copy this link:", window.location.href);
      }
    });
  }

  async function initDetail(jobId) {
    var loading = qs("#job-loading");
    var detail = qs("#job-detail");
    var errorBox = qs("#job-error");
    try {
      var results = await Promise.all([Api.get("jobs/" + jobId + "/", null, { auth: false }), loadSavedMap()]);
      renderDetail(results[0]);
      loading.hidden = true;
      detail.hidden = false;
    } catch (error) {
      loading.hidden = true;
      if (error.status === 404) {
        qs("[data-error-title]", errorBox).textContent = "This job is not available";
        qs("[data-error-text]", errorBox).textContent = "It may have closed or been removed.";
      } else {
        qs("[data-error-title]", errorBox).textContent = "We could not load this job";
        qs("[data-error-text]", errorBox).textContent = error.message;
      }
      errorBox.hidden = false;
    }
  }

  global.Jobs = {
    initHome: initHome,
    initList: initList,
    initDetail: initDetail,
    renderCard: renderCard,
    renderSkeletons: renderSkeletons,
    loadSavedMap: loadSavedMap,
    markSaved: function (jobId, savedId) {
      savedMap.set(jobId, savedId);
    },
  };
})(window);