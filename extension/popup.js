// FFDL Extension Popup Script

document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("daemon-status");
  const pageCard = document.getElementById("page-card");
  const gameTitleEl = document.getElementById("page-game-title");
  const btnQuickDl = document.getElementById("btn-quick-download");
  const manualUrlInput = document.getElementById("manual-url");
  const hosterSelect = document.getElementById("hoster-select");
  const chkMainOnly = document.getElementById("chk-main-only");
  const btnSendManual = document.getElementById("btn-send-manual");

  let currentPageUrl = "";

  // 1. Check local background daemon
  chrome.runtime.sendMessage({ action: "check_status" }, (res) => {
    if (res && res.online) {
      statusBadge.textContent = "Daemon Online";
      statusBadge.className = "status-badge online";
    } else {
      statusBadge.textContent = "Protocol Mode";
      statusBadge.className = "status-badge";
    }
  });

  // 2. Query active tab to see if on FitGirl post
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0] && tabs[0].url) {
      const activeUrl = tabs[0].url;
      if (activeUrl.includes("fitgirl-repacks.site") && !activeUrl.endsWith(".site/")) {
        currentPageUrl = activeUrl;
        pageCard.style.display = "block";
        gameTitleEl.textContent = tabs[0].title.replace(" – FitGirl Repacks", "").trim();
      }
    }
  });

  function triggerDownload(url, hoster, mainOnly) {
    const deepLink = `ffdl://download?url=${encodeURIComponent(url)}&hoster=${encodeURIComponent(hoster)}&main_only=${mainOnly ? 1 : 0}`;
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        chrome.tabs.update(tabs[0].id, { url: deepLink });
      } else {
        window.open(deepLink, "_blank");
      }
    });
  }

  btnQuickDl.addEventListener("click", () => {
    if (currentPageUrl) {
      const hoster = hosterSelect.value;
      const mainOnly = chkMainOnly.checked;
      triggerDownload(currentPageUrl, hoster, mainOnly);
    }
  });

  btnSendManual.addEventListener("click", () => {
    const url = manualUrlInput.value.trim();
    if (!url) {
      manualUrlInput.focus();
      return;
    }
    const hoster = hosterSelect.value;
    const mainOnly = chkMainOnly.checked;
    triggerDownload(url, hoster, mainOnly);
  });
});
