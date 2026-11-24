// An image for an ad or an event card (v4.15.1): upload a picture from the computer (it is made smaller in the
// browser, then stored on the server) or paste an https:// link. The preview shows exactly what students will see.
import { useRef, useState } from "react";
import { MEDIA_PATH, mediaUrl, uploadAdminImage } from "../../services/api";

const MAX_SIDE = 1400;          // pixels, the longer side
const TARGET_BYTES = 400_000;   // the server accepts up to 450 KB

async function shrink(file: File): Promise<{ blob: Blob; name: string }> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("This browser can't prepare the image.");
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close?.();
  const encode = (type: string, q: number) => new Promise<Blob | null>((res) => canvas.toBlob(res, type, q));
  for (const q of [0.86, 0.78, 0.68, 0.58, 0.48]) {
    let blob = await encode("image/webp", q);
    if (!blob || blob.type !== "image/webp") blob = await encode("image/jpeg", q);   // Safari: no WebP encoding
    if (blob && blob.size <= TARGET_BYTES) return { blob, name: blob.type === "image/webp" ? "image.webp" : "image.jpg" };
  }
  throw new Error("The image is still too large after making it smaller. Try a smaller picture.");
}

export function isImageSource(u: string) {
  const v = (u || "").trim();
  return !v || /^https:\/\/\S+$/i.test(v) || MEDIA_PATH.test(v);
}

export default function ImageField({ label, value, onChange, adminKey, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; adminKey: string; placeholder?: string;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const uploaded = MEDIA_PATH.test((value || "").trim());
  const preview = mediaUrl(value);

  const pick = async (file?: File | null) => {
    if (!file) return;
    setError(null);
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      setError("Choose a JPEG, PNG or WebP picture.");
      return;
    }
    setBusy(true);
    try {
      const { blob, name } = await shrink(file);
      const res = await uploadAdminImage(adminKey, blob, name);
      onChange(res.url);
    } catch (e) {
      setError((e as Error).message || "Upload failed. Try again.");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  return (
    <div className="cm-image-field wide">
      <span className="cm-image-label">{label}</span>
      <div className="cm-image-body"
           onDragOver={(e) => { e.preventDefault(); }}
           onDrop={(e) => { e.preventDefault(); void pick(e.dataTransfer.files?.[0]); }}>
        <div className={`cm-image-preview ${preview ? "" : "is-empty"}`}>
          {preview ? <img src={preview} alt="" referrerPolicy="no-referrer" /> : <span>No image</span>}
        </div>
        <div className="cm-image-actions">
          <button type="button" className="admin-btn-secondary" disabled={busy} onClick={() => input.current?.click()}>
            {busy ? "Uploading…" : uploaded || preview ? "Replace image" : "Upload image"}
          </button>
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" hidden
                 onChange={(e) => void pick(e.target.files?.[0])} />
          {value && <button type="button" className="cm-link-btn" onClick={() => onChange("")}>Remove</button>}
          <small className="cm-muted">or drop a picture here, or paste a link:</small>
          <input className="cm-image-link" value={uploaded ? "" : value} maxLength={400}
                 placeholder={uploaded ? "Uploaded image in use" : (placeholder || "https://…")}
                 onChange={(x) => onChange(x.target.value.trim())} aria-label={`${label} link`} />
          {error && <small className="cm-image-error" role="alert">{error}</small>}
          {uploaded && !error && <small className="cm-image-ok">✓ Uploaded. Save to use it in the chat.</small>}
        </div>
      </div>
    </div>
  );
}
