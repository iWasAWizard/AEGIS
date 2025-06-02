import React from 'react';

const themes = [
  { label: 'OLED (Default)', value: 'oled' },
  { label: 'Dracula', value: 'dracula' },
  { label: 'Solarized Dark', value: 'solarized-dark' },
  { label: 'Solarized Light', value: 'solarized-light' },
  { label: 'Light', value: 'light' },
];

export default function ThemeSelector({ theme, setTheme }) {
  return (
    <select
      className="bg-gray-800 text-white p-1 rounded"
      value={theme}
      onChange={(e) => setTheme(e.target.value)}
    >
      {themes.map((t) => (
        <option key={t.value} value={t.value}>{t.label}</option>
      ))}
    </select>
  );
}
