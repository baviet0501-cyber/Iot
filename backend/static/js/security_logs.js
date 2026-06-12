const securityLogBody = document.body;
let latestLogId = Number(securityLogBody.dataset.latestLogId || "0");
const currentUrl = new URL(window.location.href);

async function refreshWhenNewLogExists() {
  try {
    currentUrl.searchParams.set("_", Date.now().toString());
    const response = await fetch(currentUrl.href, {
      headers: { "X-Requested-With": "security-log-refresh" },
      cache: "no-store",
    });
    const html = await response.text();
    const match = html.match(/data-latest-log-id="(\d+)"/);
    const nextLogId = match ? Number(match[1]) : 0;

    if (nextLogId > latestLogId) {
      const nextDocument = new DOMParser().parseFromString(html, "text/html");
      const nextTableBody = nextDocument.querySelector(".security-log-table tbody");
      const currentTableBody = document.querySelector(".security-log-table tbody");

      if (nextTableBody && currentTableBody) {
        currentTableBody.innerHTML = nextTableBody.innerHTML;
        latestLogId = nextLogId;
        securityLogBody.dataset.latestLogId = String(nextLogId);
      } else {
        window.location.reload();
      }
    }
  } catch (error) {
    console.error("Không kiểm tra được nhật ký mới:", error);
  }
}

setInterval(refreshWhenNewLogExists, 5000);
