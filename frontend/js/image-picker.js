/**
 * FarmKonnect image picker
 *
 * Farmers photograph crops and diseased plants from a phone, often on a slow
 * connection, so this component:
 *   - offers both "Take photo" (rear camera) and "Choose photo" (gallery)
 *   - supports tapping or dragging files onto the drop zone
 *   - shrinks large phone photos in the browser before upload
 *   - previews each image with a remove button and a caption/angle selector
 *
 * Usage:
 *   const picker = ImagePicker.mount(container, {
 *     multiple: true, max: 5, maxBytes: 3 * 1024 * 1024,
 *     stages: [{value:"leaf", label:"Leaf / close-up"}, ...],
 *     value: [{src, caption, stage}],   // existing photos, when editing
 *   });
 *   picker.files()                     // File[] selected this session
 *   picker.payload("image")            // { image: File, image_caption: "..." }
 *   picker.appendTo(formData, "images")
 */
(function () {
  "use strict";

  const DEFAULT_ACCEPT = "image/jpeg,image/png,image/webp,image/heic,image/heif";

  const el = (tag, props = {}, children = []) => {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([k, v]) => {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null) node.setAttribute(k, v);
    });
    children.forEach((c) => node.appendChild(c));
    return node;
  };

  const readAsDataUrl = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });

  /**
   * Shrink an oversized photo in the browser (canvas re-encode) so a 12 MP
   * phone shot does not have to crawl over a 2G connection.
   */
  async function compress(file, maxBytes, maxDimension = 1600) {
    if (!file.type.startsWith("image/") || file.type === "image/gif") return file;
    const needsShrink = file.size > maxBytes;
    if (!needsShrink) return file;

    const dataUrl = await readAsDataUrl(file);
    const img = await new Promise((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error("Could not read that image."));
      i.src = dataUrl;
    });

    const scale = Math.min(1, maxDimension / Math.max(img.width, img.height));
    // Only downscale; never blow a small image up.
    const width = Math.round(img.width * scale);
    const height = Math.round(img.height * scale);

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d").drawImage(img, 0, 0, width, height);

    let quality = 0.82;
    let blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", quality));
    // Step the quality down until it fits the budget.
    while (blob && blob.size > maxBytes && quality > 0.4) {
      quality -= 0.15;
      blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", quality));
    }
    if (!blob || blob.size >= file.size) return file; // compression did not help

    const name = (file.name || "photo").replace(/\.[^.]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg", lastModified: Date.now() });
  }

  class ImagePicker {
    constructor(container, options = {}) {
      this.host = typeof container === "string" ? document.querySelector(container) : container;
      if (!this.host) throw new Error("ImagePicker: container not found");

      this.opts = {
        multiple: options.multiple !== false,
        max: options.max || (options.multiple === false ? 1 : 5),
        maxBytes: options.maxBytes || 3 * 1024 * 1024,
        maxDimension: options.maxDimension || 1600,
        accept: options.accept || DEFAULT_ACCEPT,
        stages: options.stages || [],
        captions: options.captions !== false,
        label: options.label || "Crop or plant photo",
        help: options.help || "Take a clear, close-up photo in daylight. Up to 6 MB per photo.",
        value: options.value || [],
        onChange: options.onChange || null,
      };

      this.selections = [];   // { file, preview, caption, stage }
      this.existing = this.opts.value.map((v) => ({ ...v }));
      this.removed = [];      // existing photos the farmer marked for removal
      this.render();
    }

    /* ---------------- public API ---------------- */

    files() {
      return this.selections.map((s) => s.file);
    }

    /** True when the farmer picked at least one new photo this session. */
    hasFiles() {
      return this.selections.length > 0;
    }

    /**
     * Attach files to a FormData payload: the first photo becomes the record's
     * main `image`, and any extra angles go to `extraField` so the API can store
     * them as additional photos of the same plant.
     *
     * Uploads are always multipart — data URLs would blow the JSON body limit
     * and are much slower on a poor connection.
     */
    appendTo(formData, field = "image", extraField = "images") {
      if (!this.selections.length) return formData;
      const [first, ...rest] = this.selections;
      formData.append(field, first.file);
      rest.forEach((s) => formData.append(extraField, s.file));
      // Angle metadata, in the same order as the files above.
      this.selections.forEach((s) => {
        if (s.stage) formData.append("photo_stage", s.stage);
        if (s.caption) formData.append("caption", s.caption);
      });
      return formData;
    }

    clear() {
      this.selections = [];
      this.render();
    }

    /* ---------------- rendering ---------------- */

    render() {
      this.host.innerHTML = "";
      this.host.classList.add("image-picker");

      const head = el("div", { class: "ip-head" }, [
        el("span", { class: "ip-label", text: this.opts.label }),
        el("span", { class: "ip-count", text: this.countText() }),
      ]);
      this.host.appendChild(head);

      const actions = el("div", { class: "ip-actions" });
      if (this.canAdd()) {
        actions.appendChild(
          this.makeInput("📷 Take photo", "environment", "ip-btn ip-btn-camera")
        );
        actions.appendChild(
          this.makeInput("🖼️ Choose photo", null, "ip-btn ip-btn-gallery")
        );
      }
      this.host.appendChild(actions);

      const drop = el("div", {
        class: "ip-drop",
        text: this.canAdd() ? "or drop a photo here" : "Photo limit reached",
      });
      if (this.canAdd()) this.wireDropTarget(drop);
      this.host.appendChild(drop);

      const grid = el("div", { class: "ip-grid" });
      this.existing.forEach((item, index) => grid.appendChild(this.tile(item, null, index, true)));
      this.selections.forEach((item, index) => grid.appendChild(this.tile(item, index, index, false)));
      if (grid.childNodes.length) this.host.appendChild(grid);

      this.host.appendChild(el("p", { class: "ip-help muted", text: this.opts.help }));
    }

    countText() {
      const total = this.existing.length + this.selections.length;
      return this.opts.multiple ? `${total} / ${this.opts.max}` : total ? "1 selected" : "none yet";
    }

    canAdd() {
      return this.existing.length + this.selections.length < this.opts.max;
    }

    makeInput(text, capture, className) {
      const input = el("input", {
        type: "file",
        accept: this.opts.accept,
        class: "ip-file",
      });
      if (capture) input.setAttribute("capture", capture);
      if (this.opts.multiple) input.setAttribute("multiple", "multiple");

      input.addEventListener("change", () => {
        this.addFiles(Array.from(input.files || []));
        input.value = ""; // let the same file be picked again
      });

      // A visually styled button that forwards clicks to the hidden input.
      const button = el("button", { type: "button", class: className, text });
      button.addEventListener("click", (e) => {
        e.preventDefault();
        input.click();
      });
      const wrap = el("span", { class: "ip-input-wrap" }, [input, button]);
      return wrap;
    }

    wireDropTarget(drop) {
      ["dragenter", "dragover"].forEach((evt) =>
        drop.addEventListener(evt, (e) => {
          e.preventDefault();
          drop.classList.add("ip-drop-active");
        })
      );
      ["dragleave", "drop"].forEach((evt) =>
        drop.addEventListener(evt, (e) => {
          e.preventDefault();
          drop.classList.remove("ip-drop-active");
        })
      );
      drop.addEventListener("drop", (e) => {
        const files = Array.from(e.dataTransfer?.files || []);
        this.addFiles(files);
      });
    }

    tile(item, selectionIndex, key, isExisting) {
      const src = isExisting ? item.src : item.preview;
      const caption = isExisting ? item.caption : item.caption;
      const stage = isExisting ? item.stage : item.stage;

      const media = el("div", { class: "ip-thumb" });
      if (src) {
        media.appendChild(el("img", { src, alt: caption || "Crop photo", loading: "lazy" }));
      } else {
        media.appendChild(el("div", { class: "ip-thumb-empty", text: "🖼️" }));
      }

      const remove = el("button", {
        type: "button",
        class: "ip-remove",
        title: isExisting ? "Mark photo for removal" : "Remove photo",
        text: "×",
      });
      remove.addEventListener("click", () => {
        if (isExisting) this.removeExisting(key);
        else this.removeSelection(selectionIndex);
      });
      media.appendChild(remove);

      const tile = el("div", { class: "ip-tile" + (isExisting ? " ip-tile-existing" : "") }, [media]);

      if (this.opts.captions) {
        const fields = el("div", { class: "ip-fields" });

        if (this.opts.stages.length) {
          const select = el("select", { class: "ip-stage", title: "Which part is this?" });
          select.appendChild(el("option", { value: "", text: "Which part?" }));
          this.opts.stages.forEach((s) =>
            select.appendChild(
              el("option", { value: s.value, text: s.label, selected: stage === s.value ? "selected" : null })
            )
          );
          select.addEventListener("change", () => {
            if (isExisting) this.existing[key].stage = select.value;
            else this.selections[selectionIndex].stage = select.value;
          });
          fields.appendChild(select);
        }

        const captionInput = el("input", {
          type: "text",
          class: "ip-caption",
          placeholder: "Note (optional)",
          value: caption || "",
        });
        captionInput.addEventListener("input", () => {
          if (isExisting) this.existing[key].caption = captionInput.value;
          else this.selections[selectionIndex].caption = captionInput.value;
        });
        fields.appendChild(captionInput);
        tile.appendChild(fields);
      }

      return tile;
    }

    /* ---------------- mutations ---------------- */

    async addFiles(files) {
      const images = files.filter((f) => f.type.startsWith("image/") || /\.(jpe?g|png|webp|heic|heif)$/i.test(f.name));
      if (!images.length) {
        this.notify("Please choose a photo (JPEG, PNG or WebP).", "error");
        return;
      }

      const room = this.opts.max - (this.existing.length + this.selections.length);
      const accepted = images.slice(0, Math.max(room, 0));
      if (images.length > accepted.length) {
        this.notify(`Only ${this.opts.max} photos can be attached — keeping the first ${accepted.length}.`, "warn");
      }

      for (const file of accepted) {
        try {
          const processed = await compress(file, this.opts.maxBytes, this.opts.maxDimension);
          const preview = await readAsDataUrl(processed);
          this.selections.push({
            file: processed,
            preview,
            caption: "",
            stage: this.opts.stages.length === 1 ? this.opts.stages[0].value : "",
            originalSize: file.size,
            storedSize: processed.size,
          });
          if (processed.size < file.size) {
            const saved = Math.round((1 - processed.size / file.size) * 100);
            this.notify(`Photo shrunk by ${saved}% for a faster upload.`, "ok");
          }
        } catch (err) {
          this.notify(err.message || "Could not read that photo.", "error");
        }
      }
      this.render();
    }

    removeSelection(index) {
      this.selections.splice(index, 1);
      this.render();
    }

    removeExisting(index) {
      // Keep the reference so the caller could delete the stored file if needed.
      this.removed.push(this.existing[index]);
      this.existing.splice(index, 1);
      this.render();
    }

    /** Existing photos the farmer marked for removal this session. */
    removedExisting() {
      return [...this.removed];
    }

    notify(message, kind) {
      if (typeof this.opts.onChange === "function") {
        this.opts.onChange({ message, kind, picker: this });
      }
      let note = this.host.querySelector(".ip-note");
      if (!note) {
        note = el("p", { class: "ip-note" });
        this.host.appendChild(note);
      }
      note.className = `ip-note ip-note-${kind || "info"}`;
      note.textContent = message;
    }
  }

  window.ImagePicker = {
    mount(container, options) {
      return new ImagePicker(container, options);
    },
    compress,
    /** Stage options reused by both dashboards. */
    DISEASE_STAGES: [
      { value: "leaf", label: "Leaf / close-up" },
      { value: "whole_plant", label: "Whole plant" },
      { value: "stem", label: "Stem" },
      { value: "fruit", label: "Fruit / pod" },
      { value: "root", label: "Root" },
      { value: "field", label: "Whole field" },
    ],
  };
})();
