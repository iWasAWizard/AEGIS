import React, { useEffect, useState } from 'react';

export default function PresetsTab() {
  const [presets, setPresets] = useState([]);
  const [current, setCurrent] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', config: '{}' });

  useEffect(() => {
    fetch('/presets')
      .then(res => res.json())
      .then(setPresets);
  }, []);

  const loadPreset = (p) => {
    setCurrent(p.id);
    setForm({
      name: p.name,
      description: p.description,
      config: JSON.stringify(p.config, null, 2)
    });
  };

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const savePreset = async () => {
    const payload = {
      id: current,
      name: form.name,
      description: form.description,
      config: JSON.parse(form.config || '{}')
    };

    await fetch('/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    alert("Preset saved.");
    window.location.reload();
  };

  return (
    <div>
      <h2>🧠 Preset Editor</h2>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <div style={{ flex: 1 }}>
          <h4>Existing Presets</h4>
          {presets.map((p, i) => (
            <div key={i} style={{ marginBottom: '0.25rem' }}>
              <button onClick={() => loadPreset(p)}>{p.name}</button>
            </div>
          ))}
        </div>

        <div style={{ flex: 2 }}>
          <h4>{current ? `Editing: ${current}` : "New Preset"}</h4>
          <input name="name" value={form.name} onChange={handleChange} placeholder="Preset Name" style={{ width: '100%' }} />
          <textarea name="description" value={form.description} onChange={handleChange} placeholder="Description" rows="2" style={{ width: '100%', marginTop: '0.5rem' }} />
          <textarea name="config" value={form.config} onChange={handleChange} placeholder="Config JSON" rows="10" style={{ width: '100%', marginTop: '0.5rem', fontFamily: 'monospace' }} />
          <button onClick={savePreset} style={{ marginTop: '0.5rem' }}>💾 Save</button>
        </div>
      </div>
    </div>
  );
}
