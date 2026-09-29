import SourceCitations from "./SourceCitations";

export default function MessageBubble({ role, content, sources, isError }) {
  const isUser = role === "user";

  return (
    <div className={`message message--${isUser ? "user" : "assistant"}`}>
      <div className={`bubble ${isError ? "bubble--error" : ""}`}>
        <p>{content}</p>
        {!isUser && <SourceCitations sources={sources} />}
      </div>
    </div>
  );
}
