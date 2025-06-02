import React, { useState } from 'react';

export default function PromptForm() {
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState('plan');
  const [iterations, setIterations] = useState(5);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, mode, iterations: parseInt(iterations, 10) }),
      });

      if (response.ok) {
        setMessage('✅ Task launched successfully.');
        setPrompt('');
      } else {
        const err = await response.text();
        setMessage(`❌ Failed to launch task: ${err}`);
      }
    } catch (error) {
      setMessage(`❌ Error: ${error.message}`);
    }

    setLoading(false);
  };

  return (
    <div className="mb-6">
      <h2 className="text-xl font-semibold mb-2">📝 Prompt Agent</h2>
      <form onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="What should the agent do?"
          className="w-full p-2 rounded border border-gray-300 mb-3"
          rows={4}
        />
        <div className="flex items-center gap-4 mb-3">
          <label>Mode:</label>
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="plan">Standard</option>
            <option value="fuzz">Fuzz</option>
          </select>
          <label>Iterations:</label>
          <input
            type="number"
            min="0"
            max="50"
            value={iterations}
            onChange={(e) => setIterations(e.target.value)}
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded"
          disabled={loading}
        >
          {loading ? 'Launching...' : '🚀 Launch Task'}
        </button>
        {message && <p className="mt-2 text-sm">{message}</p>}
      </form>
    </div>
  );
}
