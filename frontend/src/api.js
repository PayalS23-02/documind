const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Upload one or more PDF files to be ingested into the knowledge base.
 */
export async function ingestFiles(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const res = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const detail = await safeErrorDetail(res);
    throw new Error(detail || `Ingest failed with status ${res.status}`);
  }

  return res.json(); // { documents_ingested, chunks_stored }
}

/**
 * Ask a question and get a grounded, cited answer back.
 */
export async function askQuestion(question, topK) {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK ?? null }),
  });

  if (!res.ok) {
    const detail = await safeErrorDetail(res);
    throw new Error(detail || `Query failed with status ${res.status}`);
  }

  return res.json(); // { answer, sources: [{document, section, page, similarity}] }
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function safeErrorDetail(res) {
  try {
    const body = await res.json();
    return body.detail || JSON.stringify(body);
  } catch {
    return null;
  }
}
