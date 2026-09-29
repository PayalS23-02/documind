import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import UploadPanel from "./components/UploadPanel";
import { checkHealth } from "./api";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [docCount, setDocCount] = useState(0);

  useEffect(() => {
    checkHealth().then((health) => {
      if (health) {
        setBackendStatus("online");
        setDocCount(health.collection_count ?? 0);
      } else {
        setBackendStatus("offline");
      }
    });
  }, []);

  function handleIngested() {
    checkHealth().then((health) => {
      if (health) setDocCount(health.collection_count ?? 0);
    });
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>DocuMind</h1>
        <p className="tagline">
          Ask questions about academic handbooks, catalogs, and policies — grounded and
          cited.
        </p>
        <div className={`status status--${backendStatus}`}>
          Backend: {backendStatus}
          {backendStatus === "online" && ` · ${docCount} chunks indexed`}
        </div>
      </header>

      <main className="app__main">
        <UploadPanel onIngested={handleIngested} />
        <ChatWindow />
      </main>
    </div>
  );
}
