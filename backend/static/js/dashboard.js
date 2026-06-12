const temperatureValue = document.getElementById("temperatureValue");
const humidityValue = document.getElementById("humidityValue");
const deviceStatus = document.getElementById("deviceStatus");
const lastUpdated = document.getElementById("lastUpdated");
const warningBox = document.getElementById("warningBox");
const warningIcon = document.getElementById("warningIcon");
const warningText = document.getElementById("warningText");
const tempCard = document.getElementById("tempCard");
const humCard = document.getElementById("humCard");
const tempStatus = document.getElementById("tempStatus");
const humStatus = document.getElementById("humStatus");
const statusCard = document.querySelector(".metric-card.status");
const historyTable = document.getElementById("historyTable");
const chartCanvas = document.getElementById("historyChart");

const POLL_INTERVAL_MS = 5000;
const HISTORY_IDLE_REFRESH_MS = 60000;

let historyChart;
let lastSensorSignature = null;
let lastHistoryRefreshAt = 0;

function formatTime(value) {
  if (!value) {
    return "Chưa có dữ liệu";
  }
  return new Date(value).toLocaleString("vi-VN");
}

function formatNumber(value, suffix) {
  if (value === null || value === undefined) {
    return "--";
  }
  return `${Number(value).toFixed(1)}${suffix}`;
}

function buildSensorSignature(latest) {
  if (!latest) {
    return null;
  }
  return `${Number(latest.temperature).toFixed(1)}|${Number(latest.humidity).toFixed(1)}`;
}

function shouldRefreshHistory(latest) {
  const now = Date.now();
  const signature = buildSensorSignature(latest);

  if (lastHistoryRefreshAt === 0) {
    lastSensorSignature = signature;
    return true;
  }

  if (signature !== lastSensorSignature) {
    lastSensorSignature = signature;
    return true;
  }

  return now - lastHistoryRefreshAt >= HISTORY_IDLE_REFRESH_MS;
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

const LEVEL_ICONS = {
  cold: "!",
  safe: "Đạt",
  warm: "!",
  hot: "!",
  dry: "!",
  humid: "!",
  too_humid: "!",
};

function applyCardLevel(card, level) {
  card.classList.remove("cold", "safe", "warm", "hot", "dry", "humid", "too_humid");
  card.classList.add(level);
}

async function loadLatest() {
  const result = await fetchJson("/api/latest");
  const latest = result.data;

  if (!latest) {
    temperatureValue.textContent = "--";
    humidityValue.textContent = "--";
    deviceStatus.textContent = "Ngoại tuyến";
    lastUpdated.textContent = "Chưa có dữ liệu";
    warningBox.classList.add("hidden");
    tempCard.className = "metric-card temperature";
    humCard.className = "metric-card humidity";
    tempStatus.textContent = "";
    humStatus.textContent = "";
    updateStatusClass("offline");
    return null;
  }

  temperatureValue.textContent = formatNumber(latest.temperature, "°C");
  humidityValue.textContent = formatNumber(latest.humidity, "%");
  deviceStatus.textContent = result.device_status === "online" ? "Trực tuyến" : "Ngoại tuyến";
  const receivedAt = result.last_seen || latest.created_at;
  lastUpdated.textContent = `Cập nhật: ${formatTime(receivedAt)}`;
  updateStatusClass(result.device_status);

  if (result.alert) {
    const tempAlert = result.alert.temperature;
    const humAlert = result.alert.humidity;
    const overall = result.alert.overall;

    applyCardLevel(tempCard, tempAlert.level);
    applyCardLevel(humCard, humAlert.level);

    tempStatus.textContent = `${LEVEL_ICONS[tempAlert.level] || ""} ${tempAlert.message}`;
    humStatus.textContent = `${LEVEL_ICONS[humAlert.level] || ""} ${humAlert.message}`;

    if (overall !== "safe") {
      warningBox.classList.remove("hidden", "safe", "warning", "danger");
      warningBox.classList.add(overall);
      warningIcon.textContent = "Cảnh báo:";
      warningText.textContent = result.alert.message;
    } else {
      warningBox.classList.add("hidden");
    }
  }

  return latest;
}

function updateStatusClass(status) {
  statusCard.classList.toggle("online", status === "online");
  statusCard.classList.toggle("offline", status !== "online");
}

async function loadHistory() {
  const result = await fetchJson("/api/history?limit=50");
  const rows = result.data || [];
  renderTable(rows);
  renderChart(rows);
  lastHistoryRefreshAt = Date.now();
}

function renderTable(rows) {
  if (rows.length === 0) {
    historyTable.innerHTML = '<tr><td colspan="5">Chưa có dữ liệu.</td></tr>';
    return;
  }

  historyTable.innerHTML = rows
    .slice()
    .reverse()
    .map(
      (row) => `
        <tr>
          <td>${row.id}</td>
          <td>${row.device_id}</td>
          <td>${formatNumber(row.temperature, "°C")}</td>
          <td>${formatNumber(row.humidity, "%")}</td>
          <td>${formatTime(row.created_at)}</td>
        </tr>
      `
    )
    .join("");
}

function renderChart(rows) {
  const labels = rows.map((row) => new Date(row.created_at).toLocaleTimeString("vi-VN"));
  const temperatures = rows.map((row) => Number(row.temperature));
  const humidity = rows.map((row) => Number(row.humidity));

  if (!historyChart) {
    historyChart = new Chart(chartCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Nhiệt độ (°C)",
            data: temperatures,
            borderColor: "#ea580c",
            backgroundColor: "rgba(234, 88, 12, 0.12)",
            tension: 0.3,
          },
          {
            label: "Độ ẩm (%)",
            data: humidity,
            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.12)",
            tension: 0.3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    });
    return;
  }

  historyChart.data.labels = labels;
  historyChart.data.datasets[0].data = temperatures;
  historyChart.data.datasets[1].data = humidity;
  historyChart.update();
}

async function refreshDashboard() {
  try {
    const latest = await loadLatest();
    if (shouldRefreshHistory(latest)) {
      await loadHistory();
    }
  } catch (error) {
    console.error("Không tải được dữ liệu bảng điều khiển:", error);
    warningBox.classList.remove("hidden", "safe", "warning", "danger");
    warningBox.classList.add("warning");
    warningIcon.textContent = "Lỗi kết nối:";
    warningText.textContent = "Bảng điều khiển chưa đọc được API, hãy kiểm tra Flask server và đăng nhập.";
  }
}

refreshDashboard();
setInterval(refreshDashboard, POLL_INTERVAL_MS);
