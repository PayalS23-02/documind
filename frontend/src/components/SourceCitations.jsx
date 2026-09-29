export default function SourceCitations({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="citations">
      <div className="citations__label">Sources</div>
      <ul>
        {sources.map((s, i) => (
          <li key={i} className="citation">
            <span className="citation__doc">{s.document}</span>
            <span className="citation__meta">
              {" "}
              — "{s.section}", page {s.page}{" "}
              <span className="citation__similarity">
                ({Math.round(s.similarity * 100)}% match)
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
