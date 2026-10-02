document.addEventListener("DOMContentLoaded", () => {
  const dock = document.querySelector("[data-tool-dock]");
  const toggle = document.querySelector("[data-tool-dock-toggle]");

  const modal = document.querySelector("[data-tool-access-modal]");
  const modalLogo = document.querySelector("[data-tool-access-logo]");
  const modalTitle = document.querySelector("[data-tool-access-title]");
  const modalIntro = document.querySelector("[data-tool-access-intro]");
  const modalLabel = document.querySelector("[data-tool-access-label]");
  const modalForm = document.querySelector("[data-tool-access-form]");
  const modalInput = document.querySelector("[data-tool-access-input]");
  const modalSubmit = document.querySelector("[data-tool-access-submit]");
  const modalError = document.querySelector("[data-tool-access-error]");

  const studentToolButtons = document.querySelectorAll("[data-student-tool]");
  const closeButtons = document.querySelectorAll("[data-tool-access-close]");

  let activeTool = null;
  let lastFocusedElement = null;
  let lastGithubUsername = "";


  /* =======================================================
     TOOLS
     ======================================================= */

  const tools = {
    github: {
      title: "Open jouw GitHub",
      submitLabel: "Open GitHub",
      logo: "assets/images/tool-dock/github.png",

      buildUrl(githubUsername) {
        return `https://github.com/oncparkdreef/informatica-2627-${githubUsername}`;
      }
    },

    codespaces: {
      title: "Open jouw Codespace",
      submitLabel: "Open Codespace",
      logo: "assets/images/tool-dock/codespaces.png",

      buildUrl(githubUsername) {
        return `https://onc-informatica-codespaces.j-henze.workers.dev/login?github_user=${encodeURIComponent(githubUsername)}`;
      }
    }
  };


  /* =======================================================
     TOOL DOCK OPEN / DICHT
     ======================================================= */

  if (dock && toggle) {
    const toggleLabel = toggle.querySelector(".tool-dock__sr-only");

    toggle.addEventListener("click", () => {
      const isOpen = dock.classList.toggle("is-open");

      toggle.setAttribute("aria-expanded", String(isOpen));

      if (toggleLabel) {
        toggleLabel.textContent = isOpen
          ? "Sluit externe tools"
          : "Open externe tools";
      }
    });
  }


  /* =======================================================
     MODAL OPENEN
     ======================================================= */

  function openModal(toolName, triggerElement) {
    const tool = tools[toolName];

    if (!tool || !modal) {
      return;
    }

    activeTool = toolName;
    lastFocusedElement = triggerElement;

    const triggerLogo = triggerElement.querySelector(".tool-dock__icon-image");

    modalLogo.src = triggerLogo ? triggerLogo.src : "";
    modalTitle.textContent = tool.title;
    modalSubmit.textContent = tool.submitLabel;

    modalIntro.textContent = "Vul je GitHub-gebruikersnaam in.";
    modalLabel.textContent = "GitHub-gebruikersnaam";

    modalInput.type = "text";
    modalInput.inputMode = "text";
    modalInput.removeAttribute("pattern");
    modalInput.autocomplete = "username";
    modalInput.placeholder = "Bijvoorbeeld onc-123456";

    modalInput.value = lastGithubUsername;

    modalError.textContent =
      "Vul een geldige GitHub-gebruikersnaam in.";

    modalError.hidden = true;

    modal.hidden = false;
    document.body.classList.add("tool-access-modal-open");

    window.requestAnimationFrame(() => {
      modal.classList.add("is-visible");

      modalInput.focus();

      if (modalInput.value) {
        modalInput.select();
      }
    });
  }


  /* =======================================================
     MODAL SLUITEN
     ======================================================= */

  function closeModal() {
    if (!modal || modal.hidden) {
      return;
    }

    modal.classList.remove("is-visible");
    document.body.classList.remove("tool-access-modal-open");

    window.setTimeout(() => {
      modal.hidden = true;
      activeTool = null;

      if (lastFocusedElement) {
        lastFocusedElement.focus();
      }
    }, 160);
  }


  /* =======================================================
     TOOL-KNOPPEN
     ======================================================= */

  studentToolButtons.forEach((button) => {
    button.addEventListener("click", () => {
      openModal(button.dataset.studentTool, button);
    });
  });


  /* =======================================================
     MODAL SLUITEN
     ======================================================= */

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeModal);
  });


  /* =======================================================
     GITHUB-GEBRUIKERSNAAM
     ======================================================= */

  if (modalInput) {
    modalInput.addEventListener("input", () => {
      modalInput.value = modalInput.value
        .replace(/[^A-Za-z0-9-]/g, "")
        .slice(0, 39);

      modalError.hidden = true;
    });
  }


  /* =======================================================
     OPEN DE JUISTE OMGEVING
     ======================================================= */

  if (modalForm) {
    modalForm.addEventListener("submit", (event) => {
      event.preventDefault();

      const githubUsername = modalInput.value.trim();

      if (!/^[A-Za-z0-9-]{1,39}$/.test(githubUsername)) {
        modalError.hidden = false;
        modalInput.focus();
        return;
      }

      const tool = tools[activeTool];

      if (!tool) {
        return;
      }

      lastGithubUsername = githubUsername;

      const url = tool.buildUrl(githubUsername);

      window.open(url, "_blank", "noopener,noreferrer");

      closeModal();
    });
  }


  /* =======================================================
     ESCAPE
     ======================================================= */

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal && !modal.hidden) {
      closeModal();
    }
  });
});


/* =========================================================
   AGENDA TOOL
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  const STORAGE_KEY = "module01.agenda.class";

  const CLASSES = [
    "Klas 1",
    "Klas 2",
    "Klas 3"
  ];

  const openButton =
    document.querySelector("[data-agenda-open]");

  const modal =
    document.querySelector("[data-agenda-modal]");

  const closeButtons =
    document.querySelectorAll("[data-agenda-close]");

  const picker =
    document.querySelector("[data-agenda-class-picker]");

  const classButtons =
    document.querySelector("[data-agenda-class-buttons]");

  const content =
    document.querySelector("[data-agenda-content]");

  const itemsContainer =
    document.querySelector("[data-agenda-items]");

  const classLabel =
    document.querySelector("[data-agenda-class-label]");

  const changeClassButton =
    document.querySelector("[data-agenda-change-class]");

  const viewButtons =
    document.querySelectorAll("[data-agenda-view]");

  const dock =
    document.querySelector("[data-tool-dock]");

  if (
    !openButton ||
    !modal ||
    !dock ||
    !picker ||
    !classButtons ||
    !content ||
    !itemsContainer
  ) {
    return;
  }

  const scheduleUrl =
    dock.dataset.agendaSource;

  let schedule = { weeks: {} };
  let lastFocusedElement = null;
  let activeView = "upcoming";


  /* =======================================================
     SCHEDULE INLEZEN
     ======================================================= */

  async function loadSchedule() {
    try {
      const response = await fetch(scheduleUrl);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const yamlText = await response.text();

      schedule =
        jsyaml.load(yamlText) || { weeks: {} };

      return true;
    } catch (error) {
      console.error(
        "Agenda: schedule.yml kon niet worden gelezen.",
        error
      );

      return false;
    }
  }


  /* =======================================================
     KLAS ONTHOUDEN
     ======================================================= */

  function getSavedClass() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
  }

  function saveClass(className) {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        className
      );
    } catch (_) {
      // localStorage kan geblokkeerd zijn.
    }
  }

  function clearClass() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (_) {
      // Niets te doen.
    }
  }


  /* =======================================================
     DATUM / TIJD
     ======================================================= */

  function parseLocalDateTime(value) {
    if (!value) {
      return null;
    }

    const match = String(value).match(
      /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})$/
    );

    if (!match) {
      return null;
    }

    return new Date(
      Number(match[1]),
      Number(match[2]) - 1,
      Number(match[3]),
      Number(match[4]),
      Number(match[5])
    );
  }

  function formatDay(date) {
    return new Intl.DateTimeFormat(
      "nl-NL",
      {
        weekday: "short",
        day: "numeric",
        month: "short"
      }
    ).format(date);
  }

  function formatTime(date) {
    return new Intl.DateTimeFormat(
      "nl-NL",
      {
        hour: "2-digit",
        minute: "2-digit"
      }
    ).format(date);
  }

  function startOfDay(date) {
    return new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    );
  }

  function startOfWeek(date) {
    const result = startOfDay(date);

    const day =
      result.getDay() === 0
        ? 7
        : result.getDay();

    result.setDate(
      result.getDate() - day + 1
    );

    return result;
  }

  function daysUntil(date) {
    const today =
      startOfDay(new Date());

    const target =
      startOfDay(date);

    return Math.ceil(
      (target - today) / 86400000
    );
  }


  /* =======================================================
     TEKST
     ======================================================= */

  function cleanTopic(topic) {
    return String(topic || "")
      .replace(/^vakflex\s*:\s*/i, "")
      .trim() || "VakFlex";
  }

  function getWeekTitle(weekNumber) {
    const week =
      schedule.weeks?.[weekNumber];

    return week?.title || `Week ${weekNumber}`;
  }


  /* =======================================================
     AGENDA DATA
     ======================================================= */

  function buildAgendaItems() {
    const now = new Date();
    const items = [];

    for (
      const [weekNumber, week]
      of Object.entries(schedule.weeks || {})
    ) {
      for (const vakflex of week.vakflex || []) {
        const date =
          parseLocalDateTime(vakflex.date);

        if (!date) {
          continue;
        }

        items.push({
          type: "vakflex",
          date,
          title: cleanTopic(vakflex.topic),
          subtitle: "VakFlex",
          week: Number(weekNumber)
        });
      }

      const deadline =
        parseLocalDateTime(
          week.pset?.deadline
        );

      if (deadline) {
        items.push({
          type: "deadline",
          date: deadline,
          title: "PSET",
          subtitle: `Deadline Week ${weekNumber}`,
          week: Number(weekNumber)
        });
      }
    }

    items.sort(
      (a, b) => a.date - b.date
    );

    if (activeView === "all") {
      return items;
    }

    return items.filter(
      (item) => item.date >= now
    );
  }


  /* =======================================================
     WEEKGROEP
     ======================================================= */

  function getGroupLabel(weekStart) {
    const currentWeek =
      startOfWeek(new Date());

    const difference =
      Math.round(
        (weekStart - currentWeek) /
        (7 * 86400000)
      );

    if (difference === 0) {
      return "Deze week";
    }

    if (difference === 1) {
      return "Volgende week";
    }

    if (difference === -1) {
      return "Vorige week";
    }

    return `Week ${getIsoWeekNumber(weekStart)}`;
  }

  function getIsoWeekNumber(date) {
    const temp =
      new Date(
        Date.UTC(
          date.getFullYear(),
          date.getMonth(),
          date.getDate()
        )
      );

    const day =
      temp.getUTCDay() || 7;

    temp.setUTCDate(
      temp.getUTCDate() + 4 - day
    );

    const yearStart =
      new Date(
        Date.UTC(
          temp.getUTCFullYear(),
          0,
          1
        )
      );

    return Math.ceil(
      (((temp - yearStart) / 86400000) + 1) / 7
    );
  }


  /* =======================================================
     ITEM MAKEN
     ======================================================= */

  function createAgendaItem(item) {
    const row =
      document.createElement("article");

    row.className =
      `agenda-item agenda-item--${item.type}`;


    const marker =
      document.createElement("span");

    marker.className =
      "agenda-item__marker";


    const body =
      document.createElement("div");

    body.className =
      "agenda-item__body";


    const title =
      document.createElement("p");

    title.className =
      "agenda-item__title";

    title.textContent =
      item.title;


    const subtitle =
      document.createElement("p");

    subtitle.className =
      "agenda-item__meta";

    subtitle.textContent =
      item.subtitle;


    body.append(
      title,
      subtitle
    );


    const when =
      document.createElement("div");

    when.className =
      "agenda-item__when";


    const day =
      document.createElement("span");

    day.className =
      "agenda-item__date";

    day.textContent =
      formatDay(item.date);


    const time =
      document.createElement("span");

    time.className =
      "agenda-item__time";

    time.textContent =
      formatTime(item.date);


    when.append(
      day,
      time
    );


    if (
      item.type === "deadline" &&
      item.date >= new Date()
    ) {
      const remaining =
        daysUntil(item.date);

      const badge =
        document.createElement("span");

      badge.className =
        "agenda-item__badge";

      badge.textContent =
        remaining === 0
          ? "Vandaag"
          : remaining === 1
            ? "Nog 1 dag"
            : `Nog ${remaining} dagen`;

      when.append(badge);
    }


    row.append(
      marker,
      body,
      when
    );

    return row;
  }


  /* =======================================================
     AGENDA TONEN
     ======================================================= */

  function renderAgenda(className) {
    picker.hidden = true;
    content.hidden = false;

    if (classLabel) {
      classLabel.hidden = false;
      classLabel.textContent = className;
    }

    itemsContainer.replaceChildren();

    const items =
      buildAgendaItems();

    if (items.length === 0) {
      const empty =
        document.createElement("p");

      empty.className =
        "agenda-modal__empty";

      empty.textContent =
        activeView === "all"
          ? "Er staan geen momenten in de agenda."
          : "Er staan geen komende momenten in de agenda.";

      itemsContainer.append(empty);

      return;
    }


    const groups = new Map();

    for (const item of items) {
      const weekStart =
        startOfWeek(item.date);

      const key =
        weekStart.getTime();

      if (!groups.has(key)) {
        groups.set(
          key,
          {
            weekStart,
            items: []
          }
        );
      }

      groups.get(key).items.push(item);
    }


    for (const group of groups.values()) {
      const firstItem =
        group.items[0];

      const section =
        document.createElement("section");

      section.className =
        "agenda-week";


      const header =
        document.createElement("header");

      header.className =
        "agenda-week__header";


      const label =
        document.createElement("h3");

      label.className =
        "agenda-week__title";

      label.textContent =
        getGroupLabel(group.weekStart);


      const context =
        document.createElement("p");

      context.className =
        "agenda-week__context";

      context.textContent =
        `Week ${firstItem.week} · ${getWeekTitle(firstItem.week)}`;


      header.append(
        label,
        context
      );


      const list =
        document.createElement("div");

      list.className =
        "agenda-week__items";


      for (const item of group.items) {
        list.append(
          createAgendaItem(item)
        );
      }


      section.append(
        header,
        list
      );

      itemsContainer.append(section);
    }
  }


  /* =======================================================
     KLAS KIEZEN
     ======================================================= */

  function showClassPicker() {
    content.hidden = true;
    picker.hidden = false;

    if (classLabel) {
      classLabel.hidden = true;
      classLabel.textContent = "";
    }
  }

  function chooseClass(className) {
    saveClass(className);
    renderAgenda(className);
  }


  /* =======================================================
     VIEW
     ======================================================= */

  function setView(view) {
    activeView = view;

    viewButtons.forEach((button) => {
      button.classList.toggle(
        "is-active",
        button.dataset.agendaView === view
      );
    });

    const savedClass =
      getSavedClass();

    if (
      savedClass &&
      CLASSES.includes(savedClass)
    ) {
      renderAgenda(savedClass);
    }
  }


  /* =======================================================
     OPENEN / SLUITEN
     ======================================================= */

  async function openAgenda() {
    await loadSchedule();

    lastFocusedElement =
      document.activeElement;

    const savedClass =
      getSavedClass();

    if (
      savedClass &&
      CLASSES.includes(savedClass)
    ) {
      renderAgenda(savedClass);
    } else {
      showClassPicker();
    }

    modal.hidden = false;

    document.body.classList.add(
      "agenda-modal-open"
    );

    requestAnimationFrame(() => {
      modal.classList.add("is-visible");
    });
  }

  function closeAgenda() {
    if (modal.hidden) {
      return;
    }

    modal.classList.remove(
      "is-visible"
    );

    document.body.classList.remove(
      "agenda-modal-open"
    );

    window.setTimeout(() => {
      modal.hidden = true;

      if (lastFocusedElement) {
        lastFocusedElement.focus();
      }
    }, 160);
  }


  /* =======================================================
     KLAS-KNOPPEN
     ======================================================= */

  for (const className of CLASSES) {
    const button =
      document.createElement("button");

    button.type = "button";

    button.className =
      "agenda-modal__class-button";

    button.textContent =
      className;

    button.addEventListener(
      "click",
      () => chooseClass(className)
    );

    classButtons.append(button);
  }


  /* =======================================================
     EVENTS
     ======================================================= */

  openButton.addEventListener(
    "click",
    openAgenda
  );

  closeButtons.forEach((button) => {
    button.addEventListener(
      "click",
      closeAgenda
    );
  });

  if (changeClassButton) {
    changeClassButton.addEventListener(
      "click",
      () => {
        clearClass();
        showClassPicker();
      }
    );
  }

  viewButtons.forEach((button) => {
    button.addEventListener(
      "click",
      () => setView(
        button.dataset.agendaView
      )
    );
  });

  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape" &&
        !modal.hidden
      ) {
        closeAgenda();
      }
    }
  );
});