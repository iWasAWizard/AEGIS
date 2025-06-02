import React, { useEffect, useState } from 'react';

export default function ConfigTab() {
  const [config, setConfig] = useState({});
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetch('/config')
      .then(res => res.json())
      .then(data => setConfig(data || {}))
      .catch(err => console.error("Error loading config:", err));
  }, []);

  const handleChange = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    fetch('/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
      .then((res) => {
        if (res.ok) setStatus('✅ Config saved.');
        else setStatus('❌ Failed to save.');
      })
      .catch(() => setStatus('❌ Error during save.'));
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">⚙️ Agent Configuration</h2>
      <div className="space-y-3">
        {Object.entries(config).map(([key, val]) => (
          <div key={key}>
            <label className="block text-sm font-bold">{key}</label>
            <input
              className="bg-gray-800 text-white p-1 rounded w-full"
              value={val}
              onChange={(e) => handleChange(key, e.target.value)}
            />
          </div>
        ))}
      </div>
      <button
        onClick={handleSave}
        className="mt-4 bg-green-700 text-white px-4 py-2 rounded"
      >
        Save Config
      </button>
      {status && <p className="mt-2 text-sm">{status}</p>}
    </div>
  );
}
