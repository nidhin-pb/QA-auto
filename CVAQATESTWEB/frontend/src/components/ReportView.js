import React from 'react';

function ReportView({ reports, apiBase, onRefresh }) {
  return (
    <div>
      {reports.map((report, i) => (
        <div key={i} className="report-item">
          <span className="report-name">
            <i className="fas fa-file-excel" style={{color:'#68d391', marginRight:'6px'}}></i>
            {report}
          </span>
          <a
            href={`${apiBase}/api/reports/${report}`}
            download
            className="btn btn-sm btn-success"
            style={{textDecoration:'none'}}
          >
            <i className="fas fa-download"></i>
          </a>
        </div>
      ))}
      {reports.length === 0 && (
        <div style={{fontSize:'11px', color:'#4a5568', textAlign:'center', padding:'8px'}}>
          No reports yet
        </div>
      )}
      <button
        className="btn btn-sm"
        style={{width:'100%', marginTop:'8px', background:'#2d3748', color:'#a0aec0'}}
        onClick={onRefresh}
      >
        <i className="fas fa-sync-alt"></i> Refresh
      </button>
    </div>
  );
}

export default ReportView;
