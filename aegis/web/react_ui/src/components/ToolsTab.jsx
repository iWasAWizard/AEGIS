import React, { useEffect, useState } from 'react';

export default function ToolsTab() {
  const [tools, setTools] = useState([]);

  useEffect(() => {
    fetch('/tools')
      .then(res => res.json())
      .then(data => setTools(data.tools || []))
      .catch(err => console.error("Error fetching tools:", err));
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">🧰 Available Tools</h2>
      {tools.length === 0 ? (
        <p>No tools registered.</p>
      ) : (
        <ul className="space-y-4">
          {tools.map((tool) => (
            <li key={tool.name} className="border p-4 rounded bg-gray-900">
              <h3 className="text-lg font-bold">{tool.name}</h3>
              <p className="text-sm text-gray-300 mb-2">{tool.description}</p>
              <pre className="bg-black text-green-300 text-xs p-2 overflow-x-auto">
                {JSON.stringify(tool.input_schema, null, 2)}
              </pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
