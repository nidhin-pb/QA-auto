import React from 'react';

function TestDashboard({ results, progress }) {
  const passed = results.filter(r => r.status === 'passed').length;
  const failed = results.filter(r => r.status === 'failed').length;
  const errors = results.filter(r => r.status === 'error').length;
  const total = results.length;

  return (
    <div>
      <div className="results-grid">
        <div className="result-card total">
          <div className="count">{total}</div>
          <div className="label">Total</div>
        </div>
        <div className="result-card passed">
          <div className="count">{passed}</div>
          <div className="label">Passed</div>
        </div>
        <div className="result-card failed">
          <div className="count">{failed}</div>
          <div className="label">Failed</div>
        </div>
        <div className="result-card errors">
          <div className="count">{errors}</div>
          <div className="label">Errors</div>
        </div>
      </div>

      <div style={{fontSize:'12px', fontWeight:600, marginBottom:'8px', color:'#a0aec0'}}>
        TEST RESULTS
      </div>
      {results.map((r, i) => (
        <div key={i} className="scenario-item" style={{cursor:'default'}}>
          <div style={{display:'flex', justifyContent:'space-between'}}>
            <span className="scenario-id">{r.test_id}</span>
            <span className={`scenario-status ${r.status}`}>{r.status}</span>
          </div>
          <div className="scenario-name">{r.test_name}</div>
          <div className="scenario-category">{r.category}</div>
          {r.details && <div style={{fontSize:'10px', color:'#718096', marginTop:'4px'}}>{r.details.substring(0, 100)}</div>}
          {r.error && <div style={{fontSize:'10px', color:'#fc8181', marginTop:'4px'}}>{r.error.substring(0, 100)}</div>}
        </div>
      ))}

      {results.length === 0 && (
        <div style={{textAlign:'center', color:'#4a5568', padding:'20px', fontSize:'12px'}}>
          No results yet. Run tests to see results here.
        </div>
      )}
    </div>
  );
}

export default TestDashboard;
