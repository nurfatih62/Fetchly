(() => {
  "use strict";

  const elements = {
    ffmpegBanner: document.getElementById("ffmpeg-banner"),
    lookupForm: document.getElementById("lookup-form"),
    urlInput: document.getElementById("url-input"),
    pasteButton: document.getElementById("paste-button"),
    clearButton: document.getElementById("clear-button"),
    checkButton: document.getElementById("check-button"),
    formError: document.getElementById("form-error"),
    preview: document.getElementById("preview"),
    previewThumb: document.getElementById("preview-thumb"),
    platformBadge: document.getElementById("platform-badge"),
    previewTitle: document.getElementById("preview-title"),
    previewUploader: document.getElementById("preview-uploader"),
    previewDuration: document.getElementById("preview-duration"),
    downloadForm: document.getElementById("download-form"),
    downloadButton: document.getElementById("download-button"),
    downloadStatus: document.getElementById("download-status"),
    downloadError: document.getElementById("download-error"),
    qualityRow: document.getElementById("quality-row"),
    quality: document.getElementById("quality"),
  };

  const state = {
    checking: false,
    downloading: false,
    current: null,
    infoRequestId: 0,
    infoController: null,
  };

  const PLATFORM_LABELS = {
    youtube: "YouTube",
    tiktok: "TikTok",
  };

  function showError(element, message) {
    element.textContent = message;
    element.hidden = false;
  }

  function clearError(element) {
    element.textContent = "";
    element.hidden = true;
  }

  function syncButtons() {
    elements.checkButton.disabled = state.checking || state.downloading;
    elements.checkButton.textContent = state.checking ? "Memeriksa..." : "Cek video";
    elements.downloadButton.disabled = state.downloading || !state.current;
    elements.downloadButton.textContent = state.downloading
      ? "Menyiapkan..."
      : "Unduh";
    elements.pasteButton.disabled = state.downloading;
    elements.clearButton.disabled = state.downloading;
    elements.lookupForm.setAttribute(
      "aria-busy",
      state.checking ? "true" : "false"
    );
    elements.downloadForm.setAttribute(
      "aria-busy",
      state.downloading ? "true" : "false"
    );
  }

  function formatDuration(value) {
    const total = Math.floor(Number(value));
    if (!Number.isFinite(total) || total <= 0) {
      return "Tidak diketahui";
    }

    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;

    if (hours > 0) {
      return `${hours} jam ${minutes} menit`;
    }
    if (minutes > 0) {
      return `${minutes} menit ${String(seconds).padStart(2, "0")} detik`;
    }
    return `${seconds} detik`;
  }

  function selectedFormat() {
    const selected = elements.downloadForm.querySelector(
      'input[name="format"]:checked'
    );
    return selected && selected.value === "mp3" ? "mp3" : "mp4";
  }

  function syncFormatFields() {
    const isAudio = selectedFormat() === "mp3";
    elements.qualityRow.hidden = isAudio;
    elements.quality.disabled = isAudio;
  }

  function resetPreview() {
    state.current = null;
    elements.preview.hidden = true;
    elements.previewThumb.hidden = true;
    elements.previewThumb.removeAttribute("src");
    elements.downloadStatus.textContent = "";
    elements.downloadStatus.classList.remove("is-success");
    clearError(elements.downloadError);
    elements.quality.replaceChildren(new Option("Terbaik", "best"));
    for (const radio of elements.downloadForm.querySelectorAll(
      'input[name="format"]'
    )) {
      radio.checked = radio.value === "mp4";
    }
    syncFormatFields();
    syncButtons();
  }

  function renderPreview(data) {
    state.current = {
      url: data.__sourceUrl,
      platform: data.platform,
      title: data.title,
    };

    elements.previewTitle.textContent = data.title || "Video tanpa judul";
    elements.previewUploader.textContent = data.uploader || "Tidak diketahui";
    elements.previewDuration.textContent = formatDuration(data.duration);
    elements.platformBadge.textContent =
      PLATFORM_LABELS[data.platform] || "Video";

    if (data.thumbnail) {
      elements.previewThumb.hidden = false;
      elements.previewThumb.alt = `Pratinjau video: ${data.title || ""}`;
      elements.previewThumb.src = data.thumbnail;
    } else {
      elements.previewThumb.hidden = true;
      elements.previewThumb.removeAttribute("src");
      elements.previewThumb.alt = "";
    }

    elements.quality.replaceChildren(new Option("Terbaik", "best"));
    for (const format of data.formats || []) {
      const height = Number(format.height);
      if (!Number.isFinite(height) || height <= 0) {
        continue;
      }
      elements.quality.add(
        new Option(format.quality || `${height}p`, String(height))
      );
    }
    elements.quality.value = "best";

    for (const radio of elements.downloadForm.querySelectorAll(
      'input[name="format"]'
    )) {
      radio.checked = radio.value === "mp4";
    }
    syncFormatFields();

    elements.downloadStatus.textContent = "";
    elements.downloadStatus.classList.remove("is-success");
    clearError(elements.downloadError);

    elements.preview.hidden = false;
    syncButtons();
  }

  async function readErrorMessage(response, fallback) {
    try {
      const data = await response.json();
      if (data && data.error && data.error.message) {
        return data.error.message;
      }
    } catch (_error) {
      // Respons bukan JSON; pakai pesan cadangan.
    }
    return fallback;
  }

  async function checkVideo(event) {
    event.preventDefault();
    if (state.downloading) {
      return;
    }

    const url = elements.urlInput.value.trim();
    clearError(elements.formError);

    if (!url) {
      showError(
        elements.formError,
        "Link tidak valid. Tempel link video YouTube atau TikTok."
      );
      elements.urlInput.focus();
      return;
    }

    if (state.infoController) {
      state.infoController.abort();
    }
    const controller = new AbortController();
    state.infoController = controller;
    const requestId = ++state.infoRequestId;
    let timedOut = false;

    state.checking = true;
    resetPreview();
    syncButtons();

    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 60000);

    try {
      const response = await fetch("/api/info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      });

      if (requestId !== state.infoRequestId) {
        return;
      }

      if (!response.ok) {
        const message = await readErrorMessage(
          response,
          "Video tidak bisa diperiksa. Coba lagi."
        );
        if (requestId === state.infoRequestId) {
          showError(elements.formError, message);
          elements.urlInput.focus();
        }
        return;
      }

      const data = await response.json();
      if (requestId !== state.infoRequestId) {
        return;
      }

      if (elements.urlInput.value.trim() !== url) {
        return;
      }

      data.__sourceUrl = url;
      renderPreview(data);
      elements.previewTitle.setAttribute("tabindex", "-1");
      elements.previewTitle.focus({ preventScroll: true });
    } catch (error) {
      if (error.name === "AbortError") {
        if (timedOut && requestId === state.infoRequestId) {
          showError(
            elements.formError,
            "Proses terlalu lama. Coba lagi beberapa saat."
          );
        }
        return;
      }
      if (requestId === state.infoRequestId) {
        showError(
          elements.formError,
          "Tidak bisa terhubung ke aplikasi. Pastikan server masih berjalan."
        );
      }
    } finally {
      window.clearTimeout(timeoutId);
      if (requestId === state.infoRequestId) {
        state.checking = false;
        state.infoController = null;
        syncButtons();
      }
    }
  }

  async function handleDownload(event) {
    event.preventDefault();
    if (!state.current || state.downloading) {
      return;
    }

    const format = selectedFormat();
    const quality = format === "mp3" ? "best" : elements.quality.value;
    clearError(elements.downloadError);
    elements.downloadStatus.textContent =
      "Mengunduh dan menyiapkan file. Jangan tutup halaman ini.";
    elements.downloadStatus.classList.remove("is-success");

    state.downloading = true;
    syncButtons();

    try {
      const response = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: state.current.url,
          format,
          quality,
        }),
      });

      if (!response.ok) {
        const message = await readErrorMessage(
          response,
          "Unduhan gagal. Coba lagi atau pilih kualitas yang lebih rendah."
        );
        elements.downloadStatus.textContent = "";
        showError(elements.downloadError, message);
        return;
      }

      const blob = await response.blob();
      if (!blob.size) {
        throw new Error("File kosong");
      }

      const filename = getFilename(response.headers.get("content-disposition"))
        || (format === "mp3" ? "audio.mp3" : "video.mp4");
      saveBlob(blob, filename);

      elements.downloadStatus.textContent =
        "Berhasil diunduh. File ada di folder unduhanmu.";
      elements.downloadStatus.classList.add("is-success");
    } catch (error) {
      elements.downloadStatus.textContent = "";
      showError(
        elements.downloadError,
        error.name === "TypeError"
          ? "Tidak bisa terhubung ke aplikasi. Pastikan server masih berjalan."
          : "Unduhan gagal saat menyimpan file. Coba lagi."
      );
    } finally {
      state.downloading = false;
      syncButtons();
    }
  }

  function getFilename(header) {
    if (!header) {
      return null;
    }

    const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1].trim()).split(/[\\/]/).pop();
      } catch (_error) {
        // Lanjut ke bentuk filename biasa.
      }
    }

    const quoted = /filename="([^"]*)"/i.exec(header);
    if (quoted) {
      return quoted[1].split(/[\\/]/).pop();
    }

    const plain = /filename=([^;]+)/i.exec(header);
    return plain ? plain[1].trim().split(/[\\/]/).pop() : null;
  }

  function saveBlob(blob, filename) {
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
  }

  async function pasteLink() {
    clearError(elements.formError);
    try {
      if (!navigator.clipboard || !navigator.clipboard.readText) {
        throw new Error("Clipboard tidak tersedia");
      }
      const text = (await navigator.clipboard.readText()).trim();
      if (!text) {
        showError(
          elements.formError,
          "Papan klip kosong. Salin link video terlebih dahulu."
        );
        elements.urlInput.focus();
        return;
      }
      elements.urlInput.value = text;
      handleUrlEdited();
      elements.urlInput.focus();
    } catch (_error) {
      showError(
        elements.formError,
        "Browser tidak mengizinkan akses papan klip. Gunakan Ctrl+V untuk menempel."
      );
      elements.urlInput.focus();
    }
  }

  function handleUrlEdited() {
    clearError(elements.formError);
    if (state.current && elements.urlInput.value.trim() !== state.current.url) {
      resetPreview();
    }
  }

  function clearUrl() {
    if (state.infoController) {
      state.infoController.abort();
      state.infoController = null;
    }
    state.infoRequestId += 1;
    state.checking = false;
    elements.urlInput.value = "";
    clearError(elements.formError);
    resetPreview();
    syncButtons();
    elements.urlInput.focus();
  }

  async function loadDependencies() {
    try {
      const response = await fetch("/api/deps");
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      if (data && data.ffmpeg === false) {
        elements.ffmpegBanner.hidden = false;
      }
    } catch (_error) {
      // Tidak perlu mengganggu pengguna jika pemeriksaan gagal.
    }
  }

  elements.lookupForm.addEventListener("submit", checkVideo);
  elements.downloadForm.addEventListener("submit", handleDownload);
  elements.pasteButton.addEventListener("click", pasteLink);
  elements.clearButton.addEventListener("click", clearUrl);
  elements.urlInput.addEventListener("input", handleUrlEdited);
  elements.downloadForm.addEventListener("change", (event) => {
    if (event.target.name === "format") {
      clearError(elements.downloadError);
      elements.downloadStatus.textContent = "";
      elements.downloadStatus.classList.remove("is-success");
      syncFormatFields();
    }
  });
  elements.previewThumb.addEventListener("error", () => {
    elements.previewThumb.hidden = true;
  });

  resetPreview();
  syncFormatFields();
  syncButtons();
  loadDependencies();
})();
