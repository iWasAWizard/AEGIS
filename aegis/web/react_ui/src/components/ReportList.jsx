import React, { useEffect, useState } from 'react';

export default function ReportList() {
  const [reports, setReports] = useState([]);

  useEffect(() => {
    fetch('/tasks')
      .then((res) => res.json())
      .then((data) => {
        setReports(data.tasks || []);
      })
      .catch((err) => {
        console.error("Failed to load reports:", err);
        setReports([]);
      });
  }, []);

  const colorForResult = (result) => {
    if (!result || result === 'fail') return 'text-red-600';
    if (result === 'warn' || result === 'weird' || result === 'unknown') return 'text-yellow-500';
    return 'text-green-600';
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">📁 Recent Reports</h2>
      <ul className="text-sm list-disc list-inside space-y-1">
        {reports.length === 0 ? (
          <li>No tasks found.</li>
        ) : (
          reports.map((report) => (
            <li key={report.task_id} className={colorForResult(report.result)}>
              <a href={`/report/${report.task_id}`} className="underline">
                {report.task_id}
              </a>
              {' — '}
              <span className="text-gray-600">{new Date(report.timestamp).toLocaleString()}</span>
              {' — '}
              <span className="font-bold">{report.result}</span>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
