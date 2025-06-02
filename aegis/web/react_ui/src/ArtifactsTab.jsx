import React, { useEffect, useState } from 'react';

export default function ArtifactsTab() {
  const [files, setFiles] = useState([]);

  useEffect(() => {
    fetch('/artifacts')
      .then(res => res.json())
      .then(setFiles);
  }, []);

  return (
    <div>
      <h2>📦 Artifacts</h2>
      {files.length === 0 && <p>No artifacts found.</p>}
      <table style={{ width: '100%', marginTop: '1rem', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left' }}>
            <th>Filename</th>
            <th>Tool</th>
            <th>Task ID</th>
            <th>Size (KB)</th>
            <th>Timestamp</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, idx) => (
            <tr key={idx}>
              <td>{file.filename}</td>
              <td>{file.tool}</td>
              <td>{file.task_id}</td>
              <td>{file.size_kb}</td>
              <td>{file.timestamp}</td>
              <td>
                <a
                  href={`/artifacts/${file.filename}`}
                  download
                  style={{ color: 'var(--link-fg)' }}
                >
                  ⬇️
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
