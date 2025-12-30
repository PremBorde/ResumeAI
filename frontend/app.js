/**
 * ResumeAI — Frontend Application
 * Connects to FastAPI backend for resume matching & skill gap analysis
 */

const API_BASE = 'http://127.0.0.1:8000';

// Custom Alert System
function showCustomAlert(message, type = 'info') {
  // Remove existing alerts
  const existing = document.querySelector('.custom-alert');
  if (existing) existing.remove();

  const alert = document.createElement('div');
  alert.className = `custom-alert custom-alert-${type}`;
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  const bgColor = type === 'success' ? 'rgba(0, 229, 204, 0.15)' : 
                   type === 'error' ? 'rgba(255, 77, 77, 0.15)' : 
                   'rgba(0, 229, 204, 0.1)';
  const borderColor = type === 'success' ? 'rgba(0, 229, 204, 0.5)' : 
                      type === 'error' ? 'rgba(255, 77, 77, 0.5)' : 
                      'rgba(0, 229, 204, 0.3)';
  const iconColor = type === 'success' ? '#00e5cc' : 
                    type === 'error' ? '#ff4d4d' : 
                    '#00e5cc';

  alert.innerHTML = `
    <div style="display: flex; align-items: center; gap: var(--space-md);">
      <div style="width: 32px; height: 32px; border-radius: 50%; background: ${bgColor}; border: 2px solid ${borderColor}; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: ${iconColor}; flex-shrink: 0;">
        ${icon}
      </div>
      <div style="flex: 1; color: var(--text-primary); font-size: 0.95rem; line-height: 1.5;">
        ${escapeHtml(message)}
      </div>
      <button class="alert-close" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 1.2rem; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; transition: color 0.2s;" onclick="this.closest('.custom-alert').remove()">
        ×
      </button>
    </div>
  `;

  alert.style.cssText = `
    position: fixed;
    top: 100px;
    right: var(--space-lg);
    z-index: 10000;
    background: var(--bg-card);
    border: 2px solid ${borderColor};
    border-radius: var(--radius-lg);
    padding: var(--space-md) var(--space-lg);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    max-width: 400px;
    animation: slideInRight 0.3s ease-out;
    backdrop-filter: blur(10px);
  `;

  document.body.appendChild(alert);

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (alert.parentNode) {
      alert.style.animation = 'slideOutRight 0.3s ease-out';
      setTimeout(() => alert.remove(), 300);
    }
  }, 5000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
  .alert-close:hover {
    color: var(--text-primary) !important;
  }
`;
document.head.appendChild(style);

// State
let currentResumeId = localStorage.getItem('currentResumeId') || null;
let currentAnalysisId = localStorage.getItem('currentAnalysisId') || null;
let resumeSkills = [];
let resumeSkillsDetailed = [];  // Enhanced skills with confidence
let currentPageId = 'page-analyze';
let lastAnalysisPayload = null;
let resumeRawText = '';  // Store resume raw text to extract name and email
let extractedResumeData = { name: '', email: '', company: '' };  // Store extracted data

// Helper to persist state
function persistState() {
  if (currentResumeId) {
    localStorage.setItem('currentResumeId', currentResumeId);
  } else {
    localStorage.removeItem('currentResumeId');
  }
  if (currentAnalysisId) {
    localStorage.setItem('currentAnalysisId', currentAnalysisId);
  } else {
    localStorage.removeItem('currentAnalysisId');
  }
}

// DOM Elements
const elements = {
  // Navigation
  navHome: document.getElementById('nav-home'),
  navLinks: Array.from(document.querySelectorAll('.nav-link[data-page]')),
  pages: Array.from(document.querySelectorAll('.page')),

  // Steps
  stepUpload: document.getElementById('step-upload'),
  stepJd: document.getElementById('step-jd'),
  stepResults: document.getElementById('step-results'),
  
  // Upload
  uploadZone: document.getElementById('upload-zone'),
  fileInput: document.getElementById('file-input'),
  filePreview: document.getElementById('file-preview'),
  fileName: document.getElementById('file-name'),
  fileSize: document.getElementById('file-size'),
  btnRemove: document.getElementById('btn-remove'),
  btnUpload: document.getElementById('btn-upload'),
  
  // JD
  resumeSummary: document.getElementById('resume-summary'),
  summarySkills: document.getElementById('summary-skills'),
  jdInput: document.getElementById('jd-input'),
  btnBackUpload: document.getElementById('btn-back-upload'),
  btnAnalyze: document.getElementById('btn-analyze'),
  
  // Results
  scoreRing: document.getElementById('score-ring'),
  scoreNumber: document.getElementById('score-number'),
  semanticBar: document.getElementById('semantic-bar'),
  semanticValue: document.getElementById('semantic-value'),
  skillsBar: document.getElementById('skills-bar'),
  skillsValue: document.getElementById('skills-value'),
  matchingCount: document.getElementById('matching-count'),
  matchingSkills: document.getElementById('matching-skills'),
  missingCount: document.getElementById('missing-count'),
  missingSkills: document.getElementById('missing-skills'),
  niceCount: document.getElementById('nice-count'),
  niceSkills: document.getElementById('nice-skills'),
  suggestionsContent: document.getElementById('suggestions-content'),
  atsContent: document.getElementById('ats-content'),
  jobInsightsContent: document.getElementById('job-insights-content'),
  btnCopyChatgptPrompt: document.getElementById('btn-copy-chatgpt-prompt'),
  btnCopyChatgptOverleaf: document.getElementById('btn-copy-chatgpt-overleaf'),
  btnNew: document.getElementById('btn-new'),
  btnDownload: document.getElementById('btn-download'),

  // Compare
  compareContainer: document.getElementById('compare-jds'),
  compareResults: document.getElementById('compare-results'),
  btnAddJd: document.getElementById('btn-add-jd'),
  btnRunCompare: document.getElementById('btn-run-compare'),
  compareResumeWarning: document.getElementById('compare-resume-warning'),

  // Export
  exportWarning: document.getElementById('export-warning'),
  btnExportJson: document.getElementById('btn-export-json'),
  btnExportPdf: document.getElementById('btn-export-pdf'),
  btnExportDocxBullets: document.getElementById('btn-export-docx-bullets'),
  
  // Cover Letter
  coverLetterName: document.getElementById('cover-letter-name'),
  coverLetterEmail: document.getElementById('cover-letter-email'),
  coverLetterCompany: document.getElementById('cover-letter-company'),
  btnGenerateCoverLetter: document.getElementById('btn-generate-cover-letter'),
  coverLetterGeneratorForm: document.getElementById('cover-letter-generator-form'),
  coverLetterGeneratedView: document.getElementById('cover-letter-generated-view'),
  coverLetterText: document.getElementById('cover-letter-text'),
  linkedinMessageText: document.getElementById('linkedin-message-text'),
  coldmailText: document.getElementById('coldmail-text'),
  btnCopyCoverLetter: document.getElementById('btn-copy-cover-letter'),
  btnDownloadCoverLetter: document.getElementById('btn-download-cover-letter'),
  btnCopyLinkedin: document.getElementById('btn-copy-linkedin'),
  btnDownloadLinkedin: document.getElementById('btn-download-linkedin'),
  btnCopyColdmail: document.getElementById('btn-copy-coldmail'),
  btnDownloadColdmail: document.getElementById('btn-download-coldmail'),
  btnOptionCoverLetter: document.getElementById('btn-option-cover-letter'),
  btnOptionLinkedin: document.getElementById('btn-option-linkedin'),
  btnOptionColdmail: document.getElementById('btn-option-coldmail'),
};

// ========================================
// Navigation
// ========================================

function setActiveNav(pageId) {
  elements.navLinks.forEach(link => {
    const isActive = link.dataset.page === pageId;
    link.classList.toggle('active', isActive);
    link.setAttribute('aria-current', isActive ? 'page' : 'false');
  });
}

function showPage(pageId) {
  elements.pages.forEach(p => p.classList.add('hidden'));
  const page = document.getElementById(pageId);
  if (page) page.classList.remove('hidden');
  currentPageId = pageId;
  setActiveNav(pageId);

  // Apply wider layout for Analyze, Compare, and Export pages
  const mainEl = document.querySelector('.main');
  if (mainEl) {
    if (pageId === 'page-analyze' || pageId === 'page-compare' || pageId === 'page-export') {
      mainEl.classList.add('main-compare');
    } else {
      mainEl.classList.remove('main-compare');
    }
  }

  if (pageId === 'page-compare') {
    renderCompare();
  }
  if (pageId === 'page-export') {
    renderExport();
  }
}

function showStep(stepId) {
  // Steps only exist inside Analyze page
  showPage('page-analyze');
  document.querySelectorAll('.step').forEach(step => step.classList.add('hidden'));
  document.getElementById(stepId).classList.remove('hidden');
}

// Nav bindings
if (elements.navHome) {
  elements.navHome.addEventListener('click', (e) => {
    e.preventDefault();
    // If user is mid-flow, keep them where they were; otherwise send to upload.
    if (currentAnalysisId) return showStep('step-results');
    if (currentResumeId) return showStep('step-jd');
    return showStep('step-upload');
  });
}

elements.navLinks.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const pageId = link.dataset.page;
    if (!pageId) return;
    if (pageId === 'page-analyze') {
      // Restore best step based on state
      if (currentAnalysisId) return showStep('step-results');
      if (currentResumeId) return showStep('step-jd');
      return showStep('step-upload');
    }
    showPage(pageId);
  });
});

// ========================================
// Compare (multiple JDs)
// ========================================

let compareJds = [];

function renderCompare() {
  if (!elements.compareContainer || !elements.compareResults) return;

  const hasResume = Boolean(currentResumeId);
  if (elements.compareResumeWarning) {
    elements.compareResumeWarning.style.display = hasResume ? 'none' : 'block';
  }
  // Don't disable button - let click handler show alerts instead
  // This allows users to get feedback when they click without resume

  elements.compareContainer.innerHTML = '';
  compareJds.forEach((jd, idx) => {
    const wrap = document.createElement('div');
    wrap.className = 'result-card';
    wrap.style.padding = '1rem';

    wrap.innerHTML = `
      <div style="display:flex; gap: var(--space-md); flex-wrap: wrap; align-items:center; justify-content: space-between;">
        <div style="display:flex; gap: var(--space-sm); align-items:center; flex: 1; min-width: 220px;">
          <input data-idx="${idx}" data-field="title" class="jd-textarea" style="height: 42px; padding: 0.6rem 0.85rem; resize: none;" value="${escapeHtml(jd.title || '')}" />
        </div>
        <button class="btn-secondary" type="button" data-action="remove" data-idx="${idx}">Remove</button>
      </div>
      <div style="margin-top: var(--space-md);">
        <textarea data-idx="${idx}" data-field="text" class="jd-textarea" placeholder="Paste job description..." rows="15" style="min-height: 400px;">${escapeHtml(jd.text || '')}</textarea>
      </div>
    `;

    wrap.querySelectorAll('input[data-field], textarea[data-field]').forEach(el => {
      el.addEventListener('input', (e) => {
        const i = Number(e.target.dataset.idx);
        const field = e.target.dataset.field;
        compareJds[i][field] = e.target.value;
      });
    });

    wrap.querySelector('[data-action="remove"]')?.addEventListener('click', (e) => {
      const i = Number(e.target.dataset.idx);
      compareJds.splice(i, 1);
      renderCompare();
    });

    elements.compareContainer.appendChild(wrap);
  });
}

async function runCompare() {
  if (!currentResumeId) {
    showCustomAlert('Please upload a resume first.', 'error');
    return;
  }
  if (!elements.compareResults) return;

  const payload = {
    resume_id: currentResumeId,
    job_descriptions: compareJds
      .map(jd => ({ title: (jd.title || '').trim(), text: (jd.text || '').trim() }))
      .filter(jd => jd.text.length >= 50),
  };

  if (payload.job_descriptions.length < 2) {
    showCustomAlert('Please add at least 2 job descriptions (50+ characters each).', 'error');
    return;
  }

  elements.compareResults.innerHTML = `<p style="color: var(--text-secondary); font-style: italic;">Comparing...</p>`;

  try {
    const res = await fetch(`${API_BASE}/compare-jds`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Compare failed');

    // Create comparison cards with actionable features
    const cardsHtml = (data.results || []).map((r, rank) => {
      const fs = Math.round(r.score.final_match_score);
      const sem = Math.round(r.score.semantic_similarity_score);
      const skl = Math.round(r.score.skill_overlap_score);
      const missing = (r.skill_gap?.missing_required_skills || []);
      const matching = (r.skill_gap?.matching_skills || []);
      const niceToHave = (r.skill_gap?.nice_to_have_skills || []);
      
      // Get JD text for preview
      const jdItem = compareJds[r.job_index];
      const jdPreview = jdItem ? (jdItem.text || '').substring(0, 200).trim() : '';
      
      // Display limits for initial view
      const matchingDisplay = matching.slice(0, 12);
      const missingDisplay = missing.slice(0, 12);
      const niceToHaveDisplay = niceToHave.slice(0, 10);
      const hasMoreMatching = matching.length > 12;
      const hasMoreMissing = missing.length > 12;
      const hasMoreNice = niceToHave.length > 10;
      
      const scoreColor = fs >= 80 ? 'var(--accent)' : fs >= 60 ? 'var(--text-primary)' : 'var(--text-secondary)';
      const badgeColor = rank === 0 ? 'var(--accent)' : rank === 1 ? 'var(--text-primary)' : 'var(--text-secondary)';
      
      // Calculate skill coverage percentage
      const totalRequired = matching.length + missing.length;
      const skillCoverage = totalRequired > 0 ? Math.round((matching.length / totalRequired) * 100) : 0;
      
      return `
        <div class="result-card" style="margin-bottom: var(--space-lg);">
          <div style="display: flex; align-items: start; gap: var(--space-md); justify-content: space-between; margin-bottom: var(--space-md);">
            <div style="flex: 1;">
              <div style="display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-xs);">
                <span style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: ${badgeColor}20; color: ${badgeColor}; font-weight: 700; font-size: 0.9rem;">#${rank + 1}</span>
                <h3 style="margin: 0; font-size: 1.1rem; font-weight: 600;">${escapeHtml(r.title || `Job ${rank + 1}`)}</h3>
              </div>
              <div style="display: flex; gap: var(--space-md); align-items: center; margin-top: var(--space-sm); flex-wrap: wrap;">
                <div style="display: flex; align-items: baseline; gap: var(--space-xs);">
                  <span style="font-size: 2rem; font-weight: 700; color: ${scoreColor}; line-height: 1;">${fs}</span>
                  <span style="font-size: 1rem; color: var(--text-secondary);">%</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">
                  Semantic: ${sem}% · Skills: ${skl}% · Coverage: ${skillCoverage}%
                </div>
              </div>
              ${jdPreview ? `
                <div style="margin-top: var(--space-sm); padding: var(--space-sm); background: var(--bg-secondary); border-radius: var(--radius-sm);">
                  <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.5px;">Job Preview</div>
                  <div style="font-size: 0.85rem; color: var(--text-primary); line-height: 1.5;">${escapeHtml(jdPreview)}${jdItem.text.length > 200 ? '...' : ''}</div>
                </div>
              ` : ''}
            </div>
            <div style="display: flex; gap: var(--space-sm); flex-wrap: wrap; align-items: start;">
              <button class="btn-secondary" onclick="analyzeThisJD(${r.job_index})" style="padding: 0.5rem 1rem; font-size: 0.875rem;">
                📊 Full Analysis
              </button>
              <button class="btn-secondary" onclick="copyComparePrompt(${r.job_index})" style="padding: 0.5rem 1rem; font-size: 0.875rem;">
                📋 ChatGPT Prompt
              </button>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-top: var(--space-md);">
            <div>
              <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--space-xs); display: flex; align-items: center; gap: var(--space-xs);">
                ✓ Matching Skills (${matching.length}${hasMoreMatching ? '+' : ''})
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
                ${matchingDisplay.length > 0 ? matchingDisplay.map(s => `<span style="padding: 0.25rem 0.5rem; background: var(--accent-dim); color: var(--accent); border-radius: var(--radius-sm); font-size: 0.75rem;">${escapeHtml(s)}</span>`).join('') : '<span style="color: var(--text-muted); font-size: 0.8rem;">None</span>'}
                ${hasMoreMatching ? `<span style="padding: 0.25rem 0.5rem; color: var(--text-muted); font-size: 0.75rem; font-style: italic;">+${matching.length - 12} more</span>` : ''}
              </div>
            </div>
            <div>
              <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--space-xs); display: flex; align-items: center; gap: var(--space-xs);">
                ! Missing Required (${missing.length}${hasMoreMissing ? '+' : ''})
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
                ${missingDisplay.length > 0 ? missingDisplay.map(s => `<span style="padding: 0.25rem 0.5rem; background: rgba(255, 77, 77, 0.15); color: #ff4d4d; border-radius: var(--radius-sm); font-size: 0.75rem;">${escapeHtml(s)}</span>`).join('') : '<span style="color: var(--text-muted); font-size: 0.8rem;">None</span>'}
                ${hasMoreMissing ? `<span style="padding: 0.25rem 0.5rem; color: var(--text-muted); font-size: 0.75rem; font-style: italic;">+${missing.length - 12} more</span>` : ''}
              </div>
            </div>
          </div>
          
          ${niceToHave.length > 0 ? `
            <div style="margin-top: var(--space-md);">
              <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--space-xs);">
                ★ Nice to Have (${niceToHave.length}${hasMoreNice ? '+' : ''})
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
                ${niceToHaveDisplay.map(s => `<span style="padding: 0.25rem 0.5rem; background: rgba(0, 229, 204, 0.1); color: var(--accent); border-radius: var(--radius-sm); font-size: 0.75rem;">${escapeHtml(s)}</span>`).join('')}
                ${hasMoreNice ? `<span style="padding: 0.25rem 0.5rem; color: var(--text-muted); font-size: 0.75rem; font-style: italic;">+${niceToHave.length - 10} more</span>` : ''}
              </div>
            </div>
          ` : ''}
          
          <div style="margin-top: var(--space-md); padding-top: var(--space-md); border-top: 1px solid var(--border); display: flex; gap: var(--space-md); font-size: 0.8rem; color: var(--text-secondary);">
            <div>📊 Score Breakdown: <strong style="color: var(--text-primary);">${sem}%</strong> semantic · <strong style="color: var(--text-primary);">${skl}%</strong> skills</div>
            <div>🎯 Skill Match: <strong style="color: var(--text-primary);">${matching.length}/${totalRequired}</strong> required skills</div>
          </div>
        </div>
      `;
    }).join('');

    elements.compareResults.innerHTML = `
      <div style="margin-top: var(--space-xl);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-lg);">
          <h3 style="margin: 0; font-size: 1.25rem; font-weight: 400;">Ranked Results</h3>
          <button class="btn-secondary" onclick="exportComparison()" style="padding: 0.5rem 1rem; font-size: 0.875rem;">
            📥 Export Comparison
          </button>
        </div>
        ${cardsHtml}
      </div>
    `;
    
    // Store comparison data for actions
    window.lastComparisonData = data;
    window.lastCompareJds = compareJds; // Store original JDs for full analysis
  } catch (e) {
    elements.compareResults.innerHTML = `<p style="color: var(--secondary);">Error: ${escapeHtml(e?.message || String(e))}</p>`;
  }
}

// Full Analysis for a specific JD from comparison (exposed globally for onclick)
window.analyzeThisJD = async function analyzeThisJD(jobIndex) {
  if (!currentResumeId || !window.lastCompareJds || !window.lastCompareJds[jobIndex]) {
    showCustomAlert('Unable to find job description. Please run comparison again.', 'error');
    return;
  }

  const jd = window.lastCompareJds[jobIndex];
  const jdText = (jd.text || '').trim();
  
  if (jdText.length < 50) {
    showCustomAlert('Job description is too short for analysis.', 'error');
    return;
  }

  // Switch to analyze page and set JD text
  showPage('page-analyze');
  showStep('step-jd');
  elements.jdInput.value = jdText;
  elements.btnAnalyze.disabled = false;

  // Auto-trigger analysis after a small delay to ensure UI is ready
  setTimeout(() => {
    showCustomAlert('Running full analysis...', 'info');
    elements.btnAnalyze.click();
  }, 100);
}

// Copy ChatGPT prompt for a specific JD from comparison (exposed globally for onclick)
window.copyComparePrompt = function copyComparePrompt(jobIndex) {
  if (!window.lastComparisonData || !window.lastCompareJds || !window.lastCompareJds[jobIndex]) {
    showCustomAlert('Unable to find job description. Please run comparison again.', 'error');
    return;
  }

  const result = window.lastComparisonData.results.find(r => r.job_index === jobIndex);
  if (!result) {
    showCustomAlert('Unable to find comparison result.', 'error');
    return;
  }

  // Build a simplified payload for the prompt
  const payload = {
    score: result.score,
    skill_gap: result.skill_gap,
    ats: { missing_required: result.skill_gap?.missing_required_skills || [] },
    debug: {
      jd_required_skills: result.skill_gap?.missing_required_skills || [],
      jd_preferred_skills: result.skill_gap?.nice_to_have_skills || [],
    }
  };

  const prompt = buildChatGptPrompt(payload, false);
  navigator.clipboard.writeText(prompt).then(() => {
    showCustomAlert('ChatGPT prompt copied to clipboard!', 'success');
  }).catch(() => {
    showCustomAlert('Failed to copy prompt. Please try again.', 'error');
  });
}

// Export comparison results as JSON (exposed globally for onclick)
window.exportComparison = function exportComparison() {
  if (!window.lastComparisonData) {
    showCustomAlert('No comparison data available. Please run comparison first.', 'error');
    return;
  }

  const exportData = {
    generated_at: new Date().toISOString(),
    resume_id: window.lastComparisonData.resume_id,
    results: window.lastComparisonData.results.map((r, idx) => ({
      rank: idx + 1,
      title: r.title,
      job_index: r.job_index,
      score: r.score,
      skill_gap: r.skill_gap,
    })),
  };

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `job-comparison-${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  showCustomAlert('Comparison exported successfully!', 'success');
}

if (elements.btnAddJd) {
  elements.btnAddJd.addEventListener('click', () => {
    const next = compareJds.length + 1;
    compareJds.push({ title: `JD ${next}`, text: '' });
    renderCompare();
  });
}
if (elements.btnRunCompare) {
  elements.btnRunCompare.addEventListener('click', runCompare);
}

// ========================================
// Upload Step
// ========================================

// Drag and drop
elements.uploadZone.addEventListener('click', () => elements.fileInput.click());

elements.uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  elements.uploadZone.classList.add('dragover');
});

elements.uploadZone.addEventListener('dragleave', () => {
  elements.uploadZone.classList.remove('dragover');
});

elements.uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  elements.uploadZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelect(file);
});

elements.fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) handleFileSelect(file);
});

function handleFileSelect(file) {
  const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
  const validExts = ['.pdf', '.docx'];
  
  const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
  if (!validExts.includes(ext)) {
    showCustomAlert('Please upload a PDF or DOCX file.', 'error');
    return;
  }
  
  elements.uploadZone.classList.add('hidden');
  elements.filePreview.classList.remove('hidden');
  elements.fileName.textContent = file.name;
  elements.fileSize.textContent = formatFileSize(file.size);
  elements.btnUpload.disabled = false;
  
  // Store file for upload
  elements.fileInput._selectedFile = file;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

elements.btnRemove.addEventListener('click', () => {
  elements.filePreview.classList.add('hidden');
  elements.uploadZone.classList.remove('hidden');
  elements.btnUpload.disabled = true;
  elements.fileInput.value = '';
  elements.fileInput._selectedFile = null;
});

elements.btnUpload.addEventListener('click', async () => {
  const file = elements.fileInput._selectedFile;
  if (!file) return;
  
  elements.btnUpload.classList.add('loading');
  elements.btnUpload.disabled = true;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}/upload-resume`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }
    
    const data = await response.json();
    currentResumeId = data.resume_id;
    persistState();  // Save to localStorage
    resumeSkills = data.extracted.skills || [];
    resumeSkillsDetailed = data.extracted.skills_detailed || [];
    
    // Fetch resume raw text to extract name and email
    try {
      const resumeRes = await fetch(`${API_BASE}/resume/${currentResumeId}`);
      if (resumeRes.ok) {
        const resumeData = await resumeRes.json();
        resumeRawText = resumeData.raw_text || '';
        // Extract name, email, and company from resume text
        extractedResumeData = extractNameAndEmailFromResume(resumeRawText);
      }
    } catch (e) {
      console.warn('Could not fetch resume data:', e);
    }
    
    // Show summary
    elements.summarySkills.innerHTML = resumeSkills
      .slice(0, 15)
      .map(skill => `<span class="summary-skill">${escapeHtml(skill)}</span>`)
      .join('');
    
    if (resumeSkills.length > 15) {
      elements.summarySkills.innerHTML += `<span class="summary-skill">+${resumeSkills.length - 15} more</span>`;
    }
    
    showStep('step-jd');
    
  } catch (error) {
      showCustomAlert('Error uploading resume: ' + error.message, 'error');
  } finally {
    elements.btnUpload.classList.remove('loading');
    elements.btnUpload.disabled = false;
  }
});

// ========================================
// Job Description Step
// ========================================

elements.jdInput.addEventListener('input', () => {
  const length = elements.jdInput.value.length;
  elements.btnAnalyze.disabled = length < 50;
});

elements.btnBackUpload.addEventListener('click', () => {
  showStep('step-upload');
});

elements.btnAnalyze.addEventListener('click', async () => {
  const jdText = elements.jdInput.value.trim();
  if (jdText.length < 50) return;
  
  elements.btnAnalyze.classList.add('loading');
  elements.btnAnalyze.disabled = true;
  
  try {
    const response = await fetch(`${API_BASE}/analyze-match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_id: currentResumeId,
        job_description_text: jdText,
      }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Analysis failed');
    }
    
    const data = await response.json();
    currentAnalysisId = data.analysis_id;
    persistState();  // Save to localStorage
    
    showStep('step-results');
    renderResults(data);
    
  } catch (error) {
      showCustomAlert('Error analyzing match: ' + error.message, 'error');
  } finally {
    elements.btnAnalyze.classList.remove('loading');
    elements.btnAnalyze.disabled = false;
  }
});

// ========================================
// Results Step
// ========================================

function renderResults(data) {
  const { score, skill_gap, suggestions, suggestion_error, ats, evidence } = data;
  lastAnalysisPayload = data;
  
  // Animate score ring
  const finalScore = Math.round(score.final_match_score);
  const circumference = 2 * Math.PI * 54; // r = 54
  const offset = circumference * (1 - finalScore / 100);
  
  // Reset first
  elements.scoreRing.style.strokeDashoffset = circumference;
  elements.scoreNumber.textContent = '0';
  elements.semanticBar.style.width = '0%';
  elements.skillsBar.style.width = '0%';
  
  // Animate after a small delay
  setTimeout(() => {
    elements.scoreRing.style.strokeDashoffset = offset;
    animateNumber(elements.scoreNumber, 0, finalScore, 1500);
    
    const semantic = Math.round(score.semantic_similarity_score);
    const skills = Math.round(score.skill_overlap_score);
    
    elements.semanticBar.style.width = semantic + '%';
    elements.semanticValue.textContent = semantic;
    
    elements.skillsBar.style.width = skills + '%';
    elements.skillsValue.textContent = skills;
  }, 100);
  
  // Skill gap
  renderSkillChips(elements.matchingSkills, skill_gap.matching_skills, elements.matchingCount);
  renderSkillChips(elements.missingSkills, skill_gap.missing_required_skills, elements.missingCount);
  renderSkillChips(elements.niceSkills, skill_gap.nice_to_have_skills, elements.niceCount);
  
  // Suggestions
  renderSuggestions(suggestions, suggestion_error);

  // ATS
  renderAts(ats);

  // Job Insights
  renderJobInsights(data.debug || {});
}

function animateNumber(element, start, end, duration) {
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const value = Math.round(start + (end - start) * eased);
    element.textContent = value;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }
  
  requestAnimationFrame(update);
}

function renderSkillChips(container, skills, countEl) {
  container.innerHTML = '';
  countEl.textContent = skills.length;
  
  if (skills.length === 0) {
    container.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-muted);">None</span>';
    return;
  }
  
  // Build a map of detailed skills for quick lookup
  const detailedMap = new Map();
  resumeSkillsDetailed.forEach(s => {
    detailedMap.set(s.skill.toLowerCase(), s);
  });
  
  skills.forEach((skill, i) => {
    const detailed = detailedMap.get(skill.toLowerCase());
    const chip = document.createElement('div');
    chip.className = 'skill-chip-wrapper';
    chip.style.animationDelay = (i * 50) + 'ms';
    
    if (detailed) {
      // Enhanced chip with confidence and expandable details
      const confidenceColor = detailed.confidence >= 90 ? 'var(--accent)' : 
                            detailed.confidence >= 70 ? 'var(--text-primary)' : 
                            'var(--text-secondary)';
      
      chip.innerHTML = `
        <div class="skill-chip skill-chip-enhanced" style="cursor: pointer;" data-skill="${escapeHtml(skill)}">
          <span class="skill-name">${escapeHtml(skill)}</span>
          <span class="skill-confidence" style="color: ${confidenceColor}; font-size: 0.7rem; margin-left: 0.25rem;">
            ${detailed.confidence.toFixed(0)}%
          </span>
        </div>
        <div class="skill-details" style="display: none; margin-top: var(--space-xs); padding: var(--space-sm); background: var(--bg-tertiary); border-radius: var(--radius-sm); font-size: 0.8rem;">
          <div style="margin-bottom: var(--space-xs); color: var(--text-secondary);">
            <strong>Confidence:</strong> ${detailed.confidence.toFixed(1)}% | 
            <strong>Original:</strong> ${escapeHtml(detailed.original_text)}
          </div>
          ${detailed.source_snippets.length > 0 ? `
            <div style="margin-top: var(--space-xs);">
              <strong style="color: var(--text-secondary);">Found in:</strong>
              <ul style="margin: var(--space-xs) 0 0 var(--space-md); padding: 0; list-style: disc; color: var(--text-secondary);">
                ${detailed.source_snippets.map(snippet => 
                  `<li style="margin-bottom: var(--space-xs);">${escapeHtml(snippet.length > 100 ? snippet.substring(0, 100) + '...' : snippet)}</li>`
                ).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      `;
      
      // Toggle details on click
      const chipEl = chip.querySelector('.skill-chip-enhanced');
      chipEl.addEventListener('click', () => {
        const details = chip.querySelector('.skill-details');
        const isHidden = details.style.display === 'none';
        details.style.display = isHidden ? 'block' : 'none';
        chipEl.style.borderColor = isHidden ? 'var(--accent)' : 'transparent';
      });
    } else {
      // Simple chip without details
      chip.innerHTML = `<span class="skill-chip">${escapeHtml(skill)}</span>`;
    }
    
    container.appendChild(chip);
  });
}

function renderSuggestions(suggestions, error) {
  if (error) {
    elements.suggestionsContent.innerHTML = `
      <div style="padding: 1rem; background: var(--error-bg, #fee); border-left: 3px solid var(--error-color, #c33); border-radius: 4px;">
        <p style="color: var(--error-color, #c33); font-weight: 500; margin: 0 0 0.5rem 0;">
          AI Recommendations Error
        </p>
        <p style="color: var(--text-muted, #666); font-size: 0.9rem; margin: 0;">
          ${escapeHtml(error)}
        </p>
        <p style="color: var(--text-muted, #666); font-size: 0.85rem; margin: 0.5rem 0 0 0; font-style: italic;">
          Tip: Check your Gemini API quota at <a href="https://ai.dev/usage" target="_blank" style="color: var(--primary, #0066cc);">ai.dev/usage</a>
        </p>
      </div>
    `;
    return;
  }
  
  if (!suggestions || Object.keys(suggestions).length === 0) {
    elements.suggestionsContent.innerHTML = `
      <p style="color: var(--text-muted); font-style: italic;">
        No suggestions available. The AI feedback service may be temporarily unavailable.
      </p>
    `;
    return;
  }
  
  let html = '<div class="suggestion-sections">';
  
  // Score explanation
  if (suggestions.score_explanation) {
    html += `<p class="rationale">${escapeHtml(suggestions.score_explanation)}</p>`;
  }
  
  // Key strengths
  if (suggestions.key_strengths && suggestions.key_strengths.length > 0) {
    html += `
      <div class="suggestion-section">
        <h4>Key Strengths</h4>
        <ul class="suggestion-list">
          ${suggestions.key_strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
        </ul>
      </div>
    `;
  }
  
  // Skills to add
  if (suggestions.missing_skills_to_add && suggestions.missing_skills_to_add.length > 0) {
    html += `
      <div class="suggestion-section">
        <h4>Skills to Develop</h4>
        <ul class="suggestion-list">
          ${suggestions.missing_skills_to_add.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
        </ul>
      </div>
    `;
  }
  
  // ATS keywords
  if (suggestions.ats_keywords_to_include && suggestions.ats_keywords_to_include.length > 0) {
    html += `
      <div class="suggestion-section">
        <h4>ATS Keywords to Include</h4>
        <ul class="suggestion-list">
          ${suggestions.ats_keywords_to_include.map(k => `<li>${escapeHtml(k)}</li>`).join('')}
        </ul>
      </div>
    `;
  }
  
  // Projects to build
  if (suggestions.projects_to_build && suggestions.projects_to_build.length > 0) {
    html += `
      <div class="suggestion-section">
        <h4>Recommended Projects</h4>
        <ul class="suggestion-list">
          ${suggestions.projects_to_build.map(p => `<li>${escapeHtml(p)}</li>`).join('')}
        </ul>
      </div>
    `;
  }
  
  // Bullet rewrites
  if (suggestions.bullet_rewrites && suggestions.bullet_rewrites.length > 0) {
    html += `
      <div class="suggestion-section">
        <h4>Resume Bullet Improvements</h4>
        <ul class="suggestion-list">
          ${suggestions.bullet_rewrites.map(b => {
            const before = escapeHtml(b.before || '');
            const after = escapeHtml(b.after || '');
            return `<li><strong>Before:</strong> ${before}<br><strong>After:</strong> ${after}</li>`;
          }).join('')}
        </ul>
      </div>
    `;
  }
  
  html += '</div>';
  elements.suggestionsContent.innerHTML = html;
}

function renderAts(ats) {
  if (!elements.atsContent) return;
  if (!ats) {
    elements.atsContent.innerHTML = `
      <p style="color: var(--text-muted); font-style: italic;">
        No ATS report available for this run.
      </p>
    `;
    return;
  }

  const overall = Math.round(ats.overall_score || 0);
  const req = Math.round(ats.required_coverage_pct || 0);
  const pref = Math.round(ats.preferred_coverage_pct || 0);
  const missingReq = (ats.missing_required || []).slice(0, 10);
  const missingPref = (ats.missing_preferred || []).slice(0, 10);
  const missingSections = (ats.sections_missing || []);

  elements.atsContent.innerHTML = `
    <div class="suggestion-sections">
      <p class="rationale">ATS readiness score: <strong>${overall}%</strong> (Required coverage ${req}%, Preferred ${pref}%).</p>

      ${missingReq.length ? `
        <div class="suggestion-section">
          <h4>Missing Required Keywords</h4>
          <ul class="suggestion-list">
            ${missingReq.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
          </ul>
        </div>
      ` : `
        <div class="suggestion-section">
          <h4>Missing Required Keywords</h4>
          <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.25rem;">None detected.</p>
        </div>
      `}

      ${missingSections.length ? `
        <div class="suggestion-section">
          <h4>Missing Sections</h4>
          <ul class="suggestion-list">
            ${missingSections.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
          </ul>
        </div>
      ` : ``}

      ${(ats.red_flags || []).length ? `
        <div class="suggestion-section">
          <h4>Red Flags</h4>
          <ul class="suggestion-list">
            ${(ats.red_flags || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
          </ul>
        </div>
      ` : ``}

      ${(ats.recommendations || []).length ? `
        <div class="suggestion-section">
          <h4>Recommended Fixes</h4>
          <ul class="suggestion-list">
            ${(ats.recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
          </ul>
        </div>
      ` : ``}

      ${missingPref.length ? `
        <div class="suggestion-section">
          <h4>Optional Keywords to Add</h4>
          <ul class="suggestion-list">
            ${missingPref.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
          </ul>
        </div>
      ` : ``}
    </div>
  `;
}

function renderJobInsights(debug) {
  if (!elements.jobInsightsContent) return;
  if (!debug || Object.keys(debug).length === 0) {
    elements.jobInsightsContent.innerHTML = `
      <p style="color: var(--text-muted); font-style: italic;">
        No job insights available for this run.
      </p>
    `;
    return;
  }

  const roleKeywords = (debug.jd_role_keywords || []).slice(0, 8);
  const experienceLevel = debug.jd_experience_level || 'Not specified';
  const requiredSkills = (debug.jd_required_skills || []).slice(0, 6);
  const preferredSkills = (debug.jd_preferred_skills || []).slice(0, 6);

  elements.jobInsightsContent.innerHTML = `
    <div class="suggestion-sections">
      ${experienceLevel !== 'Not specified' ? `
        <div class="suggestion-section">
          <h4>Experience Level</h4>
          <p style="color: var(--text-primary); font-size: 0.9rem; margin-top: 0.25rem; font-weight: 500;">${escapeHtml(experienceLevel)}</p>
        </div>
      ` : ``}

      ${roleKeywords.length ? `
        <div class="suggestion-section">
          <h4>Role Keywords</h4>
          <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem;">
            ${roleKeywords.map(k => `<span style="padding: 0.25rem 0.5rem; font-size: 0.75rem; background: var(--tertiary-dim); color: var(--tertiary); border-radius: var(--radius-sm);">${escapeHtml(k)}</span>`).join('')}
          </div>
        </div>
      ` : ``}

      ${requiredSkills.length ? `
        <div class="suggestion-section">
          <h4>Required Skills (${requiredSkills.length})</h4>
          <ul class="suggestion-list">
            ${requiredSkills.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
          </ul>
        </div>
      ` : ``}

      ${preferredSkills.length ? `
        <div class="suggestion-section">
          <h4>Preferred Skills (${preferredSkills.length})</h4>
          <ul class="suggestion-list">
            ${preferredSkills.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
          </ul>
        </div>
      ` : ``}
    </div>
  `;
}

function buildChatGptPrompt(payload, forOverleaf = false) {
  const score = payload?.score || {};
  const gap = payload?.skill_gap || {};
  const ats = payload?.ats || {};
  const debug = payload?.debug || {};

  const finalScore = Math.round(Number(score.final_match_score || 0));
  const semanticScore = Math.round(Number(score.semantic_similarity_score || 0));
  const skillScore = Math.round(Number(score.skill_overlap_score || 0));

  const missingRequired = (gap.missing_required_skills || []).slice(0, 12);
  const niceToHave = (gap.nice_to_have_skills || []).slice(0, 12);
  const matching = (gap.matching_skills || []).slice(0, 20);

  const jdRequired = (debug.jd_required_skills || []).slice(0, 18);
  const jdPreferred = (debug.jd_preferred_skills || []).slice(0, 18);
  const roleKeywords = (debug.jd_role_keywords || []).slice(0, 12);
  const experienceLevel = debug.jd_experience_level || 'Not specified';

  const atsMissing = (ats.missing_required || []).slice(0, 12);
  const missingSections = (ats.sections_missing || []).slice(0, 10);

  const resumeSkillList = (resumeSkills || []).slice(0, 40);

  if (forOverleaf) {
    return `You are a LaTeX/Overleaf resume expert and technical recruiter.\n\nGOAL: Help me improve my resume in Overleaf (LaTeX) format to increase match score and fix ATS gaps WITHOUT lying.\nCurrent scores: final=${finalScore}%, semantic=${semanticScore}%, skills=${skillScore}%.\n\nMy resume skills (from parser): ${resumeSkillList.length ? resumeSkillList.join(', ') : 'N/A'}\nMatching skills: ${matching.length ? matching.join(', ') : 'N/A'}\n\nJob insights:\n- Experience level: ${experienceLevel}\n- Role keywords: ${roleKeywords.length ? roleKeywords.join(', ') : 'N/A'}\n- JD required skills: ${jdRequired.length ? jdRequired.join(', ') : 'N/A'}\n- JD preferred skills: ${jdPreferred.length ? jdPreferred.join(', ') : 'N/A'}\n\nGaps:\n- Missing required skills: ${missingRequired.length ? missingRequired.join(', ') : 'None'}\n- Nice-to-have skills: ${niceToHave.length ? niceToHave.join(', ') : 'None'}\n- ATS missing required keywords: ${atsMissing.length ? atsMissing.join(', ') : 'None'}\n- ATS missing sections: ${missingSections.length ? missingSections.join(', ') : 'None'}\n\nTASKS (do ALL):\n1) Provide LaTeX/Overleaf-specific resume improvements. Format all suggestions as valid LaTeX code snippets.\n2) Write a 30-day learning plan targeting missing required skills. Include weekly milestones and resources.\n3) Propose 2 portfolio projects demonstrating missing required skills. For each: scope, tech stack, features, measurable outcomes.\n4) Rewrite 6 resume bullets in STAR/action-impact style as LaTeX \\item entries. IMPORTANT: Do not invent experience; if info is missing, ask 5 clarifying questions first.\n5) Provide ATS keyword injection plan with exact LaTeX formatting: where to add keywords (\\skills{}, \\textbf{}, etc.) + 10 example LaTeX lines.\n6) Provide LaTeX code improvements: better section organization, formatting commands, and structure suggestions.`;
  }

  return `You are a senior technical recruiter + resume coach.\n\nGOAL: Increase my resume-job match score and fix ATS gaps WITHOUT lying.\nCurrent scores: final=${finalScore}%, semantic=${semanticScore}%, skills=${skillScore}%.\n\nMy resume skills (from parser): ${resumeSkillList.length ? resumeSkillList.join(', ') : 'N/A'}\nMatching skills: ${matching.length ? matching.join(', ') : 'N/A'}\n\nJob insights:\n- Experience level: ${experienceLevel}\n- Role keywords: ${roleKeywords.length ? roleKeywords.join(', ') : 'N/A'}\n- JD required skills: ${jdRequired.length ? jdRequired.join(', ') : 'N/A'}\n- JD preferred skills: ${jdPreferred.length ? jdPreferred.join(', ') : 'N/A'}\n\nGaps:\n- Missing required skills: ${missingRequired.length ? missingRequired.join(', ') : 'None'}\n- Nice-to-have skills: ${niceToHave.length ? niceToHave.join(', ') : 'None'}\n- ATS missing required keywords: ${atsMissing.length ? atsMissing.join(', ') : 'None'}\n- ATS missing sections: ${missingSections.length ? missingSections.join(', ') : 'None'}\n\nTASKS (do ALL):\n1) Write a 30-day learning plan that targets ONLY the missing required skills (prioritize by impact). Include weekly milestones and resources.\n2) Propose 2 portfolio projects that naturally demonstrate the missing required skills. For each: scope, tech stack, features, measurable outcomes, and a GitHub README outline.\n3) Rewrite 6 resume bullets in STAR/action-impact style tailored to this role. IMPORTANT: Do not invent experience; if info is missing, ask me 5 clarifying questions first.\n4) Provide an ATS keyword injection plan: exact keywords to add + where to place them (Skills/Experience/Projects) + 10 example lines.\n5) Provide a final checklist titled \"Do this next\" with 10 concrete items.`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// New analysis
elements.btnNew.addEventListener('click', () => {
  currentResumeId = null;
  currentAnalysisId = null;
  persistState();  // Clear from localStorage
  resumeSkills = [];
  
  // Reset upload
  elements.filePreview.classList.add('hidden');
  elements.uploadZone.classList.remove('hidden');
  elements.btnUpload.disabled = true;
  elements.fileInput.value = '';
  elements.fileInput._selectedFile = null;
  
  // Reset JD
  elements.jdInput.value = '';
  elements.btnAnalyze.disabled = true;
  
  showStep('step-upload');
});

// Download report
elements.btnDownload.addEventListener('click', async () => {
  if (!currentAnalysisId || !currentResumeId) {
    showCustomAlert('Please upload a resume and run an analysis first.', 'error');
    return;
  }
  
  try {
    // Fetch all data
    const [scoreRes, gapRes, suggestRes] = await Promise.all([
      fetch(`${API_BASE}/match-score?analysis_id=${currentAnalysisId}`),
      fetch(`${API_BASE}/skill-gap-report?analysis_id=${currentAnalysisId}`),
      fetch(`${API_BASE}/resume-suggestions?analysis_id=${currentAnalysisId}`),
    ]);
    
    const score = await scoreRes.json();
    const gap = await gapRes.json();
    const suggest = await suggestRes.json();
    
    // Build report
    const report = {
      generated_at: new Date().toISOString(),
      analysis_id: currentAnalysisId,
      score,
      skill_gap: gap,
      suggestions: suggest.suggestions,
    };
    
    // Download as JSON
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `resume-analysis-${currentAnalysisId.slice(-8)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
  } catch (error) {
    showCustomAlert('Error downloading report: ' + error.message, 'error');
  }
});

// ========================================
// Export page
// ========================================

// Extract name and email from resume text
function extractNameAndEmailFromResume(text) {
  if (!text) return { name: '', email: '', company: '' };
  
  // Extract email using regex
  const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/;
  const emailMatch = text.match(emailRegex);
  const email = emailMatch ? emailMatch[0] : '';
  
  // Extract name - usually at the start of resume, before email
  // Look for first 1-4 capitalized words (typically 2-3 words for names)
  let name = '';
  
  if (email) {
    // Get text before email
    const beforeEmail = text.substring(0, text.indexOf(email)).trim();
    
    // Try to match capitalized words at the start (1-4 words)
    const namePattern = /^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})/;
    const nameMatch = beforeEmail.match(namePattern);
    if (nameMatch) {
      name = nameMatch[1].trim();
    }
  }
  
  // Fallback: if no email found or name not extracted, try first line
  if (!name) {
    const firstLine = text.split(/[\n—–-]/)[0].trim();
    const namePattern = /^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})/;
    const nameMatch = firstLine.match(namePattern);
    if (nameMatch && firstLine.length < 100) {
      name = nameMatch[1].trim();
    }
  }
  
  // Extract company name from experience section
  let company = '';
  const experienceKeywords = ['Experience', 'Work', 'Employment', 'Career'];
  for (const keyword of experienceKeywords) {
    const expIndex = text.indexOf(keyword);
    if (expIndex !== -1) {
      const expSection = text.substring(expIndex, expIndex + 500);
      // Look for company patterns: "at CompanyName", "— CompanyName", etc.
      const companyPatterns = [
        /(?:at|@|—|–)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+—|\s+\(|\s+GitHub|\s+•|$)/,
        /([A-Z][A-Za-z0-9\s&]+?)\s+(?:—|–|•)\s+(?:Remote|Hybrid|Full-time|Part-time)/
      ];
      for (const pattern of companyPatterns) {
        const match = expSection.match(pattern);
        if (match && match[1]) {
          company = match[1].trim();
          // Clean up common suffixes
          company = company.replace(/\s+(Inc|LLC|Ltd|Corp|Corporation|Company)$/i, '').trim();
          if (company.length > 3 && company.length < 50) break;
        }
      }
      if (company) break;
    }
  }
  
  return { name: name || '', email: email || '', company: company || '' };
}

// Fetch resume raw text and extract data if not already done
async function fetchAndExtractResumeData() {
  if (!currentResumeId) return extractedResumeData;
  
  // If we already have the data, use it
  if (resumeRawText && (extractedResumeData.name || extractedResumeData.email)) {
    return extractedResumeData;
  }
  
  try {
    const resumeRes = await fetch(`${API_BASE}/resume/${currentResumeId}`);
    if (resumeRes.ok) {
      const resumeData = await resumeRes.json();
      resumeRawText = resumeData.raw_text || '';
      // Extract name, email, and company from resume text
      extractedResumeData = extractNameAndEmailFromResume(resumeRawText);
    }
  } catch (e) {
    console.warn('Could not fetch resume data:', e);
  }
  
  return extractedResumeData;
}

async function renderExport() {
  console.log('renderExport called - currentResumeId:', currentResumeId, 'currentAnalysisId:', currentAnalysisId);
  const hasAnalysis = Boolean(currentAnalysisId);
  if (elements.exportWarning) elements.exportWarning.style.display = hasAnalysis ? 'none' : 'block';
  // Don't disable buttons - let click handlers show alerts instead
  // This allows users to get feedback when they click without analysis
  
  // Fetch and extract resume data if we have a resume ID
  if (currentResumeId) {
    await fetchAndExtractResumeData();
    
    // Auto-populate resume fields if we have extracted data (only if fields are empty)
    if (extractedResumeData.name && elements.coverLetterName && !elements.coverLetterName.value.trim()) {
      elements.coverLetterName.value = extractedResumeData.name;
    }
    if (extractedResumeData.email && elements.coverLetterEmail && !elements.coverLetterEmail.value.trim()) {
      elements.coverLetterEmail.value = extractedResumeData.email;
    }
    if (extractedResumeData.company && elements.coverLetterCompany && !elements.coverLetterCompany.value.trim()) {
      elements.coverLetterCompany.value = extractedResumeData.company;
    }
  }
  
  // Reset message generator view if no analysis
  if (!hasAnalysis) {
    const emptyState = document.getElementById('cover-letter-empty');
    if (emptyState) emptyState.style.display = 'flex';
    if (elements.coverLetterGeneratedView) elements.coverLetterGeneratedView.style.display = 'none';
  }
}

async function downloadDocx(mode) {
  if (!currentAnalysisId || !currentResumeId) {
    showCustomAlert('Please upload a resume and run an analysis first.', 'error');
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/export/docx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: currentAnalysisId, mode }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'DOCX export failed');
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = mode === 'cover_letter'
      ? `cover-letter-${currentAnalysisId.slice(-8)}.docx`
      : `tailored-bullets-${currentAnalysisId.slice(-8)}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
      showCustomAlert('Error exporting DOCX: ' + (e?.message || String(e)), 'error');
  }
}

if (elements.btnExportJson) {
  elements.btnExportJson.addEventListener('click', () => {
    if (!currentAnalysisId || !currentResumeId) {
      showCustomAlert('Please upload a resume and run an analysis first.', 'error');
      return;
    }
    elements.btnDownload?.click();
  });
}
if (elements.btnExportPdf) {
  elements.btnExportPdf.addEventListener('click', async () => {
    if (!currentAnalysisId || !currentResumeId) {
      showCustomAlert('Please upload a resume and run an analysis first.', 'error');
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/export/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_id: currentAnalysisId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'PDF export failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume-analysis-${currentAnalysisId.slice(-8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      showCustomAlert('Error exporting PDF: ' + (e?.message || String(e)), 'error');
    }
  });
}

if (elements.btnExportDocxBullets) {
  elements.btnExportDocxBullets.addEventListener('click', () => {
    if (!currentAnalysisId || !currentResumeId) {
      showCustomAlert('Please upload a resume and run an analysis first.', 'error');
      return;
    }
    downloadDocx('resume_bullets');
  });
}

// Cover Letter Generation
if (elements.btnGenerateCoverLetter) {
  elements.btnGenerateCoverLetter.addEventListener('click', async () => {
    // Debug logging
    console.log('Generate Messages clicked - currentResumeId:', currentResumeId, 'currentAnalysisId:', currentAnalysisId);
    
    // Better validation with specific error messages
    if (!currentResumeId) {
      console.warn('Validation failed: No currentResumeId');
      showCustomAlert('Please upload a resume first.', 'error');
      return;
    }
    if (!currentAnalysisId) {
      console.warn('Validation failed: No currentAnalysisId');
      showCustomAlert('Please run an analysis first. Go to the "Analyze" page, paste a job description, and click "Analyze Match".', 'error');
      return;
    }
    
    console.log('Validation passed, proceeding with message generation...');
    
    const name = (elements.coverLetterName?.value || '').trim() || 'Your Name';
    const email = (elements.coverLetterEmail?.value || '').trim() || 'your.email@example.com';
    const company = (elements.coverLetterCompany?.value || '').trim();
    
    elements.btnGenerateCoverLetter.classList.add('loading');
    elements.btnGenerateCoverLetter.disabled = true;
    
    try {
      const res = await fetch(`${API_BASE}/generate-messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_id: currentAnalysisId,
          candidate_name: name,
          candidate_email: email,
          company_name: company,
        }),
      });
      
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Cover letter generation failed');
      }
      
      const data = await res.json();

      if (elements.coverLetterText) elements.coverLetterText.value = data.cover_letter || '';
      if (elements.linkedinMessageText) elements.linkedinMessageText.value = data.linkedin_message || '';
      if (elements.coldmailText) elements.coldmailText.value = data.cold_mail || '';
      
      // Hide empty state and show generated view
      const emptyState = document.getElementById('cover-letter-empty');
      if (emptyState) {
        emptyState.style.display = 'none';
      }
      if (elements.coverLetterGeneratedView) {
        elements.coverLetterGeneratedView.style.display = 'block';
      }

      // Default to cover letter tab after generation
      switchMessageType('cover-letter');
      
      // Show success message
      showCustomAlert('Messages generated successfully!', 'success');
    } catch (e) {
      showCustomAlert('Error generating messages: ' + (e?.message || String(e)), 'error');
    } finally {
      elements.btnGenerateCoverLetter.classList.remove('loading');
      elements.btnGenerateCoverLetter.disabled = false;
    }
  });
}

// Handle message type switching
function switchMessageType(type) {
  // Hide all outputs
  document.querySelectorAll('.message-output').forEach(el => el.style.display = 'none');
  
  // Remove active class from all buttons
  document.querySelectorAll('.message-type-btn').forEach(btn => {
    btn.classList.remove('active', 'btn-primary');
    btn.classList.add('btn-secondary');
  });
  
  // Show selected output and activate button
  const outputEl = document.getElementById(`output-${type}`);
  const btnEl = document.getElementById(`btn-option-${type}`);
  
  if (outputEl) outputEl.style.display = 'block';
  if (btnEl) {
    btnEl.classList.add('active', 'btn-primary');
    btnEl.classList.remove('btn-secondary');
  }
}

if (elements.btnOptionCoverLetter) {
  elements.btnOptionCoverLetter.addEventListener('click', () => switchMessageType('cover-letter'));
}
if (elements.btnOptionLinkedin) {
  elements.btnOptionLinkedin.addEventListener('click', () => switchMessageType('linkedin'));
}
if (elements.btnOptionColdmail) {
  elements.btnOptionColdmail.addEventListener('click', () => switchMessageType('coldmail'));
}

// Copy and download functions for all message types
if (elements.btnCopyCoverLetter) {
  elements.btnCopyCoverLetter.addEventListener('click', async () => {
    const text = elements.coverLetterText?.value || '';
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      showCustomAlert('Cover letter copied to clipboard!', 'success');
    } catch {
      elements.coverLetterText.select();
      document.execCommand('copy');
      showCustomAlert('Cover letter copied to clipboard!', 'success');
    }
  });
}

if (elements.btnDownloadCoverLetter) {
  elements.btnDownloadCoverLetter.addEventListener('click', () => {
    const text = elements.coverLetterText?.value || '';
    if (!text.trim()) return;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cover-letter-${currentAnalysisId?.slice(-8) || 'letter'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

if (elements.btnCopyLinkedin) {
  elements.btnCopyLinkedin.addEventListener('click', async () => {
    const text = elements.linkedinMessageText?.value || '';
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      showCustomAlert('LinkedIn message copied to clipboard!', 'success');
    } catch {
      elements.linkedinMessageText.select();
      document.execCommand('copy');
      showCustomAlert('LinkedIn message copied to clipboard!', 'success');
    }
  });
}

if (elements.btnDownloadLinkedin) {
  elements.btnDownloadLinkedin.addEventListener('click', () => {
    const text = elements.linkedinMessageText?.value || '';
    if (!text.trim()) return;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `linkedin-message-${currentAnalysisId?.slice(-8) || 'message'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

if (elements.btnCopyColdmail) {
  elements.btnCopyColdmail.addEventListener('click', async () => {
    const text = elements.coldmailText?.value || '';
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      showCustomAlert('Cold mail copied to clipboard!', 'success');
    } catch {
      elements.coldmailText.select();
      document.execCommand('copy');
      showCustomAlert('Cold mail copied to clipboard!', 'success');
    }
  });
}

if (elements.btnDownloadColdmail) {
  elements.btnDownloadColdmail.addEventListener('click', () => {
    const text = elements.coldmailText?.value || '';
    if (!text.trim()) return;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cold-mail-${currentAnalysisId?.slice(-8) || 'mail'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

// Copy ChatGPT prompt (normal version)
if (elements.btnCopyChatgptPrompt) {
  elements.btnCopyChatgptPrompt.addEventListener('click', async () => {
    if (!lastAnalysisPayload) {
      showCustomAlert('Run an analysis first to generate the prompt.', 'error');
      return;
    }
    const prompt = buildChatGptPrompt(lastAnalysisPayload, false);
    try {
      await navigator.clipboard.writeText(prompt);
      showCustomAlert('ChatGPT prompt copied to clipboard!', 'success');
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = prompt;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showCustomAlert('ChatGPT prompt copied to clipboard!', 'success');
    }
  });
}

// Copy ChatGPT prompt (Overleaf version)
if (elements.btnCopyChatgptOverleaf) {
  elements.btnCopyChatgptOverleaf.addEventListener('click', async () => {
    if (!lastAnalysisPayload) {
      showCustomAlert('Run an analysis first to generate the prompt.', 'error');
      return;
    }
    const prompt = buildChatGptPrompt(lastAnalysisPayload, true);
    try {
      await navigator.clipboard.writeText(prompt);
      showCustomAlert('Overleaf ChatGPT prompt copied to clipboard!', 'success');
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = prompt;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showCustomAlert('Overleaf ChatGPT prompt copied to clipboard!', 'success');
    }
  });
}

// ========================================
// Welcome Modal
// ========================================

function showWelcomeModal() {
  // Check if user has seen welcome before
  const hasSeenWelcome = localStorage.getItem('resumeai_welcome_seen');
  if (hasSeenWelcome) return;

  const modal = document.getElementById('welcome-modal');
  if (!modal) return;

  modal.style.display = 'flex';
  
  // Close button
  const closeBtn = document.getElementById('btn-welcome-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.style.display = 'none';
      localStorage.setItem('resumeai_welcome_seen', 'true');
    });
  }

  // Get Started button
  const startBtn = document.getElementById('btn-welcome-start');
  if (startBtn) {
    startBtn.addEventListener('click', () => {
      modal.style.display = 'none';
      localStorage.setItem('resumeai_welcome_seen', 'true');
      // Navigate to upload step
      showPage('page-analyze');
      showStep('step-upload');
    });
  }

  // Close on overlay click
  const overlay = modal.querySelector('.welcome-modal-overlay');
  if (overlay) {
    overlay.addEventListener('click', () => {
      modal.style.display = 'none';
      localStorage.setItem('resumeai_welcome_seen', 'true');
    });
  }
}

// ========================================
// Init
// ========================================

console.log('ResumeAI Frontend loaded');
console.log('API Base:', API_BASE);

// Show welcome modal on first visit
setTimeout(() => {
  showWelcomeModal();
}, 500);

// Default page
showPage('page-analyze');


