// FFDL Service Worker Background Script (Zero-Token Local Loopback Bridge)

const NATIVE_HOST = "com.ffdl.native_host";
const DAEMON_PORT = 41194;
const LEGACY_PORT = 45732;

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "ffdl-parent",
    title: "⚡ Download with FFDL Accelerator",
    contexts: ["link", "page"]
  });

  chrome.contextMenus.create({
    id: "ffdl-ff",
    parentId: "ffdl-parent",
    title: "⚡ FuckingFast (1-Click)",
    contexts: ["link", "page"]
  });

  chrome.contextMenus.create({
    id: "ffdl-dn",
    parentId: "ffdl-parent",
    title: "⚡ DataNodes (Direct)",
    contexts: ["link", "page"]
  });

  chrome.contextMenus.create({
    id: "ffdl-fk",
    parentId: "ffdl-parent",
    title: "⚡ FileKeeper",
    contexts: ["link", "page"]
  });

  chrome.contextMenus.create({
    id: "ffdl-magnet",
    parentId: "ffdl-parent",
    title: "🧲 Torrent Magnets",
    contexts: ["link", "page"]
  });
});

// 1. Loopback HTTP Daemon Transport (Zero-Token Local Access)
async function sendViaDaemon(url, hoster, mainOnly) {
  try {
    const res = await fetch(`http://127.0.0.1:${DAEMON_PORT}/api/v1/queue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, hoster, main_only: mainOnly }),
      signal: AbortSignal.timeout(120)
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (e) {
    // Try legacy fallback port
  }

  const res2 = await fetch(`http://127.0.0.1:${LEGACY_PORT}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, hoster, main_only: mainOnly }),
    signal: AbortSignal.timeout(120)
  });
  return await res2.json();
}

// 2. Native Messaging Transport
async function sendViaNativeHost(payload) {
  return new Promise((resolve, reject) => {
    try {
      chrome.runtime.sendNativeMessage(NATIVE_HOST, payload, (response) => {
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError);
        } else {
          resolve(response);
        }
      });
    } catch (err) {
      reject(err);
    }
  });
}

async function checkBridgeHealth() {
  let daemonOnline = false;
  let nativeOnline = false;

  try {
    const res = await fetch(`http://127.0.0.1:${DAEMON_PORT}/health`, { method: "GET" });
    if (res.ok) {
      daemonOnline = true;
    }
  } catch (e) {}

  try {
    const nativeRes = await sendViaNativeHost({ action: "PING" });
    if (nativeRes && (nativeRes.type === "PONG" || nativeRes.status === "ok")) {
      nativeOnline = true;
    }
  } catch (e) {}

  return { native: nativeOnline, daemon: daemonOnline };
}

async function dispatchDownloadJob(url, hoster = "", mainOnly = false, allParts = true) {
  const payload = {
    action: "QUEUE_DOWNLOAD",
    url: url,
    hoster: hoster,
    main_only: mainOnly,
    all: allParts
  };

  // 1. First try HTTP Loopback RPC Daemon (Zero-Token instant local call)
  try {
    const daemonResp = await sendViaDaemon(url, hoster, mainOnly);
    if (daemonResp && !daemonResp.error) {
      return { success: true, transport: "daemon", data: daemonResp };
    }
  } catch (err) {
    console.warn("HTTP bridge daemon offline, checking native messaging...", err);
  }

  // 2. Second try Native Messaging Host
  try {
    const nativeResp = await sendViaNativeHost(payload);
    if (nativeResp && !nativeResp.error) {
      return { success: true, transport: "native", data: nativeResp };
    }
  } catch (err) {
    console.warn("Native messaging unavailable, falling back to protocol...", err);
  }

  // 3. Third fallback: ffdl:// Windows Deep-Link Protocol (opens terminal window via ffdl-run.bat)
  let deepLink = `ffdl://download?url=${encodeURIComponent(url)}&all=${allParts ? 1 : 0}`;
  if (hoster) {
    deepLink += `&hoster=${encodeURIComponent(hoster)}`;
  }
  if (mainOnly) {
    deepLink += `&main_only=1`;
  }
  return { success: true, transport: "protocol", deepLink: deepLink };
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const targetUrl = info.linkUrl || info.pageUrl || (tab ? tab.url : "");
  if (!targetUrl) return;

  let hoster = "";
  if (info.menuItemId === "ffdl-ff") hoster = "fuckingfast";
  else if (info.menuItemId === "ffdl-dn") hoster = "datanodes";
  else if (info.menuItemId === "ffdl-fk") hoster = "filekeeper";
  else if (info.menuItemId === "ffdl-magnet") hoster = "magnet";

  dispatchDownloadJob(targetUrl, hoster, false, false).then((res) => {
    if (res.transport === "protocol" && tab && tab.id) {
      chrome.tabs.update(tab.id, { url: res.deepLink });
    }
  });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "download" || request.action === "QUEUE_DOWNLOAD") {
    const allParts = request.all !== undefined ? request.all : false;
    dispatchDownloadJob(request.url, request.hoster || "", request.main_only || false, allParts).then((result) => {
      sendResponse(result);
    });
    return true;
  } else if (request.action === "check_status" || request.action === "HEALTH") {
    checkBridgeHealth().then((status) => {
      sendResponse(status);
    });
    return true;
  }
});
