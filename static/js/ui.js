/**
 * UI/UX Features for Health Tracker
 * Vanilla JS — no external dependencies
 */
(function () {
  'use strict';

  /* =========================================================
   * 14. CSRF Helper (used by all POST requests)
   * ========================================================= */
  function getCSRFToken() {
    // Try cookie first
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith('csrftoken=')) {
        return decodeURIComponent(trimmed.substring('csrftoken='.length));
      }
    }
    // Fall back to meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    return '';
  }

  // Expose globally so other scripts can use it
  window.getCSRFToken = getCSRFToken;

  /* =========================================================
   * Helper: debounce
   * ========================================================= */
  function debounce(fn, delay) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function showAppToast(message, variant = 'info') {
    const container = document.getElementById('app-toast-container');
    if (!container) return;
    const tone = variant === 'error' ? 'danger' : variant;
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${tone} border-0`;
    toastEl.setAttribute('role', 'status');
    toastEl.setAttribute('aria-live', 'polite');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML =
      '<div class="d-flex">' +
      `<div class="toast-body">${message}</div>` +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
      '</div>';
    container.appendChild(toastEl);
    if (window.bootstrap && window.bootstrap.Toast) {
      const toast = new window.bootstrap.Toast(toastEl, { delay: 3000 });
      toast.show();
      toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove(), { once: true });
    } else {
      setTimeout(() => toastEl.remove(), 3000);
    }
  }

  window.showAppToast = showAppToast;

  /* =========================================================
   * Main initialisation on DOMContentLoaded
   * ========================================================= */
  document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    initAlertAutoDismiss();
    initDragAndDropDashboard();
    initQuickEntryVitals();
    initVoiceToText();
    initCollapsibleSidebar();
    initMedicalTooltips();
    initGlobalSearch();
    initCustomColorPalettes();
    initRealTimeValidation();
    initInfiniteScrolling();
    initOnboardingTour();
    initPWARegistration();
  });

  /* =========================================================
   * 1. Dark Mode Toggle
   * ========================================================= */
  function initDarkMode() {
    const toggle = document.getElementById('dark-mode-toggle');
    const root = document.documentElement;

    const applyTheme = (theme) => {
      if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
      } else {
        root.removeAttribute('data-theme');
      }
      updateDarkModeIcon(theme);
    };

    const updateDarkModeIcon = (theme) => {
      if (!toggle) return;
      const icon = toggle.querySelector('i');
      if (!icon) return;
      if (theme === 'dark') {
        icon.setAttribute('data-lucide', 'sun');
      } else {
        icon.setAttribute('data-lucide', 'moon');
      }
      if (typeof lucide !== 'undefined') lucide.createIcons();
    };

    // Apply saved preference or respect OS setting
    const saved = localStorage.getItem('theme');
    if (saved) {
      applyTheme(saved);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      applyTheme('dark');
    } else {
      updateDarkModeIcon('light');
    }

    if (toggle) {
      toggle.addEventListener('click', () => {
        const current = root.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        localStorage.setItem('theme', next);
      });
    }

    // Listen for OS preference changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  }

  /* =========================================================
   * 1b. Auto-dismiss Alerts
   * ========================================================= */
  function initAlertAutoDismiss() {
    // Auto-dismiss success, info, and warning alerts after 6 seconds
    // Error/danger alerts remain until manually dismissed
    const alerts = document.querySelectorAll(
      '.alert-success, .alert-info, .alert-warning'
    );
    alerts.forEach((alert) => {
      if (!alert.classList.contains('alert-dismissible')) return;
      setTimeout(() => {
        // Use Bootstrap's dismiss method if available, otherwise fade out
        const bsAlert = window.bootstrap && window.bootstrap.Alert
          ? window.bootstrap.Alert.getOrCreateInstance(alert)
          : null;
        if (bsAlert) {
          bsAlert.close();
        } else {
          alert.classList.remove('show');
          alert.addEventListener('transitionend', () => alert.remove(), { once: true });
        }
      }, 6000);
    });
  }

  /* =========================================================
   * 2. Drag-and-Drop Dashboard
   * ========================================================= */
  function initDragAndDropDashboard() {
    const widgets = document.querySelectorAll('.dashboard-widget');
    if (!widgets.length) return;

    let draggedEl = null;

    widgets.forEach((widget) => {
      widget.setAttribute('draggable', 'true');

      widget.addEventListener('dragstart', (e) => {
        draggedEl = widget;
        widget.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', '');
      });

      widget.addEventListener('dragend', () => {
        widget.classList.remove('dragging');
        draggedEl = null;
      });

      widget.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const container = widget.parentNode;
        if (draggedEl && draggedEl !== widget) {
          const allWidgets = [...container.querySelectorAll('.dashboard-widget:not(.dragging)')];
          const targetIdx = allWidgets.indexOf(widget);
          const draggedIdx = [...container.children].indexOf(draggedEl);
          const targetDomIdx = [...container.children].indexOf(widget);
          if (draggedIdx < targetDomIdx) {
            container.insertBefore(draggedEl, widget.nextSibling);
          } else {
            container.insertBefore(draggedEl, widget);
          }
        }
      });

      widget.addEventListener('drop', (e) => {
        e.preventDefault();
        persistWidgetOrder();
      });
    });

    async function persistWidgetOrder() {
      const container = document.querySelector('.dashboard-widget')?.parentNode;
      if (!container) return;
      const order = [...container.querySelectorAll('.dashboard-widget')].map(
        (w, i) => ({ id: w.dataset.widgetId || w.id, position: i })
      );
      try {
        await fetch('/dashboard/update_widgets/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
          },
          body: JSON.stringify({ order }),
        });
      } catch (err) {
        console.error('Failed to save widget order:', err);
      }
    }
  }

  /* =========================================================
   * 3. Quick-Entry Vitals
   * ========================================================= */
  function initQuickEntryVitals() {
    const btn = document.getElementById('quick-entry-btn');
    const modal = document.getElementById('quickEntryModal');
    if (!btn || !modal) return;

    const form = modal.querySelector('form');
    const closeBtn = modal.querySelector('.btn-close, [data-bs-dismiss="modal"]');
    const msgContainer = modal.querySelector('.quick-entry-message') || createMsgContainer(modal);
    const modalInstance = window.bootstrap && window.bootstrap.Modal
      ? window.bootstrap.Modal.getOrCreateInstance(modal)
      : null;

    if (closeBtn) {
      closeBtn.addEventListener('click', () => closeModal());
    }

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    function closeModal() {
      if (modalInstance) {
        modalInstance.hide();
      }
    }

    function createMsgContainer(parent) {
      const div = document.createElement('div');
      div.className = 'quick-entry-message';
      parent.querySelector('.modal-body')?.prepend(div) || parent.prepend(div);
      return div;
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        msgContainer.textContent = '';
        msgContainer.className = 'quick-entry-message';
        const formData = new FormData(form);
        try {
          const res = await fetch('/vitals/add/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCSRFToken() },
            body: formData,
          });
          if (res.ok) {
            msgContainer.textContent = 'Vitals saved successfully!';
            msgContainer.classList.add('text-success');
            showAppToast('Vitals saved successfully.', 'success');
            form.reset();
            setTimeout(closeModal, 1500);
          } else {
            const data = await res.json().catch(() => ({}));
            msgContainer.textContent = data.error || 'Failed to save vitals.';
            msgContainer.classList.add('text-danger');
            showAppToast(msgContainer.textContent, 'error');
          }
        } catch (err) {
          msgContainer.textContent = 'Network error. Please try again.';
          msgContainer.classList.add('text-danger');
          showAppToast('Network error while saving vitals.', 'error');
        }
      });
    }
  }

  /* =========================================================
   * 4. Voice-to-Text
   * ========================================================= */
  function initVoiceToText() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voiceButtons = Array.from(document.querySelectorAll('.voice-input-btn'));
    const topBarVoiceBtn = document.getElementById('voice-input-btn');
    if (topBarVoiceBtn) voiceButtons.push(topBarVoiceBtn);

    voiceButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        if (!SpeechRecognition) {
          showAppToast('Voice input is not supported in this browser.', 'warning');
          return;
        }

        const input = btn.id === 'voice-input-btn'
          ? document.getElementById('global-search-input')
          : btn.closest('.input-group')?.querySelector('input')
          || btn.parentElement?.querySelector('input')
          || btn.previousElementSibling;

        if (!input) return;

        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        btn.classList.add('listening');

        recognition.addEventListener('result', (e) => {
          const transcript = e.results[0][0].transcript;
          input.value = transcript;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        });

        recognition.addEventListener('end', () => {
          btn.classList.remove('listening');
        });

        recognition.addEventListener('error', (e) => {
          btn.classList.remove('listening');
          if (e.error !== 'aborted') {
            showAppToast('Voice recognition error: ' + e.error, 'error');
          }
        });

        recognition.start();
      });
    });
  }

  /* =========================================================
   * 5. Collapsible Sidebar
   * ========================================================= */
  function initCollapsibleSidebar() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (!toggleBtn) return;

    const body = document.body;

    // Restore saved state
    const savedState = localStorage.getItem('sidebarOpen');
    if (savedState === 'true') {
      body.classList.add('sidebar-open');
    } else if (savedState === 'false') {
      body.classList.remove('sidebar-open');
    }

    let overlay = document.querySelector('.sidebar-overlay');

    toggleBtn.addEventListener('click', () => {
      const isOpen = body.classList.toggle('sidebar-open');
      localStorage.setItem('sidebarOpen', String(isOpen));

      // On mobile, manage overlay
      if (window.innerWidth < 768) {
        if (isOpen) {
          if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'sidebar-overlay';
            body.appendChild(overlay);
            overlay.addEventListener('click', () => {
              body.classList.remove('sidebar-open');
              localStorage.setItem('sidebarOpen', 'false');
              overlay.remove();
              overlay = null;
            });
          }
        } else if (overlay) {
          overlay.remove();
          overlay = null;
        }
      }
    });

    // Collapsible sidebar category groups
    document.querySelectorAll('.sidebar-collapse-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var parent = btn.closest('.sidebar-category--collapsible');
        if (!parent) return;
        var bodyEl = parent.querySelector('.sidebar-collapse-body');
        var isExpanded = parent.classList.toggle('sidebar-category--expanded');
        btn.setAttribute('aria-expanded', String(isExpanded));
        if (bodyEl) {
          bodyEl.classList.toggle('sidebar-collapse-body--open', isExpanded);
        }
      });
    });
  }

  /* =========================================================
   * 6. Skeleton Loading
   * ========================================================= */
  function resolveContainer(container) {
    return typeof container === 'string' ? document.querySelector(container) : container;
  }

  function showSkeletons(container, count = 3) {
    container = resolveContainer(container);
    if (!container) return;

    for (let i = 0; i < count; i++) {
      const skeleton = document.createElement('div');
      skeleton.className = 'skeleton-loader';
      skeleton.innerHTML =
        '<div class="skeleton-line skeleton-line--title"></div>' +
        '<div class="skeleton-line skeleton-line--text"></div>' +
        '<div class="skeleton-line skeleton-line--text skeleton-line--short"></div>';
      container.appendChild(skeleton);
    }
  }

  function hideSkeletons(container) {
    container = resolveContainer(container);
    if (!container) return;
    container.querySelectorAll('.skeleton-loader').forEach((el) => el.remove());
  }

  window.showSkeletons = showSkeletons;
  window.hideSkeletons = hideSkeletons;

  /* =========================================================
   * 7. Medical Tooltips
   * ========================================================= */
  function initMedicalTooltips() {
    let activeTooltip = null;

    const removeTooltip = () => {
      if (activeTooltip) {
        activeTooltip.remove();
        activeTooltip = null;
      }
    };

    const showTooltip = (el) => {
      removeTooltip();
      const text = el.getAttribute('data-medical-tooltip');
      if (!text) return;

      const title = el.getAttribute('data-tooltip-title') || '';
      const tip = document.createElement('div');
      tip.className = 'medical-tooltip';
      tip.innerHTML =
        (title ? `<strong class="medical-tooltip__title">${title}</strong>` : '') +
        `<span class="medical-tooltip__body">${text}</span>`;
      document.body.appendChild(tip);

      const rect = el.getBoundingClientRect();
      const tipRect = tip.getBoundingClientRect();
      let top = rect.top + window.scrollY - tipRect.height - 8;
      let left = rect.left + window.scrollX + (rect.width - tipRect.width) / 2;

      // Keep within viewport
      if (top < window.scrollY) top = rect.bottom + window.scrollY + 8;
      if (left < 0) left = 4;
      if (left + tipRect.width > window.innerWidth) left = window.innerWidth - tipRect.width - 4;

      tip.style.top = top + 'px';
      tip.style.left = left + 'px';
      activeTooltip = tip;
    };

    document.querySelectorAll('[data-medical-tooltip]').forEach((el) => {
      el.setAttribute('tabindex', el.getAttribute('tabindex') || '0');
      el.addEventListener('mouseenter', () => showTooltip(el));
      el.addEventListener('focus', () => showTooltip(el));
      el.addEventListener('mouseleave', removeTooltip);
      el.addEventListener('blur', removeTooltip);
    });
  }

  /* =========================================================
   * 8. Global Search
   * ========================================================= */
  function initGlobalSearch() {
    const input = document.getElementById('global-search-input');
    const dropdown = document.getElementById('global-search-results');
    if (!input || !dropdown) return;

    const TYPE_ICONS = {
      test: '🧪',
      vitals: '❤️',
      appointment: '📅',
      medication: '💊',
      default: '🔍',
    };

    const doSearch = debounce(async (query) => {
      if (!query || query.length < 2) {
        dropdown.innerHTML = '';
        dropdown.style.display = 'none';
        return;
      }

      try {
        const res = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error('Search request failed');
        const data = await res.json();

        if (!data.results || !data.results.length) {
          dropdown.innerHTML = '<div class="search-no-results">No results found</div>';
          dropdown.style.display = 'block';
          return;
        }

        dropdown.innerHTML = data.results
          .map(
            (r) =>
              `<a class="search-result-item" href="${r.url || '#'}">` +
              `<span class="search-result-icon">${TYPE_ICONS[r.type] || TYPE_ICONS.default}</span>` +
              `<span class="search-result-name">${r.name || ''}</span>` +
              (r.date ? `<span class="search-result-date">${r.date}</span>` : '') +
              (r.value ? `<span class="search-result-value">${r.value}</span>` : '') +
              `</a>`
          )
          .join('');
        dropdown.style.display = 'block';
      } catch (err) {
        console.error('Search error:', err);
        dropdown.innerHTML = '<div class="search-no-results">Search unavailable</div>';
        dropdown.style.display = 'block';
      }
    }, 300);

    input.addEventListener('input', (e) => doSearch(e.target.value.trim()));

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        dropdown.innerHTML = '';
        dropdown.style.display = 'none';
        input.blur();
      }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.style.display = 'none';
      }
    });
  }

  /* =========================================================
   * 9. Custom Color Palettes
   * ========================================================= */
  function initCustomColorPalettes() {
    applyPaletteFromStorage();
  }

  function applyPaletteFromStorage() {
    try {
      const raw = localStorage.getItem('colorPalette');
      if (!raw) return;
      const palette = JSON.parse(raw);
      applyPalette(palette);
    } catch (e) {
      console.error('Invalid color palette in localStorage:', e);
    }
  }

  function applyPalette(palette) {
    const root = document.documentElement;
    for (const [category, color] of Object.entries(palette)) {
      root.style.setProperty(`--color-${category}`, color);
    }
  }

  function updateCategoryColor(category, color) {
    let palette = {};
    try {
      palette = JSON.parse(localStorage.getItem('colorPalette')) || {};
    } catch (_) {
      /* empty */
    }
    palette[category] = color;
    localStorage.setItem('colorPalette', JSON.stringify(palette));
    document.documentElement.style.setProperty(`--color-${category}`, color);
  }

  window.updateCategoryColor = updateCategoryColor;

  /* =========================================================
   * 10. Real-time Validation
   * ========================================================= */
  function initRealTimeValidation() {
    document.querySelectorAll('.validated-form').forEach((form) => {
      const inputs = form.querySelectorAll('input, select, textarea');

      inputs.forEach((input) => {
        input.addEventListener('input', () => validateField(input));
        input.addEventListener('blur', () => validateField(input));
      });

      form.addEventListener('submit', (e) => {
        let valid = true;
        inputs.forEach((input) => {
          if (!validateField(input)) valid = false;
        });
        if (!valid) e.preventDefault();
      });
    });
  }

  function validateField(input) {
    const feedback = input.parentElement?.querySelector('.invalid-feedback');
    let message = '';

    // Required check
    if (input.hasAttribute('required') && !input.value.trim()) {
      message = 'This field is required.';
    }

    // Number range check
    if (!message && (input.type === 'number' || input.inputMode === 'numeric')) {
      if (input.value && isNaN(Number(input.value))) {
        message = 'Please enter a valid number.';
      } else if (input.value) {
        const val = Number(input.value);
        const min = input.hasAttribute('min') ? Number(input.min) : null;
        const max = input.hasAttribute('max') ? Number(input.max) : null;
        if (min !== null && val < min) {
          message = `Value must be at least ${min}.`;
        } else if (max !== null && val > max) {
          message = `Value must be at most ${max}.`;
        }
      }
    }

    // Date check
    if (!message && input.type === 'date' && input.value) {
      const d = new Date(input.value);
      if (isNaN(d.getTime())) {
        message = 'Please enter a valid date.';
      }
    }

    // Apply classes
    if (message) {
      input.classList.remove('is-valid');
      input.classList.add('is-invalid');
      if (feedback) feedback.textContent = message;
      return false;
    }

    if (input.value.trim()) {
      input.classList.remove('is-invalid');
      input.classList.add('is-valid');
    } else {
      input.classList.remove('is-invalid', 'is-valid');
    }
    if (feedback) feedback.textContent = '';
    return true;
  }

  /* =========================================================
   * 11. Infinite Scrolling
   * ========================================================= */
  function initInfiniteScrolling() {
    const sentinel = document.querySelector('.infinite-scroll-sentinel');
    const container = document.querySelector('.infinite-scroll-container');
    if (!sentinel || !container) return;

    let loading = false;

    const observer = new IntersectionObserver(
      async (entries) => {
        const entry = entries[0];
        if (!entry.isIntersecting || loading) return;

        const nextUrl = sentinel.getAttribute('data-next-url');
        if (!nextUrl) {
          observer.disconnect();
          return;
        }

        loading = true;
        const spinner = document.createElement('div');
        spinner.className = 'infinite-scroll-loader';
        spinner.innerHTML = '<div class="spinner" aria-hidden="true"></div><span>Loading…</span>';
        container.appendChild(spinner);

        try {
          const res = await fetch(nextUrl);
          if (!res.ok) throw new Error('Fetch failed');
          const data = await res.json();

          spinner.remove();

          if (data.html) {
            container.insertAdjacentHTML('beforeend', data.html);
          } else if (data.results && Array.isArray(data.results)) {
            data.results.forEach((item) => {
              const div = document.createElement('div');
              div.className = 'infinite-scroll-item';
              div.innerHTML = item.html || JSON.stringify(item);
              container.appendChild(div);
            });
          }

          if (data.next_url) {
            sentinel.setAttribute('data-next-url', data.next_url);
          } else {
            sentinel.removeAttribute('data-next-url');
            observer.disconnect();
          }
        } catch (err) {
          console.error('Infinite scroll error:', err);
          spinner.remove();
        } finally {
          loading = false;
        }
      },
      { rootMargin: '200px' }
    );

    observer.observe(sentinel);
  }

  /* =========================================================
   * 12. Onboarding Tour
   * ========================================================= */
  const TOUR_STEPS = [
    {
      element: 'body',
      title: 'Welcome to Health Tracker',
      content: 'Let us show you around! This quick tour will help you get started with the key features.',
      position: 'bottom',
    },
    {
      element: '#sidebar, .sidebar, nav[role="navigation"]',
      title: 'Navigation Sidebar',
      content: 'Use the sidebar to navigate between different sections of the app.',
      position: 'right',
    },
    {
      element: '.dashboard, #dashboard, [data-section="dashboard"]',
      title: 'Dashboard Overview',
      content: 'Your dashboard shows a summary of all your health data at a glance.',
      position: 'bottom',
    },
    {
      element: '#add-test-btn, .add-test, a[href*="add"]',
      title: 'Adding New Tests',
      content: 'Click here to add new blood test results or other health data.',
      position: 'bottom',
    },
    {
      element: '.chart-container, #charts, canvas',
      title: 'Viewing Charts',
      content: 'Visualise your health trends over time with interactive charts.',
      position: 'top',
    },
    {
      element: '#quick-entry-btn',
      title: 'Quick Entry',
      content: 'Use Quick Entry for fast vitals logging without leaving the current page.',
      position: 'bottom',
    },
    {
      element: '#dark-mode-toggle',
      title: 'Dark Mode',
      content: 'Toggle dark mode for comfortable viewing in low-light conditions.',
      position: 'left',
    },
  ];

  function startTour() {
    let currentStep = 0;

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'tour-overlay';
    document.body.appendChild(overlay);

    // Create tooltip container
    const tooltip = document.createElement('div');
    tooltip.className = 'tour-tooltip';
    document.body.appendChild(tooltip);

    const showStep = (index) => {
      if (index >= TOUR_STEPS.length) {
        endTour();
        return;
      }

      const step = TOUR_STEPS[index];
      const target = resolveSelector(step.element);

      // Remove previous highlight
      document.querySelectorAll('.tour-highlight').forEach((el) =>
        el.classList.remove('tour-highlight')
      );

      if (target) {
        target.classList.add('tour-highlight');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      const isLast = index === TOUR_STEPS.length - 1;
      tooltip.innerHTML =
        `<div class="tour-tooltip__header">${step.title}</div>` +
        `<div class="tour-tooltip__body">${step.content}</div>` +
        `<div class="tour-tooltip__footer">` +
        `<span class="tour-step-count">${index + 1} / ${TOUR_STEPS.length}</span>` +
        `<button class="tour-btn tour-btn--skip" type="button">Skip</button>` +
        `<button class="tour-btn tour-btn--next" type="button">${isLast ? 'Done' : 'Next'}</button>` +
        `</div>`;

      positionTooltip(tooltip, target, step.position);

      tooltip.querySelector('.tour-btn--next').addEventListener('click', () => {
        currentStep++;
        showStep(currentStep);
      });

      tooltip.querySelector('.tour-btn--skip').addEventListener('click', endTour);
    };

    const endTour = () => {
      overlay.remove();
      tooltip.remove();
      document.querySelectorAll('.tour-highlight').forEach((el) =>
        el.classList.remove('tour-highlight')
      );
      localStorage.setItem('tourCompleted', 'true');
    };

    showStep(currentStep);
  }

  function resolveSelector(selectorStr) {
    // Support comma-separated selectors (first match wins)
    const selectors = selectorStr.split(',').map((s) => s.trim());
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el) return el;
      } catch (_) {
        /* invalid selector, skip */
      }
    }
    return null;
  }

  function positionTooltip(tooltip, target, position) {
    if (!target) {
      // Centre on screen
      tooltip.style.position = 'fixed';
      tooltip.style.top = '50%';
      tooltip.style.left = '50%';
      tooltip.style.transform = 'translate(-50%, -50%)';
      return;
    }

    tooltip.style.position = 'absolute';
    tooltip.style.transform = '';
    const rect = target.getBoundingClientRect();
    const tipRect = tooltip.getBoundingClientRect();
    const scrollY = window.scrollY;
    const scrollX = window.scrollX;

    let top, left;
    switch (position) {
      case 'top':
        top = rect.top + scrollY - tipRect.height - 12;
        left = rect.left + scrollX + (rect.width - tipRect.width) / 2;
        break;
      case 'bottom':
        top = rect.bottom + scrollY + 12;
        left = rect.left + scrollX + (rect.width - tipRect.width) / 2;
        break;
      case 'left':
        top = rect.top + scrollY + (rect.height - tipRect.height) / 2;
        left = rect.left + scrollX - tipRect.width - 12;
        break;
      case 'right':
        top = rect.top + scrollY + (rect.height - tipRect.height) / 2;
        left = rect.right + scrollX + 12;
        break;
      default:
        top = rect.bottom + scrollY + 12;
        left = rect.left + scrollX;
    }

    // Clamp within viewport
    if (left < 4) left = 4;
    if (left + tipRect.width > window.innerWidth + scrollX) {
      left = window.innerWidth + scrollX - tipRect.width - 4;
    }
    if (top < scrollY) top = rect.bottom + scrollY + 12;

    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
  }

  window.startTour = startTour;

  function initOnboardingTour() {
    const startTourBtn = document.getElementById('start-tour-btn');
    if (startTourBtn) {
      startTourBtn.addEventListener('click', () => {
        localStorage.removeItem('tourCompleted');
        startTour();
      });
    }

    if (localStorage.getItem('tourCompleted') !== 'true') {
      // Wait for full page load before starting tour
      if (document.readyState === 'complete') {
        startTour();
      } else {
        window.addEventListener('load', () => startTour());
      }
    }
  }

  /* =========================================================
   * 13b. Chart Dark Mode Helper
   * ========================================================= */
  /**
   * Returns chart color settings that adapt to the current dark/light theme.
   * Chart templates can call window.getChartThemeColors() to get theme-aware colors.
   */
  window.getChartThemeColors = function () {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
      gridColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
      tickColor: isDark ? '#94a3b8' : '#6b7280',
      fontColor: isDark ? '#94a3b8' : '#6b7280',
      tooltipBg: isDark ? 'rgba(15,23,42,0.95)' : 'rgba(17,24,39,0.92)',
      tooltipTitleColor: isDark ? '#cbd5e1' : '#9ca3af',
      tooltipBodyColor: isDark ? '#f1f5f9' : '#f9fafb',
    };
  };

  /* =========================================================
   * 13. PWA Registration
   * ========================================================= */
  function initPWARegistration() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/sw.js').catch((err) => {
        console.warn('Service worker registration failed:', err);
      });
    }
  }
})();
