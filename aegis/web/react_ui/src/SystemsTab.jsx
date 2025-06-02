import React, { useEffect, useState } from 'react';

export default function SystemsTab() {
  const [inventory, setInventory] = useState([]);

  useEffect(() => {
    fetch('/inventory')
      .then(res => res.json())
      .then(data => setInventory(data.inventory || []));
  }, []);

  return (
    <div>
      <h2>🖥️ System Inventory</h2>
      {inventory.length === 0 && <p>Loading...</p>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
        {inventory.map((item, index) => (
          <div key={index} style={{
            border: '1px solid var(--border)',
            padding: '1rem',
            borderRadius: '8px',
            backgroundColor: item.error ? '#330000' : 'var(--input-bg)',
            color: item.error ? '#ff6666' : 'var(--input-fg)',
            minWidth: '300px'
          }}>
            <h3>{item.name}</h3>
            {item.error ? (
              <p><strong>Error:</strong> {item.error}</p>
            ) : (
              <ul>
                {Object.entries(item.data).map(([key, val]) => (
                  <li key={key}><strong>{key}:</strong> {val}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
