document.addEventListener("DOMContentLoaded", () => {
  const dock = document.querySelector("[data-tool-dock]");
  const toggle = document.querySelector("[data-tool-dock-toggle]");

  const modal = document.querySelector("[data-tool-access-modal]");
  const modalLogo = document.querySelector("[data-tool-access-logo]");
  const modalTitle = document.querySelector("[data-tool-access-title]");
  const modalForm = document.querySelector("[data-tool-access-form]");
  const modalInput = document.querySelector("[data-tool-access-input]");
  const modalSubmit = document.querySelector("[data-tool-access-submit]");
  const modalError = document.querySelector("[data-tool-access-error]");

  const studentToolButtons = document.querySelectorAll("[data-student-tool]");
  const closeButtons = document.querySelectorAll("[data-tool-access-close]");

  let activeTool = null;
  let lastFocusedElement = null;
  let lastStudentNumber = "";

  const tools = {
    github: {
      title: "Open jouw GitHub",
      submitLabel: "Open GitHub",
      logo: "assets/images/tool-dock/github.png",

      buildUrl(studentNumber) {
        return `https://github.com/oncparkdreef/informatica-2627-onc-${studentNumber}`;
      }
    },

    codespaces: {
      title: "Open jouw Codespace",
      submitLabel: "Open Codespace",
      logo: "assets/images/tool-dock/codespaces.png",

      buildUrl(studentNumber) {
        return `https://codespaces.new/oncparkdreef/informatica-2627-onc-${studentNumber}?quickstart=1`;
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

    modalInput.value = lastStudentNumber;
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


  studentToolButtons.forEach((button) => {
    button.addEventListener("click", () => {
      openModal(button.dataset.studentTool, button);
    });
  });


  closeButtons.forEach((button) => {
    button.addEventListener("click", closeModal);
  });


  /* =======================================================
     ALLEEN CIJFERS
     ======================================================= */

  if (modalInput) {
    modalInput.addEventListener("input", () => {
      modalInput.value = modalInput.value.replace(/\D/g, "");
      modalError.hidden = true;
    });
  }


  /* =======================================================
     OPEN DE JUISTE OMGEVING
     ======================================================= */

  if (modalForm) {
    modalForm.addEventListener("submit", (event) => {
      event.preventDefault();

      const studentNumber = modalInput.value.trim();

      if (!/^\d+$/.test(studentNumber)) {
        modalError.hidden = false;
        modalInput.focus();
        return;
      }

      const tool = tools[activeTool];

      if (!tool) {
        return;
      }

      lastStudentNumber = studentNumber;

      const url = tool.buildUrl(studentNumber);

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

