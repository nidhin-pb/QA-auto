import React from 'react';

function TestDashboard({ results, progress }) {
  const passed = results.filter(r => r.status === 'passed').length;
  const failed = results.filter(r => r.status === 'failed').length;
  const errors = results.filter(r => r.status === 'error').length;
  const skipped = results.filter(r => r.status === 'skipped').length;
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

      <div style={{ fontSize: '12px', color: '#a0aec0', marginBottom: '10px' }}>
        Skipped / Blocked: {skipped}
      </div>

      <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '8px', color: '#a0aec0' }}>
        TEST RESULTS
      </div>

      {results.map((r, i) => (
        <div key={i} className="scenario-item" style={{ cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span className="scenario-id">{r.test_id}</span>
            <span className={`scenario-status ${r.status}`}>{r.status}</span>
          </div>

          <div className="scenario-name">{r.test_name}</div>
          <div className="scenario-category">{r.category}</div>

          {r.execution_mode && (
            <div style={{ fontSize: '10px', color: '#63b3ed', marginTop: '4px' }}>
              Mode: {r.execution_mode} | Auto: {r.automation_level || 'n/a'}
            </div>
          )}

          {r.structured_family && (
            <div style={{ fontSize: '10px', color: '#68d391', marginTop: '2px' }}>
              Family: {r.structured_family}
            </div>
          )}

          {r.display_status && (
            <div style={{ fontSize: '10px', color: '#f6e05e', marginTop: '2px' }}>
              QA Status: {r.display_status}
            </div>
          )}

          {typeof r.qa_score !== 'undefined' && (
            <div style={{ fontSize: '10px', color: '#90cdf4', marginTop: '2px' }}>
              QA Score: {r.qa_score} / 100 ({r.qa_grade || 'N/A'})
            </div>
          )}

          {r.failure_type && (
            <div style={{ fontSize: '10px', color: '#fc8181', marginTop: '2px' }}>
              Failure Type: {r.failure_type}
            </div>
          )}

          {r.alternate_outcome && (
            <div style={{ fontSize: '10px', color: '#f6ad55', marginTop: '2px' }}>
              Alternate outcome: {r.alternate_reason || 'Yes'}
            </div>
          )}

          {r.goal_achieved_reason && (
            <div style={{ fontSize: '10px', color: '#90cdf4', marginTop: '2px' }}>
              Goal: {r.goal_achieved_reason}
            </div>
          )}

          {r.details && (
            <div style={{ fontSize: '10px', color: '#718096', marginTop: '4px' }}>
              {r.details.substring(0, 180)}
            </div>
          )}

          {r.error && (
            <div style={{ fontSize: '10px', color: '#fc8181', marginTop: '4px' }}>
              {r.error.substring(0, 180)}
            </div>
          )}
        </div>
      ))}

      {results.length === 0 && (
        <div style={{ textAlign: 'center', color: '#4a5568', padding: '20px', fontSize: '12px' }}>
          No results yet. Run tests to see results here.
        </div>
      )}
    </div>
  );
}

export default TestDashboard;
