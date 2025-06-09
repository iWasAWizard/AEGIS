// aegis/web/react_ui/src/components/ToolsTab.jsx
import React, { useEffect, useState } from 'react';

/**
 * A component for the "Tools" tab that fetches and displays a list of all
 * tools available to the agent. It shows each tool's name, description,
 * category, safety status, and a detailed view of its input schema.
 * @returns {React.Component} The tools inventory tab component.
 */
export default function ToolsTab() {
  const [tools, setTools] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/inventory')
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to fetch: ${res.status} ${res.statusText}`);
        }
        return res.json();
      })
      .then(data => setTools(data || []))
      .catch(err => {
        console.error("Error fetching tools:", err);
        setError(err.message);
      });
  }, []);

  return (
    <div>
      <h2 style={{ fontSize: '1.2em', marginBottom: '1rem' }}>🧰 Available Tools</h2>
      {error && <p style={{ color: '#ff6666' }}>Error loading tools: {error}</p>}
      {!error && tools.length === 0 ? (
        <p>No tools are registered or the API is not responding.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '1rem' }}>
          {tools.map((tool) => (
            <div key={tool.name} style={{ border: '1px solid var(--border)', padding: '1rem', borderRadius: '4px', backgroundColor: 'var(--input-bg)' }}>
              <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', color: 'var(--accent)', margin: '0 0 0.5rem 0' }}>{tool.name}</h3>
              <p style={{ fontSize: '0.9em', opacity: 0.8, margin: '0 0 1rem 0' }}>{tool.description}</p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                <span style={{ backgroundColor: '#444', color: '#eee', padding: '2px 8px', borderRadius: '10px', fontSize: '0.8em' }}>{tool.category}</span>
                {tool.safe_mode ? (
                    <span style={{ backgroundColor: '#00522E', color: '#C6F6D5', padding: '2px 8px', borderRadius: '10px', fontSize: '0.8em' }}>Safe</span>
                ) : (
                    <span style={{ backgroundColor: '#8B0000', color: '#FED7D7', padding: '2px 8px', borderRadius: '10px', fontSize: '0.8em' }}>Unsafe</span>
                )}
              </div>
              <details>
                <summary style={{ cursor: 'pointer', fontSize: '0.9em' }}>Input Schema</summary>
                <pre style={{ backgroundColor: '#000', color: '#0f0', fontSize: '0.8em', padding: '0.5rem', marginTop: '0.5rem', overflowX: 'auto', whiteSpace: 'pre-wrap', borderRadius: '4px' }}>
                  {JSON.stringify(tool.input_schema, null, 2)}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}