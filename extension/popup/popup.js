document.addEventListener("DOMContentLoaded", () => {
  const daemonStatus = document.getElementById("daemon-status");
  const nativeStatus = document.getElementById("native-status");
  const quickUrlInput = document.getElementById("quick-url");
  const quickDownloadBtn = document.getElementById("quick-download-btn");
  const statusMsg = document.getElementById("status-message");

  // Check bridge health
  chrome.runtime.sendMessage({ action: "HEALTH" }, (res) => {
    if (res) {
      if (res.daemon) {
        daemonStatus.className = "badge online";
        daemonStatus.innerText = "ONLINE";
      } else {
        daemonStatus.className = "badge offline";
        daemonStatus.innerText = "OFFLINE";
      }

      if (res.native) {
        nativeStatus.className = "badge online";
        nativeStatus.innerText = "ONLINE";
      } else {
        nativeStatus.className = "badge offline";
        nativeStatus.innerText = "OFFLINE";
      }
    }
  });

  // Quick download
  quickDownloadBtn.addEventListener("click", () => {
    const url = quickUrlInput.value.trim();
    if (!url) {
      statusMsg.innerText = "❌ Please enter a valid URL";
      return;
    }

    statusMsg.innerText = "⏳ Dispatching to CLI...";
    chrome.runtime.sendMessage(
      { action: "QUEUE_DOWNLOAD", url: url, hoster: "fuckingfast", main_only: true },
      (res) => {
        if (res && res.success) {
          statusMsg.innerText = `✔ Queued via ${res.transport.toUpperCase()}`;
        } else {
          statusMsg.innerText = "❌ Failed to queue";
        }
      }
    );
  });
});
