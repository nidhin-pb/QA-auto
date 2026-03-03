import React, { useEffect, useState } from 'react';

function ExcelSuiteConfig({ apiBase, isRunning, isInitialized, onRunSuite }) {
  const [suite, setSuite] = useState({ suite_name: '', count: 0, errors: [], preview: [] });
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const res = await fetch(`${apiBase}/api/excel-suite`);
    const data = await res.json();
    setSuite(data);
  };

  useEffect(() => { refresh(); }, []);

  const onPick = async (e) => {
    const f = (e.target.files || [])[0];
    if (!f) return;

    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', f);
      const res = await fetch(`${apiBase}/api/excel-suite/upload`, { method: 'POST', body: fd });
      await res.json();
      await refresh();
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  };

  return (
    <div style={{marginTop:'14px'}}>
      <h3 style={{fontSize:'14px', fontWeight:700, marginBottom:'10px', color:'#667eea'}}>
        Excel / CSV Test Suite
      </h3>

      <input
        type="file"
        disabled={busy || isRunning}
        onChange={onPick}
        style={{width:'100%', marginBottom:'10px'}}
        accept=".xlsx,.csv"
      />

      <div style={{fontSize:'12px', color:'#a0aec0', marginBottom:'6px'}}>
        Loaded: {suite.count || 0} testcases {suite.suite_name ? `(${suite.suite_name})` : ''}
      </div>

      {suite.errors && suite.errors.length > 0 && (
        <div style={{background:'#742a2a', color:'#fed7d7', padding:'8px', borderRadius:'6px', fontSize:'12px', marginBottom:'10px'}}>
          {suite.errors.map((er, i) => <div key={i}>• {er}</div>)}
        </div>
      )}

      <button
        className="btn btn-primary"
        disabled={!isInitialized || isRunning || busy || !(suite.count > 0)}
        onClick={onRunSuite}
        style={{width:'100%'}}
      >
        Run Excel Suite
      </button>
    </div>
  );
}

export default ExcelSuiteConfig;
