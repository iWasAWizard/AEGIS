import React, { useEffect, useState } from 'react';

export default function ReportsTab() {
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState([]);
  const [diffs, setDiffs] = useState([]);

  useEffect(() => {
    fetch('/reports')
      .then(res => res.json())
      .then(setReports);
  }, []);

  const toggleSelect = (id) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    );
  };

  const handleCompare = async () => {
    const res = await fetch('/compare_reports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(selected)
    });
    const json = await res.json();
    setDiffs(json.diffs || []);
  };

  return (
    <div>
      <h2>📄 Reports</h2>
      {reports.length === 0 && <p>No reports available.</p>}
      {reports.map((r, i) => (
        <div key={i} style={{
          border: '1px solid var(--border)',
          marginBottom: '0.5rem',
          padding: '0.5rem',
          borderRadius: '6px',
          backgroundColor: selected.includes(r.id) ? '#1c1c2b' : 'var(--input-bg)'
        }}>
          <input type="checkbox" onChange={() => toggleSelect(r.id)} checked={selected.includes(r.id)} />
          <strong style={{ marginLeft: '0.5rem' }}>{r.id}</strong>
          <div style={{ fontSize: '0.9em', opacity: 0.7 }}>{r.timestamp}</div>
          <a href={`/reports/${r.id}.json`} style={{ float: 'right' }} download>⬇️</a>
        </div>
      ))}

      {selected.length >= 2 && (
        <button onClick={handleCompare} style={{ marginTop: '1rem' }}>
          Compare Selected ({selected.length})
        </button>
      )}

      {diffs.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h3>🔍 Comparison Results</h3>
          {diffs.map((diff, i) => (
            <div key={i} style={{
              border: '1px dashed var(--border)',
              padding: '0.5rem',
              marginBottom: '1rem',
              whiteSpace: 'pre-wrap',
              backgroundColor: '#111',
              color: '#0f0',
              fontFamily: 'monospace',
              fontSize: '0.85em'
            }}>
              <div style={{ marginBottom: '0.5rem', fontWeight: 'bold' }}>
                {diff.from} ⟷ {diff.to}
              </div>
              {diff.diff || 'No diff found'}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
