/* =========================================================
   NEXUS EXPENSE TRACKER
   PREMIUM APPLICATION JAVASCRIPT
   ---------------------------------------------------------
   Philosophy:
   - Progressive enhancement
   - Defensive DOM handling
   - Zero dependency beyond Chart.js where available
   - Preserve existing backend APIs
   - Premium micro-interactions
   - Motion + accessibility
   - Voice transactions
   - Communication Center
   - Dashboard intelligence
   ========================================================= */

"use strict";


/* =========================================================
   NEXUS GLOBAL CONFIGURATION
   ========================================================= */

window.Nexus = window.Nexus || {};

Nexus.config = {
  animationDuration: 420,
  toastDuration: 3200,
  counterDuration: 1000,
  reducedMotion:
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
};


/* =========================================================
   APPLICATION BOOTSTRAP
   ========================================================= */

window.addEventListener("DOMContentLoaded", () => {
  Nexus.init();
});


Nexus.init = function () {
  initToastSystem();
  initPageTransitions();
  initRevealAnimations();
  initInteractiveCards();
  initButtonInteractions();
  initNavigationInteractions();
  initModalSystem();
  initDropdownSystem();
  initTooltips();
  initAnimatedCounters();
  initProgressIndicators();
  initScrollEffects();
  initKeyboardShortcuts();
  initCommandPalette();
  initCopyButtons();
  initAutoResizeTextareas();

  initNexusCharts();
  initNexusVoice();
  initCommunicationCenter();

  /*
   * Give the browser one frame to paint the page before
   * removing the boot state. This prevents a harsh first render.
   */
  requestAnimationFrame(() => {
    document.documentElement.classList.add("nexus-ready");
  });
};


/* =========================================================
   UTILITY HELPERS
   ========================================================= */

function qs(selector, parent = document) {
  return parent.querySelector(selector);
}


function qsa(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}


function escapeHTML(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}


function prefersReducedMotion() {
  return (
    Nexus.config.reducedMotion ||
    document.documentElement.classList.contains(
      "reduce-motion"
    )
  );
}


function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}


/* =========================================================
   TOAST SYSTEM
   ========================================================= */

function initToastSystem() {
  qsa(".toast").forEach((toast) => {
    scheduleToastRemoval(toast);
  });
}


function scheduleToastRemoval(toast) {
  if (!toast) return;

  setTimeout(() => {
    toast.classList.add("hide");

    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 450);
  }, Nexus.config.toastDuration);
}


window.NexusToast = {
  show(message, type = "info", duration = 3200) {
    let container = qs("#nexusToastContainer");

    if (!container) {
      container = document.createElement("div");
      container.id = "nexusToastContainer";
      container.className = "nexus-toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");

    toast.className = `toast nexus-dynamic-toast ${type}`;

    const iconMap = {
      success: "✓",
      error: "!",
      warning: "⚠",
      info: "i"
    };

    toast.innerHTML = `
      <span class="toast-icon">
        ${iconMap[type] || "i"}
      </span>
      <span class="toast-message"></span>
      <button
        type="button"
        class="toast-close"
        aria-label="Close notification"
      >×</button>
    `;

    const messageNode =
      qs(".toast-message", toast);

    if (messageNode) {
      messageNode.textContent = message;
    }

    qs(".toast-close", toast)?.addEventListener(
      "click",
      () => {
        toast.classList.add("hide");
        setTimeout(() => toast.remove(), 350);
      }
    );

    container.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add("visible");
    });

    setTimeout(() => {
      toast.classList.add("hide");

      setTimeout(() => {
        toast.remove();
      }, 400);
    }, duration);
  }
};


/* =========================================================
   PAGE TRANSITIONS
   ========================================================= */

function initPageTransitions() {
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a");

    if (!link) return;

    const href = link.getAttribute("href");

    if (
      !href ||
      href.startsWith("#") ||
      href.startsWith("javascript:") ||
      href.startsWith("mailto:") ||
      href.startsWith("tel:") ||
      link.target === "_blank" ||
      link.hasAttribute("download") ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }

    if (
      href.startsWith("http://") ||
      href.startsWith("https://")
    ) {
      try {
        if (
          new URL(href, window.location.href).origin !==
          window.location.origin
        ) {
          return;
        }
      } catch (_) {
        return;
      }
    }

    if (prefersReducedMotion()) {
      return;
    }

    document.documentElement.classList.add(
      "nexus-page-leaving"
    );
  });
}


/* =========================================================
   REVEAL ANIMATIONS
   ========================================================= */

function initRevealAnimations() {
  const elements = qsa(
    "[data-reveal], .reveal, .animate-on-scroll"
  );

  if (!elements.length) {
    return;
  }

  if (
    prefersReducedMotion() ||
    !("IntersectionObserver" in window)
  ) {
    elements.forEach((el) => {
      el.classList.add("revealed");
    });

    return;
  }

  const observer =
    new IntersectionObserver(
      (entries, observerInstance) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }

          entry.target.classList.add("revealed");

          observerInstance.unobserve(
            entry.target
          );
        });
      },
      {
        threshold: 0.08,
        rootMargin: "0px 0px -40px 0px"
      }
    );

  elements.forEach((el, index) => {
    el.style.setProperty(
      "--nexus-reveal-delay",
      `${Math.min(index * 45, 450)}ms`
    );

    observer.observe(el);
  });
}


/* =========================================================
   INTERACTIVE CARDS
   ========================================================= */

function initInteractiveCards() {
  const cards = qsa(
    ".card, .stat-card, .dashboard-card, .metric-card, [data-tilt]"
  );

  if (!cards.length || prefersReducedMotion()) {
    return;
  }

  cards.forEach((card) => {
    if (
      card.dataset.nexusInteractiveInitialized === "true"
    ) {
      return;
    }

    card.dataset.nexusInteractiveInitialized = "true";

    card.addEventListener("pointermove", (event) => {
      if (window.innerWidth < 768) {
        return;
      }

      const rect = card.getBoundingClientRect();

      const x =
        (event.clientX - rect.left) /
        rect.width;

      const y =
        (event.clientY - rect.top) /
        rect.height;

      const rotateX =
        (0.5 - y) * 3.5;

      const rotateY =
        (x - 0.5) * 3.5;

      card.style.setProperty(
        "--nexus-mouse-x",
        `${x * 100}%`
      );

      card.style.setProperty(
        "--nexus-mouse-y",
        `${y * 100}%`
      );

      card.style.transform =
        `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
    });

    card.addEventListener("pointerleave", () => {
      card.style.transform = "";
    });
  });
}


/* =========================================================
   BUTTON MICRO-INTERACTIONS
   ========================================================= */

function initButtonInteractions() {
  document.addEventListener("click", (event) => {
    const button =
      event.target.closest(
        "button, .btn, .primary-btn, .secondary-btn, [role='button']"
      );

    if (!button || prefersReducedMotion()) {
      return;
    }

    const rect =
      button.getBoundingClientRect();

    const ripple =
      document.createElement("span");

    ripple.className =
      "nexus-ripple";

    const size =
      Math.max(
        rect.width,
        rect.height
      );

    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;

    ripple.style.left =
      `${event.clientX - rect.left - size / 2}px`;

    ripple.style.top =
      `${event.clientY - rect.top - size / 2}px`;

    button.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 650);
  });
}


/* =========================================================
   NAVIGATION INTERACTIONS
   ========================================================= */

function initNavigationInteractions() {
  const toggle =
    qs(
      "#sidebarToggle, #menuToggle, [data-sidebar-toggle]"
    );

  const sidebar =
    qs(
      "#sidebar, .sidebar, [data-sidebar]"
    );

  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      document.body.classList.toggle(
        "sidebar-open"
      );

      sidebar.classList.toggle(
        "open"
      );
    });
  }

  qsa(
    ".nav-link, .sidebar-link, [data-nav-link]"
  ).forEach((link) => {
    link.addEventListener("click", () => {
      qsa(
        ".nav-link.active, .sidebar-link.active, [data-nav-link].active"
      ).forEach((item) => {
        item.classList.remove("active");
      });

      link.classList.add("active");

      if (window.innerWidth < 900) {
        document.body.classList.remove(
          "sidebar-open"
        );

        sidebar?.classList.remove("open");
      }
    });
  });
}


/* =========================================================
   MODAL SYSTEM
   ========================================================= */

function initModalSystem() {
  document.addEventListener("click", (event) => {
    const opener =
      event.target.closest(
        "[data-modal-open]"
      );

    if (opener) {
      const id =
        opener.dataset.modalOpen;

      const modal =
        document.getElementById(id);

      if (modal) {
        openNexusModal(modal);
      }

      return;
    }

    const closer =
      event.target.closest(
        "[data-modal-close], .modal-close"
      );

    if (closer) {
      const modal =
        closer.closest(
          ".modal, [role='dialog']"
        );

      if (modal) {
        closeNexusModal(modal);
      }
    }

    if (
      event.target.matches(
        ".modal-backdrop, .modal"
      ) &&
      event.target.dataset.closeOnBackdrop === "true"
    ) {
      closeNexusModal(event.target);
    }
  });

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Escape") {
        return;
      }

      const modal =
        qs(
          ".modal.open, .modal.active, [role='dialog'].open"
        );

      if (modal) {
        closeNexusModal(modal);
      }
    }
  );
}


function openNexusModal(modal) {
  if (!modal) return;

  modal.hidden = false;

  requestAnimationFrame(() => {
    modal.classList.add("open", "active");
  });

  document.body.classList.add(
    "nexus-modal-open"
  );
}


function closeNexusModal(modal) {
  if (!modal) return;

  modal.classList.remove(
    "open",
    "active"
  );

  setTimeout(() => {
    modal.hidden = true;
  }, prefersReducedMotion() ? 0 : 250);

  document.body.classList.remove(
    "nexus-modal-open"
  );
}


window.NexusModal = {
  open: openNexusModal,
  close: closeNexusModal
};


/* =========================================================
   DROPDOWN SYSTEM
   ========================================================= */

function initDropdownSystem() {
  document.addEventListener("click", (event) => {
    const trigger =
      event.target.closest(
        "[data-dropdown-toggle]"
      );

    if (trigger) {
      const id =
        trigger.dataset.dropdownToggle;

      const dropdown =
        document.getElementById(id);

      if (!dropdown) {
        return;
      }

      const wasOpen =
        dropdown.classList.contains("open");

      closeAllDropdowns();

      if (!wasOpen) {
        dropdown.classList.add("open");
        trigger.setAttribute(
          "aria-expanded",
          "true"
        );
      }

      return;
    }

    if (
      !event.target.closest(
        ".dropdown, [data-dropdown]"
      )
    ) {
      closeAllDropdowns();
    }
  });
}


function closeAllDropdowns() {
  qsa(
    ".dropdown.open, [data-dropdown].open"
  ).forEach((dropdown) => {
    dropdown.classList.remove("open");
  });

  qsa(
    "[data-dropdown-toggle]"
  ).forEach((trigger) => {
    trigger.setAttribute(
      "aria-expanded",
      "false"
    );
  });
}


/* =========================================================
   TOOLTIP SYSTEM
   ========================================================= */

function initTooltips() {
  const elements = qsa(
    "[data-tooltip], [title]"
  );

  if (!elements.length) {
    return;
  }

  elements.forEach((element) => {
    if (
      element.dataset.nexusTooltipInitialized
    ) {
      return;
    }

    element.dataset.nexusTooltipInitialized =
      "true";

    const originalTitle =
      element.dataset.tooltip ||
      element.getAttribute("title");

    if (!originalTitle) {
      return;
    }

    element.dataset.nexusTooltip =
      originalTitle;

    if (
      element.hasAttribute("title")
    ) {
      element.removeAttribute("title");
    }

    element.addEventListener(
      "mouseenter",
      () => {
        showTooltip(
          element,
          originalTitle
        );
      }
    );

    element.addEventListener(
      "mouseleave",
      hideTooltip
    );

    element.addEventListener(
      "focus",
      () => {
        showTooltip(
          element,
          originalTitle
        );
      }
    );

    element.addEventListener(
      "blur",
      hideTooltip
    );
  });
}


let activeTooltip = null;


function showTooltip(element, text) {
  hideTooltip();

  const tooltip =
    document.createElement("div");

  tooltip.className =
    "nexus-tooltip";

  tooltip.textContent =
    text;

  document.body.appendChild(
    tooltip
  );

  const rect =
    element.getBoundingClientRect();

  tooltip.style.left =
    `${rect.left + rect.width / 2}px`;

  tooltip.style.top =
    `${rect.top - 10}px`;

  activeTooltip = tooltip;

  requestAnimationFrame(() => {
    tooltip.classList.add("visible");
  });
}


function hideTooltip() {
  if (!activeTooltip) {
    return;
  }

  activeTooltip.remove();
  activeTooltip = null;
}


/* =========================================================
   ANIMATED NUMBER COUNTERS
   ========================================================= */

function initAnimatedCounters() {
  const counters = qsa(
    "[data-counter], [data-count]"
  );

  if (!counters.length) {
    return;
  }

  if (
    prefersReducedMotion()
  ) {
    counters.forEach((element) => {
      const value =
        element.dataset.counter ||
        element.dataset.count;

      element.textContent =
        formatCounterValue(
          Number(value),
          element
        );
    });

    return;
  }

  if (!("IntersectionObserver" in window)) {
    counters.forEach(
      animateCounter
    );

    return;
  }

  const observer =
    new IntersectionObserver(
      (entries, observerInstance) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }

          animateCounter(
            entry.target
          );

          observerInstance.unobserve(
            entry.target
          );
        });
      },
      {
        threshold: 0.35
      }
    );

  counters.forEach((counter) => {
    observer.observe(counter);
  });
}


function animateCounter(element) {
  if (
    element.dataset.counterAnimated ===
    "true"
  ) {
    return;
  }

  element.dataset.counterAnimated =
    "true";

  const target =
    Number(
      element.dataset.counter ??
      element.dataset.count
    );

  if (!Number.isFinite(target)) {
    return;
  }

  const duration =
    Number(
      element.dataset.counterDuration
    ) ||
    Nexus.config.counterDuration;

  const startTime =
    performance.now();

  function frame(now) {
    const progress =
      Math.min(
        (now - startTime) /
        duration,
        1
      );

    const eased =
      1 -
      Math.pow(
        1 - progress,
        3
      );

    const value =
      target * eased;

    element.textContent =
      formatCounterValue(
        value,
        element
      );

    if (progress < 1) {
      requestAnimationFrame(frame);
    }
  }

  requestAnimationFrame(frame);
}


function formatCounterValue(
  value,
  element
) {
  const prefix =
    element?.dataset?.prefix ||
    "";

  const suffix =
    element?.dataset?.suffix ||
    "";

  const decimals =
    Number(
      element?.dataset?.decimals
    );

  const hasDecimals =
    Number.isFinite(decimals);

  const formatted =
    new Intl.NumberFormat(
      "en-IN",
      hasDecimals
        ? {
            minimumFractionDigits:
              decimals,
            maximumFractionDigits:
              decimals
          }
        : {
            maximumFractionDigits: 2
          }
    ).format(value);

  return `${prefix}${formatted}${suffix}`;
}


/* =========================================================
   PROGRESS INDICATORS
   ========================================================= */

function initProgressIndicators() {
  qsa(
    "[data-progress]"
  ).forEach((element) => {
    const value =
      Number(
        element.dataset.progress
      );

    if (!Number.isFinite(value)) {
      return;
    }

    const percentage =
      Math.max(
        0,
        Math.min(
          100,
          value
        )
      );

    element.style.setProperty(
      "--progress",
      `${percentage}%`
    );

    if (
      element.tagName === "PROGRESS"
    ) {
      element.value =
        percentage;
    }
  });
}


/* =========================================================
   SCROLL EFFECTS
   ========================================================= */

function initScrollEffects() {
  const header =
    qs(
      ".topbar, .navbar, header[data-sticky]"
    );

  if (!header) {
    return;
  }

  let ticking = false;

  const update =
    () => {
      const scrolled =
        window.scrollY > 12;

      header.classList.toggle(
        "scrolled",
        scrolled
      );

      ticking = false;
    };

  window.addEventListener(
    "scroll",
    () => {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    },
    {
      passive: true
    }
  );

  update();
}


/* =========================================================
   KEYBOARD SHORTCUTS
   ========================================================= */

function initKeyboardShortcuts() {
  document.addEventListener(
    "keydown",
    (event) => {
      /*
       * Ctrl/Cmd + K
       * Open command palette.
       */
      if (
        (event.ctrlKey ||
          event.metaKey) &&
        event.key.toLowerCase() === "k"
      ) {
        event.preventDefault();

        if (
          window.NexusCommandPalette
        ) {
          NexusCommandPalette.open();
        }
      }

      /*
       * /
       * Focus search when the user isn't typing.
       */
      if (
        event.key === "/" &&
        !isTypingTarget(event.target)
      ) {
        const search =
          qs(
            "#globalSearch, #searchInput, input[type='search']"
          );

        if (search) {
          event.preventDefault();
          search.focus();
        }
      }
    }
  );
}


function isTypingTarget(element) {
  if (!element) {
    return false;
  }

  const tag =
    element.tagName;

  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    element.isContentEditable
  );
}


/* =========================================================
   COMMAND PALETTE
   ========================================================= */

function initCommandPalette() {
  const palette =
    qs("#commandPalette");

  if (!palette) {
    return;
  }

  const input =
    qs(
      "#commandPaletteInput",
      palette
    );

  const items =
    qsa(
      "[data-command]",
      palette
    );

  function filter() {
    const query =
      (input?.value || "")
        .trim()
        .toLowerCase();

    items.forEach((item) => {
      const text =
        item.textContent
          .toLowerCase();

      item.hidden =
        query &&
        !text.includes(query);
    });
  }

  input?.addEventListener(
    "input",
    filter
  );

  palette.addEventListener(
    "click",
    (event) => {
      if (
        event.target === palette ||
        event.target.closest(
          "[data-command-close]"
        )
      ) {
        close();
      }
    }
  );

  function open() {
    palette.hidden = false;

    requestAnimationFrame(() => {
      palette.classList.add(
        "open",
        "active"
      );

      input?.focus();
    });
  }

  function close() {
    palette.classList.remove(
      "open",
      "active"
    );

    setTimeout(() => {
      palette.hidden = true;
    }, prefersReducedMotion() ? 0 : 220);
  }

  window.NexusCommandPalette = {
    open,
    close
  };
}


/* =========================================================
   COPY BUTTONS
   ========================================================= */

function initCopyButtons() {
  document.addEventListener(
    "click",
    async (event) => {
      const button =
        event.target.closest(
          "[data-copy]"
        );

      if (!button) {
        return;
      }

      const value =
        button.dataset.copy;

      if (!value) {
        return;
      }

      try {
        await navigator.clipboard.writeText(
          value
        );

        const original =
          button.textContent;

        button.textContent =
          "Copied ✓";

        setTimeout(() => {
          button.textContent =
            original;
        }, 1400);

      } catch (_) {
        NexusToast.show(
          "Unable to copy to clipboard.",
          "error"
        );
      }
    }
  );
}


/* =========================================================
   AUTO-RESIZE TEXTAREAS
   ========================================================= */

function initAutoResizeTextareas() {
  qsa(
    "textarea[data-autoresize]"
  ).forEach((textarea) => {
    const resize = () => {
      textarea.style.height =
        "auto";

      textarea.style.height =
        `${textarea.scrollHeight}px`;
    };

    textarea.addEventListener(
      "input",
      resize
    );

    resize();
  });
}


/* =========================================================
   NEXUS CHARTS
   ========================================================= */

window.NexusCharts = {

  instances: {},

  base() {
    return {
      responsive: true,
      maintainAspectRatio: false,

      interaction: {
        intersect: false,
        mode: "index"
      },

      animation: {
        duration:
          prefersReducedMotion()
            ? 0
            : 900,
        easing: "easeOutQuart"
      },

      plugins: {
        legend: {
          labels: {
            color: "#a7afc5",
            usePointStyle: true,
            padding: 18,
            font: {
              family:
                "Inter, system-ui, sans-serif"
            }
          }
        },

        tooltip: {
          backgroundColor:
            "rgba(15,18,30,.96)",

          borderColor:
            "rgba(255,255,255,.08)",

          borderWidth: 1,

          titleColor:
            "#ffffff",

          bodyColor:
            "#b8bfd1",

          padding: 12,

          cornerRadius: 10,

          displayColors: true
        }
      },

      scales: {
        x: {
          border: {
            display: false
          },

          ticks: {
            color: "#737b91"
          },

          grid: {
            color:
              "rgba(255,255,255,.045)"
          }
        },

        y: {
          border: {
            display: false
          },

          ticks: {
            color: "#737b91"
          },

          grid: {
            color:
              "rgba(255,255,255,.045)"
          }
        }
      }
    };
  },


  destroy(id) {
    if (
      this.instances[id]
    ) {
      this.instances[id].destroy();
      delete this.instances[id];
    }
  },


  donut(
    id,
    labels,
    values
  ) {
    const canvas =
      document.getElementById(id);

    if (
      !canvas ||
      typeof Chart ===
        "undefined"
    ) {
      return null;
    }

    this.destroy(id);

    const chart =
      new Chart(
        canvas,
        {
          type: "doughnut",

          data: {
            labels,

            datasets: [
              {
                data: values,

                borderWidth: 0,

                hoverOffset: 7,

                backgroundColor: [
                  "#7c5cff",
                  "#00e5ff",
                  "#25d695",
                  "#ffb84d",
                  "#ff5c8a",
                  "#6c7bff",
                  "#b66dff",
                  "#46d9c5",
                  "#8892a8"
                ]
              }
            ]
          },

          options: {
            responsive: true,
            maintainAspectRatio: false,

            cutout: "72%",

            animation: {
              animateRotate:
                !prefersReducedMotion(),
              duration:
                prefersReducedMotion()
                  ? 0
                  : 900
            },

            plugins: {
              legend: {
                position:
                  "bottom",

                labels: {
                  color:
                    "#a7afc5",

                  padding: 16,

                  usePointStyle:
                    true
                }
              },

              tooltip: {
                callbacks: {
                  label(context) {
                    const value =
                      context.raw;

                    return ` ${context.label}: ₹${Number(
                      value
                    ).toLocaleString(
                      "en-IN"
                    )}`;
                  }
                }
              }
            }
          }
        }
      );

    this.instances[id] =
      chart;

    return chart;
  },


  line(
    id,
    labels,
    income,
    expense
  ) {
    const canvas =
      document.getElementById(id);

    if (
      !canvas ||
      typeof Chart ===
        "undefined"
    ) {
      return null;
    }

    this.destroy(id);

    const options =
      this.base();

    const chart =
      new Chart(
        canvas,
        {
          type: "line",

          data: {
            labels,

            datasets: [
              {
                label:
                  "Income",

                data:
                  income,

                borderColor:
                  "#25d695",

                backgroundColor:
                  "rgba(37,214,149,.08)",

                fill: true,

                tension:
                  0.42,

                pointRadius:
                  3,

                pointHoverRadius:
                  6,

                borderWidth:
                  2
              },

              {
                label:
                  "Expense",

                data:
                  expense,

                borderColor:
                  "#7c5cff",

                backgroundColor:
                  "rgba(124,92,255,.08)",

                fill: true,

                tension:
                  0.42,

                pointRadius:
                  3,

                pointHoverRadius:
                  6,

                borderWidth:
                  2
              }
            ]
          },

          options
        }
      );

    this.instances[id] =
      chart;

    return chart;
  },


  bar(
    id,
    labels,
    values,
    label = "Amount"
  ) {
    const canvas =
      document.getElementById(id);

    if (
      !canvas ||
      typeof Chart ===
        "undefined"
    ) {
      return null;
    }

    this.destroy(id);

    const chart =
      new Chart(
        canvas,
        {
          type: "bar",

          data: {
            labels,

            datasets: [
              {
                label,

                data:
                  values,

                backgroundColor:
                  "rgba(124,92,255,.72)",

                borderRadius:
                  8,

                borderSkipped:
                  false
              }
            ]
          },

          options:
            this.base()
        }
      );

    this.instances[id] =
      chart;

    return chart;
  }
};


function initNexusCharts() {
  /*
   * Charts are intentionally not created automatically
   * from arbitrary page data.
   *
   * Existing dashboard templates can continue calling:
   *
   * NexusCharts.donut(...)
   * NexusCharts.line(...)
   * NexusCharts.bar(...)
   */
}


/* =========================================================
   NEXUS VOICE TRANSACTION SYSTEM
   ========================================================= */

function initNexusVoice() {
  const trigger =
    document.getElementById(
      "voiceTrigger"
    );

  const panel =
    document.getElementById(
      "voicePanel"
    );

  if (
    !trigger ||
    !panel
  ) {
    return;
  }

  const status =
    document.getElementById(
      "voiceStatus"
    );

  const transcript =
    document.getElementById(
      "voiceTranscript"
    );

  const liveDot =
    document.getElementById(
      "voiceLiveDot"
    );

  const triggerText =
    document.getElementById(
      "voiceTriggerText"
    );

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    trigger.addEventListener(
      "click",
      () => {
        panel.hidden =
          false;

        if (status) {
          status.textContent =
            "Voice input is not supported in this browser.";
        }

        if (transcript) {
          transcript.textContent =
            "Please use Google Chrome or another browser with Web Speech support.";
        }
      }
    );

    return;
  }

  let recognition =
    null;

  let listening =
    false;


  function setListeningState(
    active
  ) {
    listening =
      active;

    liveDot?.classList.toggle(
      "active",
      active
    );

    trigger.classList.toggle(
      "active",
      active
    );

    if (triggerText) {
      triggerText.textContent =
        active
          ? "Listening..."
          : "Voice";
    }

    if (status) {
      status.textContent =
        active
          ? "Listening..."
          : "Ready to listen";
    }
  }


  function showPanel() {
    panel.hidden =
      false;

    panel.classList.add(
      "open"
    );
  }


  function setStatus(
    message
  ) {
    if (status) {
      status.textContent =
        message;
    }
  }


  function setTranscript(
    message
  ) {
    if (transcript) {
      transcript.textContent =
        message;
    }
  }


  async function parseSpeech(
    text
  ) {
    setStatus(
      "Understanding transaction..."
    );

    setTranscript(
      `"${text}"`
    );

    try {
      const response =
        await fetch(
          "/api/voice/parse",
          {
            method:
              "POST",

            credentials:
              "same-origin",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                text
              })
          }
        );

      const result =
        await response.json();

      if (
        !response.ok ||
        !result.success
      ) {
        throw new Error(
          result.error ||
          result.message ||
          "Unable to understand the transaction."
        );
      }

      showVoiceConfirmation(
        result
      );

    } catch (error) {
      setStatus(
        "Could not understand"
      );

      setTranscript(
        error.message
      );

      removeVoiceActions();
    }
  }


  function removeVoiceActions() {
    qsa(
      ".nexus-voice-actions"
    ).forEach(
      (el) => el.remove()
    );
  }


  function showVoiceConfirmation(
    result
  ) {
    removeVoiceActions();

    setStatus(
      "Review before saving"
    );

    const amount =
      Number(
        result.amount
      );

    setTranscript(
      `${result.kind === "income"
        ? "Income"
        : "Expense"} • ₹${Number.isFinite(
        amount
      )
        ? amount.toFixed(2)
        : "0.00"} • ${result.category || "Uncategorized"} • ${
        result.payment_method ||
        "Unknown"
      } • ${
        result.transaction_date ||
        "Today"
      }`
    );

    const actions =
      document.createElement(
        "div"
      );

    actions.className =
      "nexus-voice-actions";

    actions.style.display =
      "flex";

    actions.style.gap =
      "10px";

    actions.style.marginTop =
      "14px";

    actions.style.flexWrap =
      "wrap";


    const confirm =
      document.createElement(
        "button"
      );

    confirm.type =
      "button";

    confirm.className =
      "primary-btn";

    confirm.textContent =
      "✓ Confirm transaction";


    const reject =
      document.createElement(
        "button"
      );

    reject.type =
      "button";

    reject.className =
      "secondary-btn";

    reject.textContent =
      "Cancel";


    confirm.addEventListener(
      "click",
      async () => {
        confirm.disabled =
          true;

        reject.disabled =
          true;

        setStatus(
          "Saving transaction..."
        );

        try {
          const response =
            await fetch(
              "/api/voice/confirm",
              {
                method:
                  "POST",

                credentials:
                  "same-origin",

                headers: {
                  "Content-Type":
                    "application/json"
                },

                body:
                  JSON.stringify({
                    voice_command_id:
                      result.voice_command_id
                  })
              }
            );

          const data =
            await response.json();

          if (
            !response.ok ||
            !data.success
          ) {
            throw new Error(
              data.error ||
              data.message ||
              "Unable to save transaction."
            );
          }

          setStatus(
            "Transaction saved"
          );

          setTranscript(
            "✓ Voice transaction added successfully."
          );

          NexusToast.show(
            "Transaction added successfully.",
            "success"
          );

          setTimeout(
            () => {
              window.location.reload();
            },
            800
          );

        } catch (error) {
          confirm.disabled =
            false;

          reject.disabled =
            false;

          setStatus(
            "Save failed"
          );

          setTranscript(
            error.message
          );
        }
      }
    );


    reject.addEventListener(
      "click",
      async () => {
        try {
          await fetch(
            "/api/voice/reject",
            {
              method:
                "POST",

              credentials:
                "same-origin",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  voice_command_id:
                    result.voice_command_id
                })
            }
          );
        } catch (_) {
          /*
           * Logging failure should never
           * prevent the UI from recovering.
           */
        }

        removeVoiceActions();

        setStatus(
          "Ready to listen"
        );

        setTranscript(
          'Try: "Spent 500 on dinner using UPI."'
        );
      }
    );


    actions.appendChild(
      confirm
    );

    actions.appendChild(
      reject
    );

    panel.appendChild(
      actions
    );
  }


  function startRecognition() {
    if (listening) {
      recognition?.stop();
      return;
    }

    showPanel();

    recognition =
      new SpeechRecognition();

    recognition.lang =
      "en-IN";

    recognition.continuous =
      false;

    recognition.interimResults =
      true;

    recognition.maxAlternatives =
      1;


    recognition.onstart =
      () => {
        setListeningState(
          true
        );

        setStatus(
          "Listening..."
        );

        setTranscript(
          "Speak your transaction now..."
        );
      };


    recognition.onresult =
      (event) => {
        let finalText =
          "";

        let interimText =
          "";

        for (
          let i =
            event.resultIndex;
          i <
            event.results.length;
          i++
        ) {
          const text =
            event.results[i][0]
              .transcript;

          if (
            event.results[i]
              .isFinal
          ) {
            finalText +=
              text;
          } else {
            interimText +=
              text;
          }
        }

        if (
          interimText.trim()
        ) {
          setTranscript(
            `"${interimText.trim()}"`
          );
        }

        if (
          finalText.trim()
        ) {
          setTranscript(
            `"${finalText.trim()}"`
          );

          parseSpeech(
            finalText.trim()
          );
        }
      };


    recognition.onerror =
      (event) => {
        setListeningState(
          false
        );

        const messages = {
          "not-allowed":
            "Microphone permission was denied. Allow microphone access and try again.",

          "audio-capture":
            "No microphone was detected.",

          "no-speech":
            "No speech detected. Try again.",

          "network":
            "Speech recognition needs a network connection in this browser."
        };

        setStatus(
          "Voice input error"
        );

        setTranscript(
          messages[
            event.error
          ] ||
          `Voice recognition error: ${event.error}`
        );
      };


    recognition.onend =
      () => {
        setListeningState(
          false
        );
      };


    try {
      recognition.start();
    } catch (error) {
      setListeningState(
        false
      );

      setStatus(
        "Unable to start microphone"
      );

      setTranscript(
        error.message
      );
    }
  }


  trigger.addEventListener(
    "click",
    startRecognition
  );
}


/* =========================================================
   COMMUNICATION CENTER
   Email + SMS + History
   ========================================================= */

function initCommunicationCenter() {
  const emailForm =
    document.getElementById(
      "emailSendForm"
    );

  const smsForm =
    document.getElementById(
      "smsSendForm"
    );

  const historyContainer =
    document.getElementById(
      "communicationHistory"
    );

  if (
    !emailForm &&
    !smsForm &&
    !historyContainer
  ) {
    return;
  }

  initEmailForm();
  initSmsForm();
  initCommunicationRefresh();
  initSmsCounter();

  if (historyContainer) {
    loadCommunicationHistory();
  }
}


/* =========================================================
   COMMUNICATION HELPERS
   ========================================================= */

function setCommunicationStatus(
  elementId,
  message,
  type = "info"
) {
  const element =
    document.getElementById(
      elementId
    );

  if (!element) {
    return;
  }

  element.textContent =
    message;

  element.dataset.status =
    type;

  element.classList.remove(
    "success",
    "error",
    "info",
    "loading"
  );

  if (type) {
    element.classList.add(
      type
    );
  }
}


function setButtonLoading(
  button,
  loading,
  loadingText,
  normalText
) {
  if (!button) {
    return;
  }

  button.disabled =
    loading;

  if (loading) {
    button.dataset.originalText =
      button.textContent ||
      normalText ||
      "";

    button.textContent =
      loadingText ||
      "Sending...";

    button.classList.add(
      "loading"
    );
  } else {
    button.textContent =
      normalText ||
      button.dataset.originalText ||
      button.textContent;

    button.classList.remove(
      "loading"
    );

    delete button.dataset
      .originalText;
  }
}


/* =========================================================
   ROBUST JSON REQUEST HELPER
   ========================================================= */

async function fetchJson(
  url,
  options = {}
) {
  let response;

  try {
    response =
      await fetch(
        url,
        {
          credentials:
            "same-origin",
          ...options
        }
      );
  } catch (networkError) {
    throw new Error(
      networkError?.message ||
      "Network error. Please make sure the NEXUS server is running."
    );
  }

  const contentType =
    response.headers.get(
      "content-type"
    ) || "";

  let data =
    null;

  let rawText =
    "";

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    try {
      data =
        await response.json();
    } catch (_) {
      data =
        null;
    }
  } else {
    try {
      rawText =
        await response.text();
    } catch (_) {
      rawText =
        "";
    }
  }

  if (!response.ok) {
    const serverError =
      data?.error ||
      data?.message ||
      rawText ||
      `Request failed with status ${response.status}.`;

    throw new Error(
      String(serverError)
    );
  }

  if (!data) {
    throw new Error(
      rawText ||
      "The server returned an invalid response."
    );
  }

  if (
    data.success === false
  ) {
    const serverError =
      data.error ||
      data.message ||
      "The server rejected the request.";

    throw new Error(
      String(serverError)
    );
  }

  return data;
}


/* =========================================================
   COMMUNICATION DATE FORMAT
   ========================================================= */

function formatCommunicationDate(
  value
) {
  if (!value) {
    return "Unknown time";
  }

  const raw =
    String(value);

  let normalized =
    raw;

  if (
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(
      raw
    )
  ) {
    normalized =
      raw.replace(
        " ",
        "T"
      ) + "Z";
  }

  const date =
    new Date(
      normalized
    );

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return raw;
  }

  return new Intl.DateTimeFormat(
    "en-IN",
    {
      dateStyle:
        "medium",

      timeStyle:
        "short"
    }
  ).format(date);
}


function communicationStatusLabel(
  status
) {
  const normalized =
    String(
      status || ""
    ).toLowerCase();

  if (
    normalized ===
    "sent"
  ) {
    return "Sent";
  }

  if (
    normalized ===
    "failed"
  ) {
    return "Failed";
  }

  if (
    normalized ===
    "queued"
  ) {
    return "Queued";
  }

  return normalized
    ? normalized
        .charAt(0)
        .toUpperCase() +
      normalized.slice(1)
    : "Unknown";
}


/* =========================================================
   EMAIL FORM
   ========================================================= */

function initEmailForm() {
  const form =
    document.getElementById(
      "emailSendForm"
    );

  if (!form) {
    return;
  }

  form.addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();

      const recipient =
        document
          .getElementById(
            "emailRecipient"
          )
          ?.value
          .trim() ||
        "";

      const subject =
        document
          .getElementById(
            "emailSubject"
          )
          ?.value
          .trim() ||
        "";

      const message =
        document
          .getElementById(
            "emailMessage"
          )
          ?.value
          .trim() ||
        "";

      const button =
        document.getElementById(
          "emailSendButton"
        );


      if (!recipient) {
        setCommunicationStatus(
          "emailFormStatus",
          "Please enter a recipient email address.",
          "error"
        );

        document
          .getElementById(
            "emailRecipient"
          )
          ?.focus();

        return;
      }


      if (!subject) {
        setCommunicationStatus(
          "emailFormStatus",
          "Please enter an email subject.",
          "error"
        );

        document
          .getElementById(
            "emailSubject"
          )
          ?.focus();

        return;
      }


      if (!message) {
        setCommunicationStatus(
          "emailFormStatus",
          "Please enter a message.",
          "error"
        );

        document
          .getElementById(
            "emailMessage"
          )
          ?.focus();

        return;
      }


      setCommunicationStatus(
        "emailFormStatus",
        "Sending email...",
        "loading"
      );

      setButtonLoading(
        button,
        true,
        "Sending...",
        "Send Email"
      );


      try {
        const result =
          await fetchJson(
            "/api/email/send",
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  recipient,
                  subject,
                  message_body:
                    message
                })
            }
          );


        setCommunicationStatus(
          "emailFormStatus",
          result.message ||
            "Email sent successfully.",
          "success"
        );

        NexusToast.show(
          result.message ||
            "Email sent successfully.",
          "success"
        );


        const messageField =
          document.getElementById(
            "emailMessage"
          );

        if (messageField) {
          messageField.value =
            "";
        }


        await loadCommunicationHistory();

      } catch (error) {
        setCommunicationStatus(
          "emailFormStatus",
          error.message ||
            "Unable to send email.",
          "error"
        );
      } finally {
        setButtonLoading(
          button,
          false,
          "",
          "Send Email"
        );
      }
    }
  );
}


/* =========================================================
   SMS FORM
   ========================================================= */

function initSmsForm() {
  const form =
    document.getElementById(
      "smsSendForm"
    );

  if (!form) {
    return;
  }

  form.addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();

      const recipient =
        document
          .getElementById(
            "smsRecipient"
          )
          ?.value
          .trim() ||
        "";

      const message =
        document
          .getElementById(
            "smsMessage"
          )
          ?.value
          .trim() ||
        "";

      const button =
        document.getElementById(
          "smsSendButton"
        );


      if (!recipient) {
        setCommunicationStatus(
          "smsFormStatus",
          "Please enter a phone number in international format, e.g. +919876543210.",
          "error"
        );

        document
          .getElementById(
            "smsRecipient"
          )
          ?.focus();

        return;
      }


      if (!message) {
        setCommunicationStatus(
          "smsFormStatus",
          "Please enter an SMS message.",
          "error"
        );

        document
          .getElementById(
            "smsMessage"
          )
          ?.focus();

        return;
      }


      if (
        message.length >
        1600
      ) {
        setCommunicationStatus(
          "smsFormStatus",
          "SMS message is too long. Keep it within 1600 characters.",
          "error"
        );

        document
          .getElementById(
            "smsMessage"
          )
          ?.focus();

        return;
      }


      setCommunicationStatus(
        "smsFormStatus",
        "Sending SMS...",
        "loading"
      );

      setButtonLoading(
        button,
        true,
        "Sending...",
        "Send SMS"
      );


      try {
        const result =
          await fetchJson(
            "/api/sms/send",
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body:
                JSON.stringify({
                  recipient,
                  message_body:
                    message
                })
            }
          );


        setCommunicationStatus(
          "smsFormStatus",
          result.message ||
            "SMS sent successfully.",
          "success"
        );

        NexusToast.show(
          result.message ||
            "SMS sent successfully.",
          "success"
        );


        const messageField =
          document.getElementById(
            "smsMessage"
          );

        if (messageField) {
          messageField.value =
            "";
        }

        updateSmsCounter();

        await loadCommunicationHistory();

      } catch (error) {
        setCommunicationStatus(
          "smsFormStatus",
          error.message ||
            "Unable to send SMS.",
          "error"
        );
      } finally {
        setButtonLoading(
          button,
          false,
          "",
          "Send SMS"
        );
      }
    }
  );
}


/* =========================================================
   SMS CHARACTER COUNTER
   ========================================================= */

function initSmsCounter() {
  const message =
    document.getElementById(
      "smsMessage"
    );

  if (!message) {
    return;
  }

  message.addEventListener(
    "input",
    updateSmsCounter
  );

  updateSmsCounter();
}


function updateSmsCounter() {
  const message =
    document.getElementById(
      "smsMessage"
    );

  const counter =
    document.getElementById(
      "smsMessageCounter"
    );

  if (
    !message ||
    !counter
  ) {
    return;
  }

  const length =
    message.value.length;

  const maximum =
    Number(
      message.getAttribute(
        "maxlength"
      )
    ) || 1600;

  counter.textContent =
    `${length} / ${maximum}`;

  counter.classList.toggle(
    "warning",
    length >=
      Math.floor(
        maximum * 0.8
      )
  );

  counter.classList.toggle(
    "danger",
    length >= maximum
  );
}


/* =========================================================
   COMMUNICATION REFRESH
   ========================================================= */

function initCommunicationRefresh() {
  const button =
    document.getElementById(
      "communicationRefresh"
    );

  if (!button) {
    return;
  }

  button.addEventListener(
    "click",
    async () => {
      const originalText =
        button.textContent;

      button.disabled =
        true;

      button.classList.add(
        "loading"
      );

      button.textContent =
        "Refreshing...";

      try {
        await loadCommunicationHistory();
      } finally {
        button.disabled =
          false;

        button.classList.remove(
          "loading"
        );

        button.textContent =
          originalText ||
          "Refresh";
      }
    }
  );
}


/* =========================================================
   COMMUNICATION HISTORY
   ========================================================= */

async function loadCommunicationHistory() {
  const container =
    document.getElementById(
      "communicationHistory"
    );

  if (!container) {
    return;
  }

  const loading =
    document.getElementById(
      "communicationLoading"
    );

  const empty =
    document.getElementById(
      "communicationEmpty"
    );


  if (loading) {
    loading.hidden =
      false;
  }

  if (empty) {
    empty.hidden =
      true;
  }


  setCommunicationStatus(
    "communicationHistoryStatus",
    "Loading communication history...",
    "loading"
  );


  try {
    const result =
      await fetchJson(
        "/api/communications/history"
      );

    const items =
      normalizeCommunicationHistory(
        result
      );

    renderCommunicationHistory(
      items
    );


    if (!items.length) {
      setCommunicationStatus(
        "communicationHistoryStatus",
        "No email or SMS activity yet.",
        "info"
      );
    } else {
      setCommunicationStatus(
        "communicationHistoryStatus",
        `${items.length} communication${
          items.length === 1
            ? ""
            : "s"
        } recorded.`,
        "success"
      );
    }

  } catch (error) {
    container.replaceChildren();

    if (empty) {
      empty.hidden =
        false;
    }

    setCommunicationStatus(
      "communicationHistoryStatus",
      error.message ||
        "Unable to load communication history.",
      "error"
    );

  } finally {
    if (loading) {
      loading.hidden =
        true;
    }
  }
}


/* =========================================================
   NORMALIZE API HISTORY
   ========================================================= */

function normalizeCommunicationHistory(
  data
) {
  let items =
    [];

  if (
    Array.isArray(
      data.items
    )
  ) {
    items =
      data.items.map(
        (item) => ({
          ...item,

          channel:
            item.channel ||
            item.type ||
            item.communication_type ||
            "communication"
        })
      );

  } else {

    if (
      Array.isArray(
        data.emails
      )
    ) {
      items.push(
        ...data.emails.map(
          (item) => ({
            ...item,
            channel:
              "email"
          })
        )
      );
    }


    if (
      Array.isArray(
        data.sms
      )
    ) {
      items.push(
        ...data.sms.map(
          (item) => ({
            ...item,
            channel:
              "sms"
          })
        )
      );
    }
  }


  items =
    items.map(
      (item) => {
        const channel =
          String(
            item.channel ||
              item.type ||
              ""
          ).toLowerCase();

        return {
          ...item,

          channel:
            channel.includes(
              "sms"
            )
              ? "sms"
              : "email"
        };
      }
    );


  items.sort(
    (a, b) => {
      const dateA =
        communicationTimestamp(
          a
        );

      const dateB =
        communicationTimestamp(
          b
        );

      return (
        dateB -
        dateA
      );
    }
  );


  return items;
}


function communicationTimestamp(
  item
) {
  const value =
    item.created_at ||
    item.sent_at ||
    item.timestamp ||
    item.date ||
    "";

  if (!value) {
    return 0;
  }

  let normalized =
    String(value);

  if (
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(
      normalized
    )
  ) {
    normalized =
      normalized.replace(
        " ",
        "T"
      ) +
      "Z";
  }

  const timestamp =
    new Date(
      normalized
    ).getTime();

  return Number.isNaN(
    timestamp
  )
    ? 0
    : timestamp;
}


/* =========================================================
   RENDER COMMUNICATION HISTORY
   ========================================================= */

function renderCommunicationHistory(
  items
) {
  const container =
    document.getElementById(
      "communicationHistory"
    );

  const empty =
    document.getElementById(
      "communicationEmpty"
    );

  if (!container) {
    return;
  }

  container.replaceChildren();


  if (!items.length) {
    if (empty) {
      empty.hidden =
        false;
    }

    return;
  }


  if (empty) {
    empty.hidden =
      true;
  }


  const fragment =
    document.createDocumentFragment();


  items.forEach(
    (item) => {
      fragment.appendChild(
        createCommunicationHistoryItem(
          item
        )
      );
    }
  );


  container.appendChild(
    fragment
  );
}


/* =========================================================
   HISTORY ITEM
   ========================================================= */

function createCommunicationHistoryItem(
  item
) {
  const channel =
    item.channel ===
    "sms"
      ? "sms"
      : "email";

  const status =
    String(
      item.status ||
        "unknown"
    ).toLowerCase();


  const article =
    document.createElement(
      "article"
    );

  article.className =
    "communication-history-item";

  article.dataset.channel =
    channel;

  article.dataset.status =
    status;


  const icon =
    document.createElement(
      "div"
    );

  icon.className =
    "communication-history-item-icon";

  icon.textContent =
    channel === "sms"
      ? "SMS"
      : "✉";


  const main =
    document.createElement(
      "div"
    );

  main.className =
    "communication-history-item-main";


  const heading =
    document.createElement(
      "div"
    );

  heading.className =
    "communication-history-item-heading";


  const title =
    document.createElement(
      "strong"
    );

  title.className =
    "communication-history-item-title";

  title.textContent =
    channel === "sms"
      ? "SMS"
      : "Email";


  const statusBadge =
    document.createElement(
      "span"
    );

  statusBadge.className =
    "communication-history-status";

  statusBadge.dataset.status =
    status;

  statusBadge.textContent =
    communicationStatusLabel(
      status
    );


  heading.appendChild(
    title
  );

  heading.appendChild(
    statusBadge
  );


  const recipient =
    document.createElement(
      "div"
    );

  recipient.className =
    "communication-history-recipient";

  recipient.textContent =
    item.recipient ||
    item.to ||
    "Unknown recipient";


  main.appendChild(
    heading
  );

  main.appendChild(
    recipient
  );


  if (
    channel ===
      "email" &&
    (item.subject ||
      "").trim()
  ) {
    const subject =
      document.createElement(
        "div"
      );

    subject.className =
      "communication-history-subject";

    subject.textContent =
      item.subject;

    main.appendChild(
      subject
    );
  }


  const bodyValue =
    item.message_body ||
    item.body ||
    item.message ||
    item.template ||
    "";


  if (bodyValue) {
    const body =
      document.createElement(
        "p"
      );

    body.className =
      "communication-history-message";

    body.textContent =
      bodyValue;

    main.appendChild(
      body
    );
  }


  const footer =
    document.createElement(
      "div"
    );

  footer.className =
    "communication-history-item-footer";


  const time =
    document.createElement(
      "span"
    );

  time.className =
    "communication-history-time";

  time.textContent =
    formatCommunicationDate(
      item.sent_at ||
      item.created_at ||
      item.timestamp
    );

  footer.appendChild(
    time
  );


  if (
    item.provider_message_id
  ) {
    const provider =
      document.createElement(
        "span"
      );

    provider.className =
      "communication-history-provider";

    provider.textContent =
      `ID: ${item.provider_message_id}`;

    footer.appendChild(
      provider
    );
  }


  if (
    item.error_message
  ) {
    const error =
      document.createElement(
        "span"
      );

    error.className =
      "communication-history-error";

    error.textContent =
      item.error_message;

    footer.appendChild(
      error
    );
  }


  main.appendChild(
    footer
  );


  article.appendChild(
    icon
  );

  article.appendChild(
    main
  );


  return article;
}


/* =========================================================
   GLOBAL COMMUNICATION API
   ========================================================= */

window.NexusCommunication = {
  refresh:
    loadCommunicationHistory
};


/* =========================================================
   NEXUS GLOBAL API
   ========================================================= */

window.NexusApp = {
  version: "2.0.0",

  toast:
    window.NexusToast,

  charts:
    window.NexusCharts,

  modal:
    window.NexusModal,

  commandPalette:
    window.NexusCommandPalette,

  refreshCommunication:
    loadCommunicationHistory,

  prefersReducedMotion
};


/* =========================================================
   FINAL SAFETY NET
   ========================================================= */

window.addEventListener(
  "error",
  (event) => {
    /*
     * Do not let an isolated frontend error
     * destroy the rest of the application.
     *
     * We deliberately do not display raw JS errors
     * to users because they are not useful UX.
     */
    console.warn(
      "NEXUS frontend error:",
      event.error || event.message
    );
  }
);


window.addEventListener(
  "unhandledrejection",
  (event) => {
    console.warn(
      "NEXUS async operation failed:",
      event.reason
    );
  }
);