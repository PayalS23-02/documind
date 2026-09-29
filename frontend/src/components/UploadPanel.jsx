import { useRef, useState } from "react";
import { ingestFiles } from "../api";

export default function UploadPanel({ onIngested }) {
  const inputRef = useRef(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");

  async function handleFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;

    setStatus("uploading");
    setMessage(`Ingesting ${files.length} file(s)...`);

    try {
      const result = await ingestFiles(files);
      setStatus("done");
      setMessage(
        `Ingested ${result.documents_ingested} document(s), ${result.chunks_stored} chunks stored.`
      );
      onIngested?.(result);
    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Ingestion failed.");
    }
  }

  return (
    <div className="upload-panel">
      <div
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <p>Drop PDF handbooks/catalogs here, or click to select files.</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {message && <p className={`upload-status upload-status--${status}`}>{message}</p>}
    </div>
  );
}
