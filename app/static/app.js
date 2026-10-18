const tabPictures = document.getElementById("tab-pictures");
const tabFiles = document.getElementById("tab-files");
const panelPictures = document.getElementById("panel-pictures");
const panelFiles = document.getElementById("panel-files");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");

tabPictures.addEventListener("click", () => selectMode("pictures"));
tabFiles.addEventListener("click", () => selectMode("files"));

function selectMode(mode) {
  const pictures = mode === "pictures";
  tabPictures.setAttribute("aria-selected", String(pictures));
  tabFiles.setAttribute("aria-selected", String(!pictures));
  panelPictures.hidden = !pictures;
  panelFiles.hidden = pictures;
  hideError();
}

function hideError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
  result.hidden = true;
}

bindDrop("file-first", "drop-first", "name-first", "preview-first");
bindDrop("file-second", "drop-second", "name-second", "preview-second");

function bindDrop(inputId, dropId, nameId, previewId) {
  const input = document.getElementById(inputId);
  const drop = document.getElementById(dropId);
  const name = document.getElementById(nameId);
  const preview = document.getElementById(previewId);

  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (!file) return;
    name.textContent = file.name;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.add("over");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.remove("over");
    });
  });
  drop.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change"));
  });
}

document.getElementById("picture-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  const first = document.getElementById("file-first").files[0];
  const second = document.getElementById("file-second").files[0];
  if (!first || !second) {
    showError("Choose two images first.");
    return;
  }
  const body = new FormData();
  body.append("first", first);
  body.append("second", second);
  await submit("/api/pictures", { method: "POST", body }, "picture-submit");
});

document.getElementById("file-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  const text = document.getElementById("shared-text").value;
  await submit(
    "/api/files",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    },
    "file-submit",
  );
});

async function submit(url, options, buttonId) {
  const button = document.getElementById(buttonId);
  const previous = button.textContent;
  button.disabled = true;
  button.textContent = "Building…";
  try {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) {
      showError(payload.detail || "The server could not build the pair.");
      return;
    }
    render(payload);
  } catch (err) {
    showError("Could not reach the local server.");
  } finally {
    button.disabled = false;
    button.textContent = previous;
  }
}

function render(payload) {
  result.hidden = false;
  document.getElementById("md5").textContent = payload.md5;
  const cards = document.getElementById("cards");
  cards.replaceChildren();
  payload.files.forEach((file, index) => {
    const card = document.createElement("article");
    card.className = "card";
    const title = document.createElement("h2");
    title.textContent = file.name;
    card.append(title);
    if (payload.kind === "gif") {
      const img = document.createElement("img");
      img.alt = file.name;
      img.src = `data:${file.media_type};base64,${file.base64}`;
      card.append(img);
    }
    const sha = document.createElement("p");
    sha.className = "hash";
    sha.textContent = file.sha256;
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `SHA-256 · ${file.size.toLocaleString()} bytes`;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "download";
    button.textContent = "Download";
    button.addEventListener("click", () => download(file));
    card.append(sha, meta, button);
    cards.append(card);
  });

  const count = payload.diff.length;
  document.getElementById("diff-count").textContent =
    `${count} byte${count === 1 ? "" : "s"} differ. Highlighted below.`;
  document.getElementById("dump-left").innerHTML = dump(payload.blocks.left, payload.blocks.right);
  document.getElementById("dump-right").innerHTML = dump(payload.blocks.right, payload.blocks.left);
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

function dump(bytes, other) {
  const rows = [];
  for (let offset = 0; offset < bytes.length; offset += 16) {
    const cells = [];
    for (let column = 0; column < 16; column += 1) {
      const index = offset + column;
      const hex = bytes[index].toString(16).padStart(2, "0");
      if (bytes[index] !== other[index]) cells.push(`<span class="hit">${hex}</span>`);
      else cells.push(hex);
    }
    const label = offset.toString(16).padStart(2, "0");
    rows.push(`${label}  ${cells.join(" ")}`);
  }
  return rows.join("\n");
}

function download(file) {
  const binary = atob(file.base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const url = URL.createObjectURL(new Blob([bytes], { type: file.media_type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  link.click();
  URL.revokeObjectURL(url);
}
