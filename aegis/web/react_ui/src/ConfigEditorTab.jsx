// aegis/web/react_ui/src/ConfigEditorTab.jsx
import React from 'react';

export default function ConfigEditorTab({
  files,
  currentFile,
  content,
  setContent,
  status,
  loadConfigFileContent,
  saveConfigFileContent
}) {

  return (
    <div>
      <h2>⚙️ Config Editor</h2>
       <p style={{ opacity: 0.8, marginTop: '-0.5rem', marginBottom: '1.5rem' }}>
        Live-edit the core YAML configuration files for AEGIS. Changes are saved directly to the host filesystem.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '2rem' }}>
        <div>
          <h4>Editable Files</h4>
          <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            {files.map((file) => (
              <div key={file} style={{ marginBottom: '0.25rem' }}>
                <button
                    onClick={() => loadConfigFileContent(file)}
                    style={{
                        width: '100%',
                        textAlign: 'left',
                        fontWeight: currentFile === file ? 'bold' : 'normal',
                        color: currentFile === file ? 'var(--accent)' : 'var(--fg)'
                    }}>
                  {file}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <h4>{currentFile ? `Editing: ${currentFile}` : "Select a file to edit"}</h4>
                <span style={{opacity: 0.7, fontSize: '0.9em'}}>{status}</span>
            </div>
            <textarea
                value={content}
                onChange={e => setContent(e.target.value)}
                placeholder="Select a file from the left to view its content..."
                rows="25"
                disabled={!currentFile}
                style={{
                    width: '100%',
                    fontFamily: 'monospace',
                    fontSize: '0.9em',
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--input-bg)'
                }}
            />
            <button onClick={saveConfigFileContent} disabled={!currentFile} style={{ marginTop: '1rem' }}>
                💾 Save Changes
            </button>
        </div>
      </div>
    </div>
  );
}