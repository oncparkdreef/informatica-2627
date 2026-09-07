document.addEventListener("DOMContentLoaded", () => {
  const pageTocHeadings = document.querySelectorAll(
    ".md-content .page-toc[id]"
  );

  if (pageTocHeadings.length === 0) {
    return;
  }

  const allowedIds = new Set(
    Array.from(pageTocHeadings).map(
      heading => `#${heading.id}`
    )
  );

  const tocLinks = document.querySelectorAll(
    ".md-sidebar--secondary .md-nav__link[href^='#']"
  );

  tocLinks.forEach(link => {
    const item = link.closest(".md-nav__item");

    if (!item) {
      return;
    }

    if (!allowedIds.has(link.getAttribute("href"))) {
      item.style.display = "none";
    }
  });

  document.querySelectorAll(".page-toc-managed").forEach(toc => {
    toc.classList.add("page-toc-ready");
  });
});