// FFDL — FitGirl Download Accelerator Content Script (Per-Hoster Inline Buttons & Post Badges)

function showToast(message, isSuccess = true) {
  const existing = document.getElementById("ffdl-toast-notification");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "ffdl-toast-notification";
  toast.className = "ffdl-toast";
  const icon = isSuccess ? "⚡" : "❌";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function triggerFFDLDownload(postUrl, hoster = "", allParts = false, buttonElem = null) {
  const cleanUrl = encodeURIComponent(postUrl);
  let deepLink = `ffdl://download?url=${cleanUrl}`;
  if (hoster) {
    deepLink += `&hoster=${encodeURIComponent(hoster)}`;
  }
  if (allParts) {
    deepLink += `&all=1`;
  }

  const label = hoster ? hoster.toUpperCase() : "ALL MIRRORS";

  if (buttonElem) {
    const originalText = buttonElem.innerHTML;
    buttonElem.innerHTML = `<span>⚡</span> Opening CLI...`;
    buttonElem.style.opacity = "0.85";
    buttonElem.disabled = true;

    setTimeout(() => {
      buttonElem.innerHTML = originalText;
      buttonElem.disabled = false;
      buttonElem.style.opacity = "1";
    }, 2500);
  }

  showToast(`⚡ Launching FFDL Accelerator [${label}]...`);
  window.location.href = deepLink;

  if (chrome.runtime && chrome.runtime.sendMessage) {
    try {
      chrome.runtime.sendMessage({ action: "download_triggered", url: postUrl, hoster: hoster });
    } catch (e) {}
  }
}

// 1. Injects dedicated buttons right next to each hoster in Download Mirrors list
function injectPerHosterButtons() {
  const postUrl = window.location.href.split("#")[0].split("?")[0];
  const listItems = document.querySelectorAll(".entry-content li, article.post li, .post-content li, li");

  listItems.forEach((li) => {
    if (li.querySelector(".ffdl-inline-btn") || li.getAttribute("data-ffdl-injected") === "true") {
      return;
    }

    const text = li.innerText || "";
    const html = li.innerHTML || "";

    let hosterKey = null;
    let label = "";
    let btnClass = "";
    let icon = "⚡";

    if (/datanodes/i.test(text) || /datanodes/i.test(html)) {
      hosterKey = "datanodes";
      label = "Download DataNodes";
      btnClass = "ffdl-btn-dn";
    } else if (/fuckingfast/i.test(text) || /fuckingfast/i.test(html)) {
      hosterKey = "fuckingfast";
      label = "Download FuckingFast";
      btnClass = "ffdl-btn-ff";
    } else if (/filekeeper/i.test(text) || /filekeeper/i.test(html)) {
      hosterKey = "filekeeper";
      label = "Download FileKeeper";
      btnClass = "ffdl-btn-fk";
    } else if (/magnet/i.test(html) && (/1337x/i.test(text) || /magnet:\?/i.test(html) || /\[magnet\]/i.test(html))) {
      hosterKey = "magnet";
      label = "Download Magnet";
      btnClass = "ffdl-btn-magnet";
      icon = "🧲";
    }

    if (hosterKey) {
      li.setAttribute("data-ffdl-injected", "true");

      const btn = document.createElement("button");
      btn.className = `ffdl-inline-btn ${btnClass}`;
      btn.innerHTML = `<span>${icon}</span> <span>${label}</span>`;
      btn.title = `Launch FFDL Accelerator for ${label}`;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        triggerFFDLDownload(postUrl, hosterKey, false, btn);
      });

      if (hosterKey === "magnet") {
        const magnetLink = Array.from(li.querySelectorAll("a")).find(a => 
          /magnet:\?/i.test(a.href) || /magnet/i.test(a.innerText)
        );
        if (magnetLink && magnetLink.nextSibling) {
          magnetLink.parentNode.insertBefore(btn, magnetLink.nextSibling);
          return;
        } else if (magnetLink) {
          magnetLink.parentNode.appendChild(btn);
          return;
        }
      }

      // Find the anchor or text inside the li to append next to
      const targetAnchor = Array.from(li.querySelectorAll("a, strong, b")).find(el => {
        const t = el.innerText || el.textContent || "";
        return /filehoster|datanodes|fuckingfast|filekeeper|magnet/i.test(t);
      }) || li.firstChild;

      if (targetAnchor && targetAnchor.nextSibling) {
        targetAnchor.parentNode.insertBefore(btn, targetAnchor.nextSibling);
      } else if (targetAnchor) {
        targetAnchor.parentNode.appendChild(btn);
      } else {
        li.appendChild(btn);
      }
    }
  });
}

// 2. Injects "Download with FFDL" button right at the header of single game post pages
function injectSinglePostButton() {
  const singleTitle = document.querySelector("h1.entry-title");
  if (!singleTitle) return;

  const article = singleTitle.closest("article") || document.querySelector(".entry-content")?.parentNode;
  if (!article) return;

  if (article.querySelector(".ffdl-single-post-btn") || document.getElementById("ffdl-single-top-btn")) {
    return;
  }

  const postUrl = window.location.href.split("#")[0].split("?")[0];

  const btn = document.createElement("button");
  btn.id = "ffdl-single-top-btn";
  btn.className = "ffdl-card-btn ffdl-single-post-btn";
  btn.innerHTML = "<span>⚡</span> Download with FFDL";
  btn.title = "Launch FFDL Accelerator for this repack (Auto-selects all parts & best mirror)";
  btn.style.cssText = "margin-top: 8px; margin-bottom: 12px; display: inline-flex; cursor: pointer; border: none;";

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    triggerFFDLDownload(postUrl, "", false, btn);
  });

  const header = article.querySelector(".entry-header") || singleTitle.parentNode;
  if (header) {
    const meta = header.querySelector(".entry-meta");
    if (meta) {
      header.insertBefore(btn, meta);
    } else {
      header.appendChild(btn);
    }
  } else {
    singleTitle.parentNode.insertBefore(btn, singleTitle.nextSibling);
  }
}

// 3. Injects "Download with FFDL" badge on EVERY post card across feeds, homepage, search, and category archives
function injectPostFeedButtons() {
  const posts = document.querySelectorAll("article, [id^='post-'], .post");
  if (!posts || posts.length === 0) return;

  posts.forEach((post) => {
    if (post.querySelector(".ffdl-feed-btn") || post.querySelector(".ffdl-single-post-btn")) {
      return;
    }

    // Identify post title anchor
    const titleAnchor = post.querySelector(".entry-title a, h1 a, h2 a, .entry-header a");
    if (!titleAnchor || !titleAnchor.href) {
      return;
    }

    const postUrl = titleAnchor.href;
    if (!/fitgirl-repacks\.site/i.test(postUrl)) {
      return;
    }

    const btn = document.createElement("button");
    btn.className = "ffdl-card-btn ffdl-feed-btn";
    btn.innerHTML = "<span>⚡</span> Download with FFDL";
    btn.title = "Launch FFDL Accelerator for this repack (Auto-selects all parts & best mirror)";
    btn.style.cssText = "display: inline-flex; cursor: pointer; border: none; margin: 8px 0;";

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      triggerFFDLDownload(postUrl, "", false, btn);
    });

    const targetHeader = post.querySelector(".entry-header") || titleAnchor.closest("header") || titleAnchor.parentNode;
    if (targetHeader) {
      const meta = targetHeader.querySelector(".entry-meta");
      if (meta) {
        targetHeader.insertBefore(btn, meta);
      } else {
        targetHeader.appendChild(btn);
      }
    } else {
      titleAnchor.parentNode.appendChild(btn);
    }
  });
}

function runAllInjections() {
  // Ensure the old bulky top banner remains permanently removed
  const existingBar = document.getElementById("ffdl-action-bar");
  if (existingBar) existingBar.remove();

  injectSinglePostButton();
  injectPostFeedButtons();
  injectPerHosterButtons();
}

// Run immediately on script execution
runAllInjections();

// Observe DOM mutations to dynamically attach buttons on ajax pagination, search filters, and content hydration
const observer = new MutationObserver(() => {
  runAllInjections();
});

observer.observe(document.body, { childList: true, subtree: true });
