const params = new URLSearchParams(window.location.search);
const queryToken = params.get("token");
if (queryToken) {
  localStorage.setItem("gameToolToken", queryToken);
}
const token = localStorage.getItem("gameToolToken") || "";

const envKeys = [
  "PUBLIC_IP",
  "SOURCE_ROOT",
  "MYSQL_ROOT_PASSWORD",
  "MYSQL_PORT",
  "COMPOSE",
  "IMPORT_DB",
  "FORCE_IMPORT_DB",
  "REMOVE_BACKDOORS",
  "START_GAME",
  "START_ZONE2",
];

let lastStatus = null;
let configDirty = false;

function api(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  return fetch(path, { ...options, headers }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  });
}

function fmtSize(size) {
  if (!size) return "";
  if (size > 1024 * 1024 * 1024) return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (size > 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.round(size / 1024)} KB`;
}

function renderAssets(paths) {
  const labels = {
    serverArchive: "手工端压缩包",
    serverExtracted: "服务端目录",
    tiandaoZip: "天道压缩包",
    apk: "天道 APK",
    dockerPackage: "Docker 打包",
    dockerData: "部署数据",
  };
  const root = document.getElementById("assetList");
  root.innerHTML = Object.entries(labels)
    .map(([key, label]) => {
      const item = paths[key] || {};
      const state = item.exists ? "已找到" : "缺失";
      const size = item.size ? ` · ${fmtSize(item.size)}` : "";
      return `<div class="asset">
        <strong>${label}</strong>
        <code>${item.path || ""}${size}</code>
        <span class="pill ${item.exists ? "" : "missing"}">${state}</span>
      </div>`;
    })
    .join("");
}

function renderApkTools(tools) {
  const labels = {
    apktool: "apktool",
    apksigner: "apksigner",
    zipalign: "zipalign",
  };
  const root = document.getElementById("apkTools");
  root.innerHTML = Object.entries(labels)
    .map(([key, label]) => {
      const item = tools[key] || {};
      return `<div class="asset">
        <strong>${label}</strong>
        <code>${item.output || "-"}</code>
        <span class="pill ${item.ok ? "" : "missing"}">${item.ok ? "可用" : "缺失"}</span>
      </div>`;
    })
    .join("");
}

function fillConfig(config) {
  const form = document.getElementById("configForm");
  if (configDirty) return;
  envKeys.forEach((key) => {
    const input = form.elements[key];
    if (!input) return;
    if (input.type === "checkbox") {
      input.checked = String(config[key] || "0") === "1";
    } else {
      input.value = config[key] || "";
    }
  });
}

function readConfig() {
  const form = document.getElementById("configForm");
  const values = {};
  envKeys.forEach((key) => {
    const input = form.elements[key];
    if (!input) return;
    values[key] = input.type === "checkbox" ? (input.checked ? "1" : "0") : input.value;
  });
  return values;
}

function renderTasks(tasks) {
  const select = document.getElementById("taskSelect");
  const previous = select.value;
  select.innerHTML = "";
  tasks.forEach((task) => {
    const option = document.createElement("option");
    option.value = task.id;
    option.textContent = `${task.name} · ${task.status}`;
    select.appendChild(option);
  });
  if ([...select.options].some((opt) => opt.value === previous)) {
    select.value = previous;
  }
  renderSelectedTask(tasks);
}

function renderSelectedTask(tasks) {
  const select = document.getElementById("taskSelect");
  const log = document.getElementById("taskLog");
  const task = tasks.find((item) => item.id === select.value) || tasks[0];
  if (!task) {
    log.textContent = "暂无任务。";
    return;
  }
  select.value = task.id;
  const header = `[${task.status}] ${task.name}\n${task.command}\n\n`;
  log.textContent = header + (task.log || []).join("\n");
  log.scrollTop = log.scrollHeight;
}

async function refresh() {
  try {
    const data = await api("/api/status");
    lastStatus = data;
    renderAssets(data.paths);
    renderApkTools(data.tools);
    fillConfig(data.config);
    document.getElementById("composeStatus").textContent =
      data.tools.composePs.output || data.tools.docker.output || "暂无状态。";
    renderTasks(data.tasks || []);
  } catch (err) {
    document.getElementById("composeStatus").textContent = `加载失败：${err.message}`;
  }
}

async function saveConfig() {
  await api("/api/config", { method: "POST", body: readConfig() });
  configDirty = false;
  await refresh();
}

async function runAction(action) {
  await saveConfig();
  const data = await api("/api/task", { method: "POST", body: { action } });
  await refresh();
  document.querySelector('[data-section="logs"]').click();
  const select = document.getElementById("taskSelect");
  select.value = data.task.id;
}

document.querySelectorAll(".nav").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".section").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.section).classList.add("active");
  });
});

document.getElementById("refreshBtn").addEventListener("click", refresh);
document.getElementById("saveConfigBtn").addEventListener("click", saveConfig);
document.getElementById("taskSelect").addEventListener("change", () => renderSelectedTask(lastStatus?.tasks || []));
document.getElementById("configForm").addEventListener("input", () => {
  configDirty = true;
});
document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action).catch((err) => alert(err.message)));
});

refresh();
setInterval(refresh, 3000);
