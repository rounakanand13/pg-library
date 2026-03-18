function normalize(text) {
  return (text || "").toLowerCase().trim();
}

function initReveal() {
  const nodes = document.querySelectorAll(".reveal");
  if (!nodes.length) {
    return;
  }

  if (!("IntersectionObserver" in window)) {
    nodes.forEach((node) => node.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.01,
      rootMargin: "0px 0px -8% 0px"
    }
  );

  nodes.forEach((node) => observer.observe(node));
}

function initSearchAndFilters() {
  const searchInput = document.querySelector("[data-search-input]");
  const cards = Array.from(document.querySelectorAll(".chapter-card"));
  const buttons = Array.from(document.querySelectorAll("[data-year-filter]"));
  const counter = document.querySelector("[data-results-count]");

  if (!searchInput || !cards.length || !buttons.length || !counter) {
    return;
  }

  let activeYear = "all";

  const render = () => {
    const query = normalize(searchInput.value);
    let visible = 0;

    cards.forEach((card) => {
      const cardYear = card.dataset.year || "Unknown";
      const haystack = card.dataset.search || "";
      const matchesQuery = !query || haystack.includes(query);
      const matchesYear = activeYear === "all" || cardYear === activeYear;
      const show = matchesQuery && matchesYear;
      card.hidden = !show;
      if (show) {
        visible += 1;
      }
    });

    counter.textContent = `${visible} chapter${visible === 1 ? "" : "s"}`;
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      activeYear = button.dataset.yearFilter || "all";
      buttons.forEach((item) => item.classList.toggle("is-active", item === button));
      render();
    });
  });

  searchInput.addEventListener("input", render);

  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const isTyping =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      (target && target.isContentEditable);

    if (event.key === "/" && !isTyping) {
      event.preventDefault();
      searchInput.focus();
      searchInput.select();
    }

    if (event.key === "Escape" && document.activeElement === searchInput) {
      searchInput.blur();
    }
  });

  render();
}

function updateProgressBar() {
  const progressBar = document.querySelector("[data-reading-progress] span");
  if (!progressBar) {
    return;
  }

  const documentHeight = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = documentHeight <= 0 ? 0 : window.scrollY / documentHeight;
  progressBar.style.width = `${Math.min(100, Math.max(0, ratio * 100))}%`;
}

function initReadingProgress() {
  if (!document.querySelector("[data-reading-progress]")) {
    return;
  }

  updateProgressBar();
  window.addEventListener("scroll", updateProgressBar, { passive: true });
  window.addEventListener("resize", updateProgressBar);
}

function initChapterShortcuts() {
  const root = document.body;
  const prevUrl = root.dataset.prevUrl;
  const nextUrl = root.dataset.nextUrl;

  if (!prevUrl && !nextUrl) {
    return;
  }

  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const isTyping =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      (target && target.isContentEditable);

    if (isTyping) {
      return;
    }

    if (event.key === "[" && prevUrl) {
      window.location.href = prevUrl;
    }

    if (event.key === "]" && nextUrl) {
      window.location.href = nextUrl;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initReveal();
  initSearchAndFilters();
  initReadingProgress();
  initChapterShortcuts();
});
