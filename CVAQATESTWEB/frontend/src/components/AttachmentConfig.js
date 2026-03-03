import React, { useEffect, useState } from 'react';

function AttachmentConfig({ apiBase, isRunning }) {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const res = await fetch(`${apiBase}/api/attachments`);
    const data = await res.json();
    setFiles(data.files || []);
  };

  useEffect(() => { refresh(); }, []);

  const onPick = async (e) => {
    const picked = Array.from(e.target.files || []).slice(0, 2);
    if (picked.length === 0) return;

    setBusy(true);
    try {
      const fd = new FormData();
      picked.forEach(f => fd.append('files', f));
      const res = await fetch(`${apiBase}/api/attachments/upload`, { method: 'POST', body: fd });
      const data = await res.json();
      setFiles(data.files || []);
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  };

  const clear = async () => {
    setBusy(true);
    try {
      await fetch(`${apiBase}/api/attachments/clear`, { method: 'POST' });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{marginTop:'14px'}}>
      <h3 style={{fontSize:'14px', fontWeight:700, marginBottom:'10px', color:'#667eea'}}>
        Attachments (for ATT-001/ATT-002)
      </h3>

      <input
        type="file"
        multiple
        disabled={busy || isRunning}
        onChange={onPick}
        style={{width:'100%', marginBottom:'10px'}}
        accept=".png,.jpg,.jpeg,.pdf,.doc,.docx,.txt"
      />

      <div style={{fontSize:'12px', color:'#a0aec0', marginBottom:'6px'}}>
        Staged files: {files.length}/2
      </div>

      {files.map((f, i) => (
        <div key={i} style={{fontSize:'12px', background:'#2d3748', padding:'6px 8px', borderRadius:'6px', marginBottom:'6px'}}>
          {f.name}
        </div>
      ))}

      <button
        className="btn btn-sm"
        style={{width:'100%', background:'#4a5568', color:'#e2e8f0'}}
        onClick={clear}
        disabled={busy || isRunning}
      >
        Clear Attachments
      </button>
    </div>
  );
}

export default AttachmentConfig;
