/**
 * PortfolioPulse - Yahoo Finance Portfolio & Holding Analyzer Frontend Logic
 */

const state = {
  analysisData: null,
  currentFilter: 'all', // 'all', 'profit', 'loss', 'dividend'
  searchQuery: '',
  sortColumn: 'marketValue',
  sortAscending: false,
  selectedFile: null
};

// Distinct colors for sector allocation bar
const SECTOR_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899',
  '#06b6d4', '#14b8a6', '#f97316', '#6366f1', '#eab308'
];

// Formatting Utilities
function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined || isNaN(num)) return 'N/A';
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

function formatCurrency(num, curr = '₹') {
  if (num === null || num === undefined || isNaN(num)) return 'N/A';
  const val = Number(num);
  const absVal = Math.abs(val);

  let formatted = '';
  if (absVal >= 1e7) { // 1 Crore = 10M
    formatted = `${(val / 1e7).toFixed(2)} Cr`;
  } else if (absVal >= 1e5) { // 1 Lakh = 100k
    formatted = `${(val / 1e5).toFixed(2)} L`;
  } else {
    formatted = val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return `${curr}${formatted}`;
}

function formatPercent(num) {
  if (num === null || num === undefined || isNaN(num)) return 'N/A';
  const val = Number(num);
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}

function showToast(message, isError = false) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderColor = isError ? 'var(--color-down)' : 'var(--color-up)';
  toast.innerHTML = `<span>${isError ? '⚠️' : '✅'}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ==================== FETCH & RENDER PORTFOLIO ====================

async function fetchPortfolioAnalysis() {
  const banner = document.getElementById('loading-banner');
  if (banner) banner.style.display = 'flex';

  try {
    const res = await fetch('/api/portfolio/analysis');
    if (!res.ok) throw new Error('Failed to fetch portfolio analysis');
    const data = await res.json();
    state.analysisData = data;

    renderKPIs(data.summary, data.rawTransactionCount);
    renderSectorAllocation(data.sectorAllocation, data.summary.totalMarketValue);
    renderPerformanceHighlights(data);
    renderHoldingsTable();
  } catch (err) {
    console.error('Error fetching analysis:', err);
    showToast('Failed to load portfolio analysis: ' + err.message, true);
  } finally {
    if (banner) banner.style.display = 'none';
  }
}

function renderKPIs(summary, rawTxCount = 0) {
  // Currency detector (if Indian stocks dominant, use ₹, else $)
  const holdings = state.analysisData ? state.analysisData.holdings : [];
  const curr = (holdings.length > 0 && holdings[0].currency === 'INR') ? '₹' : '$';

  // Header meta pill
  document.getElementById('header-meta-pill').innerText =
    `${summary.totalHoldings} Active Holdings | ${rawTxCount.toLocaleString()} Transactions Analyzed`;

  // 1. Total Portfolio Value
  document.getElementById('kpi-total-val').innerText = formatCurrency(summary.totalMarketValue, curr);
  document.getElementById('kpi-total-cost').innerText = formatCurrency(summary.totalCostBasis, curr);

  // 2. Total Unrealized Return
  const isUp = summary.totalGainLoss >= 0;
  const gainValElem = document.getElementById('kpi-total-gain');
  gainValElem.innerText = `${isUp ? '+' : ''}${formatCurrency(summary.totalGainLoss, curr)}`;
  gainValElem.style.color = isUp ? 'var(--color-up)' : 'var(--color-down)';

  const gainPctElem = document.getElementById('kpi-gain-pct');
  gainPctElem.className = `delta-badge ${isUp ? 'up' : 'down'}`;
  gainPctElem.innerText = formatPercent(summary.totalGainLossPercent);

  // 3. Today's Day Change
  const dayUp = summary.totalDayChange >= 0;
  const dayValElem = document.getElementById('kpi-day-gain');
  dayValElem.innerText = `${dayUp ? '+' : ''}${formatCurrency(summary.totalDayChange, curr)}`;
  dayValElem.style.color = dayUp ? 'var(--color-up)' : 'var(--color-down)';

  const dayPctElem = document.getElementById('kpi-day-pct');
  dayPctElem.className = `delta-badge ${dayUp ? 'up' : 'down'}`;
  dayPctElem.innerText = formatPercent(summary.totalDayChangePercent);

  // 4. Annual Dividend Income
  document.getElementById('kpi-dividend-income').innerText = formatCurrency(summary.totalAnnualDividends, curr);
  document.getElementById('kpi-dividend-yield').innerText = `${summary.portfolioDividendYield.toFixed(2)}%`;

  // 5. Portfolio Beta
  const beta = summary.portfolioBeta || 1.0;
  document.getElementById('kpi-portfolio-beta').innerText = beta.toFixed(2);
  const betaDesc = document.getElementById('kpi-beta-desc');
  if (beta < 0.8) {
    betaDesc.innerHTML = `<span style="color: #38bdf8;">Low Volatility / Conservative</span>`;
  } else if (beta <= 1.15) {
    betaDesc.innerHTML = `<span>Market Correlated Risk</span>`;
  } else {
    betaDesc.innerHTML = `<span style="color: #f59e0b;">Higher Volatility / Growth</span>`;
  }

  // 6. Weighted P/E
  document.getElementById('kpi-portfolio-pe').innerText = summary.portfolioPE ? `${summary.portfolioPE.toFixed(1)}x` : 'N/A';
  document.getElementById('kpi-holdings-count').innerText = summary.totalHoldings;
}

function renderSectorAllocation(sectors, totalVal) {
  const bar = document.getElementById('sector-bar');
  const list = document.getElementById('sector-list');
  const countLabel = document.getElementById('sector-count-label');

  if (!sectors || sectors.length === 0) {
    bar.innerHTML = '';
    list.innerHTML = `<div style="font-size: 13px; color: var(--text-muted);">No sector data available</div>`;
    countLabel.innerText = '0 Sectors';
    return;
  }

  countLabel.innerText = `${sectors.length} Sectors`;

  // Render multi-segment bar
  bar.innerHTML = sectors.map((s, i) => {
    const color = SECTOR_COLORS[i % SECTOR_COLORS.length];
    return `<div class="alloc-bar-segment" style="width: ${s.percentage}%; background-color: ${color};" title="${s.sector}: ${s.percentage}%"></div>`;
  }).join('');

  // Render sector pill cards
  list.innerHTML = sectors.map((s, i) => {
    const color = SECTOR_COLORS[i % SECTOR_COLORS.length];
    return `
      <div class="sector-pill">
        <div class="sector-name-group">
          <span class="sector-dot" style="background-color: ${color};"></span>
          <span class="sector-name">${s.sector}</span>
        </div>
        <div class="sector-val-group">
          <div class="sector-pct">${s.percentage}%</div>
          <div class="sector-amount">${formatCurrency(s.value)}</div>
        </div>
      </div>
    `;
  }).join('');
}

function renderPerformanceHighlights(data) {
  const summary = data.summary;
  document.getElementById('ratio-profit-loss').innerText =
    `${summary.profitableCount} Profitable / ${summary.lossCount} in Loss`;

  // Top Gainers
  const gainersList = document.getElementById('top-gainers-list');
  if (data.topWinners && data.topWinners.length > 0) {
    gainersList.innerHTML = data.topWinners.map(h => `
      <div class="performer-item">
        <span class="performer-sym" onclick="window.openDeepDive('${h.symbol}')" style="cursor: pointer; color: #38bdf8;">${h.symbol}</span>
        <span class="delta-badge up">${formatPercent(h.gainLossPercent)}</span>
      </div>
    `).join('');
  } else {
    gainersList.innerHTML = `<div style="font-size: 12px; color: var(--text-muted);">None</div>`;
  }

  // Top Losers
  const losersList = document.getElementById('top-losers-list');
  if (data.topLosers && data.topLosers.length > 0) {
    losersList.innerHTML = data.topLosers.map(h => `
      <div class="performer-item">
        <span class="performer-sym" onclick="window.openDeepDive('${h.symbol}')" style="cursor: pointer; color: #38bdf8;">${h.symbol}</span>
        <span class="delta-badge down">${formatPercent(h.gainLossPercent)}</span>
      </div>
    `).join('');
  } else {
    losersList.innerHTML = `<div style="font-size: 12px; color: var(--text-muted);">None</div>`;
  }

  // Market Cap classification distribution
  const mcapContainer = document.getElementById('mcap-distribution-bars');
  if (data.marketCapAllocation) {
    mcapContainer.innerHTML = data.marketCapAllocation.map(m => `
      <div style="flex: 1; background: var(--bg-secondary); border: 1px solid var(--border-color); padding: 8px 10px; border-radius: 6px; text-align: center;">
        <span style="display: block; font-size: 10px; color: var(--text-muted); text-transform: uppercase;">${m.category}</span>
        <b style="color: var(--text-primary); font-size: 13px;">${m.percentage}%</b>
      </div>
    `).join('');
  }
}

// ==================== HOLDINGS TABLE RENDERING ====================

function renderHoldingsTable() {
  if (!state.analysisData || !state.analysisData.holdings) return;

  let list = [...state.analysisData.holdings];

  // Update filter counters
  document.getElementById('count-all').innerText = list.length;
  document.getElementById('count-profit').innerText = list.filter(h => h.gainLoss >= 0).length;
  document.getElementById('count-loss').innerText = list.filter(h => h.gainLoss < 0).length;
  document.getElementById('count-dividend').innerText = list.filter(h => (h.dividendYield || 0) > 0).length;

  // Filter tab
  if (state.currentFilter === 'profit') {
    list = list.filter(h => h.gainLoss >= 0);
  } else if (state.currentFilter === 'loss') {
    list = list.filter(h => h.gainLoss < 0);
  } else if (state.currentFilter === 'dividend') {
    list = list.filter(h => (h.dividendYield || 0) > 0);
  }

  // Search query filter
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter(h =>
      h.symbol.toLowerCase().includes(q) ||
      (h.shortName && h.shortName.toLowerCase().includes(q)) ||
      (h.sector && h.sector.toLowerCase().includes(q))
    );
  }

  // Sort
  list.sort((a, b) => {
    let valA = a[state.sortColumn];
    let valB = b[state.sortColumn];

    if (valA === null || valA === undefined) valA = -99999999;
    if (valB === null || valB === undefined) valB = -99999999;

    if (typeof valA === 'string') {
      return state.sortAscending ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return state.sortAscending ? (valA - valB) : (valB - valA);
  });

  const tbody = document.getElementById('holdings-tbody');
  if (list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="17" style="text-align: center; padding: 48px; color: var(--text-muted);">
          <h4>No matching holdings found</h4>
          <p>Try adjusting your search filter or import your portfolio transactions.</p>
        </td>
      </tr>
    `;
    return;
  }

  const curr = (list.length > 0 && list[0].currency === 'INR') ? '₹' : '$';

  tbody.innerHTML = list.map(h => {
    const isUp = h.gainLoss >= 0;
    const dayUp = (h.positionDayChange || 0) >= 0;

    // 52-Week Range dot position
    const rPct = Math.max(0, Math.min(100, h.range52WeekPercent || 50));

    // Analyst Consensus badge
    let recBadge = '-';
    if (h.recommendationKey && h.recommendationKey !== 'N/A') {
      let bColor = '#3b82f6';
      if (h.recommendationKey.includes('BUY')) bColor = 'var(--color-up)';
      if (h.recommendationKey.includes('SELL')) bColor = 'var(--color-down)';
      recBadge = `<span class="tag-badge" style="color: ${bColor}; border-color: ${bColor}; font-size: 10px;">${h.recommendationKey}</span>`;
      if (h.targetUpsidePercent !== null) {
        const uSign = h.targetUpsidePercent >= 0 ? '+' : '';
        recBadge += ` <span style="font-size: 11px; color: ${h.targetUpsidePercent >= 0 ? 'var(--color-up)' : 'var(--color-down)'};">${uSign}${h.targetUpsidePercent}%</span>`;
      }
    }

    return `
      <tr>
        <!-- Stock / Company -->
        <td>
          <div class="stock-cell-title">
            <span class="stock-sym-link" onclick="window.openDeepDive('${h.symbol}')">
              ${h.symbol}
            </span>
            <span class="stock-name-sub" title="${h.shortName || h.symbol}">${h.shortName || h.symbol}</span>
          </div>
        </td>

        <!-- Sector -->
        <td>
          <span class="tag-badge">${h.sector || 'Other'}</span>
        </td>

        <!-- Shares -->
        <td style="font-weight: 600;">${formatNumber(h.shares, 2)}</td>

        <!-- Avg Buy Price -->
        <td>${formatCurrency(h.avgBuyPrice, curr)}</td>

        <!-- Live Price -->
        <td><b>${formatCurrency(h.currentPrice, curr)}</b></td>

        <!-- Today's P&L -->
        <td class="${dayUp ? 'delta-badge up' : 'delta-badge down'}">
          ${dayUp ? '+' : ''}${formatCurrency(h.positionDayChange, curr)}
          <span style="font-size: 10px;">(${formatPercent(h.positionDayChangePercent)})</span>
        </td>

        <!-- Market Value -->
        <td><b>${formatCurrency(h.marketValue, curr)}</b></td>

        <!-- Cost Basis -->
        <td>${formatCurrency(h.costBasis, curr)}</td>

        <!-- Total P&L -->
        <td class="${isUp ? 'delta-badge up' : 'delta-badge down'}" style="font-size: 13px;">
          ${isUp ? '+' : ''}${formatCurrency(h.gainLoss, curr)}
        </td>

        <!-- Return % -->
        <td class="${isUp ? 'delta-badge up' : 'delta-badge down'}" style="font-size: 13px;">
          ${formatPercent(h.gainLossPercent)}
        </td>

        <!-- Weight % -->
        <td>
          <div class="weight-bar-bg">
            <div class="weight-bar-fill" style="width: ${Math.min(100, (h.portfolioWeightPercent || 0) * 3)}%;"></div>
          </div>
          <b>${(h.portfolioWeightPercent || 0).toFixed(2)}%</b>
        </td>

        <!-- P/E (TTM) -->
        <td>${h.trailingPE ? h.trailingPE.toFixed(1) : '-'}</td>

        <!-- Dividend Yield -->
        <td>
          ${h.dividendYield ? `<b>${h.dividendYield.toFixed(2)}%</b>` : '-'}
          ${h.positionAnnualDividend > 0 ? `<div style="font-size: 10px; color: var(--text-muted);">${formatCurrency(h.positionAnnualDividend, curr)}/yr</div>` : ''}
        </td>

        <!-- Beta -->
        <td>${h.beta ? h.beta.toFixed(2) : '-'}</td>

        <!-- 52W Range -->
        <td>
          <div class="range-mini-track" title="52W Range: ${formatCurrency(h.fiftyTwoWeekLow, curr)} - ${formatCurrency(h.fiftyTwoWeekHigh, curr)}">
            <div class="range-mini-dot" style="left: ${rPct}%;"></div>
          </div>
        </td>

        <!-- Analyst Consensus -->
        <td>${recBadge}</td>

        <!-- Actions -->
        <td style="text-align: center;">
          <button class="btn" style="padding: 4px 8px; font-size: 11px;" onclick="window.openDeepDive('${h.symbol}')">🔍 Analyze</button>
          <button class="btn" style="padding: 4px 6px; font-size: 11px; color: var(--color-down);" onclick="window.deleteHolding('${h.symbol}')" title="Delete holding">✕</button>
        </td>
      </tr>
    `;
  }).join('');
}

// Table sorting & filtering
function sortTable(column) {
  if (state.sortColumn === column) {
    state.sortAscending = !state.sortAscending;
  } else {
    state.sortColumn = column;
    state.sortAscending = false;
  }
  renderHoldingsTable();
}

function setFilter(filter) {
  state.currentFilter = filter;
  document.querySelectorAll('.filter-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  renderHoldingsTable();
}

function handleSearchFilter(e) {
  state.searchQuery = e.target.value.trim();
  renderHoldingsTable();
}

// ==================== 1-CLICK LOCAL IMPORT & BULK CSV UPLOAD ====================

async function loadLocalPortfolioCSV() {
  const banner = document.getElementById('loading-banner');
  const text = document.getElementById('loading-text');
  if (banner) {
    text.innerText = 'Parsing portfolio.csv from workspace and fetching live Yahoo Finance analytics...';
    banner.style.display = 'flex';
  }

  try {
    const res = await fetch('/api/portfolio/load-local', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load local portfolio.csv');

    showToast(`Successfully imported ${data.parsedTransactions.toLocaleString()} transactions (${data.activeHoldingsCount} active stocks)!`);
    await fetchPortfolioAnalysis();
  } catch (err) {
    showToast(err.message, true);
  } finally {
    if (banner) banner.style.display = 'none';
  }
}

function openUploadModal() {
  document.getElementById('upload-modal').classList.add('open');
}

function closeUploadModal() {
  document.getElementById('upload-modal').classList.remove('open');
  state.selectedFile = null;
  document.getElementById('selected-file-info').style.display = 'none';
  document.getElementById('btn-submit-upload').disabled = true;
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    setSelectedFile(file);
  }
}

function setSelectedFile(file) {
  state.selectedFile = file;
  const infoBox = document.getElementById('selected-file-info');
  document.getElementById('selected-file-name').innerText = file.name;
  document.getElementById('selected-file-size').innerText = `${(file.size / 1024).toFixed(1)} KB`;
  infoBox.style.display = 'block';
  document.getElementById('btn-submit-upload').disabled = false;
}

async function uploadFile() {
  if (!state.selectedFile) return;

  const mode = document.querySelector('input[name="upload-mode"]:checked').value;
  const formData = new FormData();
  formData.append('file', state.selectedFile);
  formData.append('mode', mode);

  closeUploadModal();

  const banner = document.getElementById('loading-banner');
  const text = document.getElementById('loading-text');
  if (banner) {
    text.innerText = 'Uploading and analyzing portfolio with Yahoo Finance...';
    banner.style.display = 'flex';
  }

  try {
    const res = await fetch('/api/portfolio/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    showToast(`Uploaded ${data.parsedTransactions.toLocaleString()} transactions (${data.activeHoldingsCount} active stocks)!`);
    await fetchPortfolioAnalysis();
  } catch (err) {
    showToast(err.message, true);
  } finally {
    if (banner) banner.style.display = 'none';
  }
}

// Drag & drop setup
document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, e => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, e => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
      });
    });
    dropzone.addEventListener('drop', e => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        setSelectedFile(files[0]);
      }
    });
  }

  // Load portfolio on startup
  fetchPortfolioAnalysis();
});

// ==================== DEEP DIVE MODAL ====================

async function openDeepDive(symbol) {
  const modal = document.getElementById('deep-dive-modal');
  modal.classList.add('open');

  document.getElementById('dd-symbol').innerText = symbol;
  document.getElementById('dd-name').innerText = 'Loading company info...';

  try {
    const res = await fetch(`/api/holding/deep-dive/${symbol}`);
    const d = await res.json();

    const curr = d.currency === 'INR' ? '₹' : '$';

    document.getElementById('dd-name').innerText = d.longName || d.shortName || symbol;
    document.getElementById('dd-sector').innerText = d.sector || 'N/A';
    document.getElementById('dd-price').innerText = formatCurrency(d.currentPrice, curr);

    const isUp = (d.dayChange || 0) >= 0;
    const deltaElem = document.getElementById('dd-delta');
    deltaElem.className = `delta-badge ${isUp ? 'up' : 'down'}`;
    deltaElem.innerText = `${isUp ? '+' : ''}${(d.dayChange || 0).toFixed(2)} (${formatPercent(d.dayChangePercent)})`;

    document.getElementById('dd-exchange').innerText = d.exchange || 'N/A';

    // Valuation Multiples
    document.getElementById('dd-trailingPE').innerText = d.trailingPE ? `${d.trailingPE.toFixed(2)}x` : 'N/A';
    document.getElementById('dd-forwardPE').innerText = d.forwardPE ? `${d.forwardPE.toFixed(2)}x` : 'N/A';
    document.getElementById('dd-priceToBook').innerText = d.priceToBook ? `${d.priceToBook.toFixed(2)}x` : 'N/A';
    document.getElementById('dd-priceToSales').innerText = d.priceToSales ? `${d.priceToSales.toFixed(2)}x` : 'N/A';
    document.getElementById('dd-evEbitda').innerText = d.enterpriseToEbitda ? `${d.enterpriseToEbitda.toFixed(2)}x` : 'N/A';
    document.getElementById('dd-pegRatio').innerText = d.pegRatio ? `${d.pegRatio.toFixed(2)}` : 'N/A';
    document.getElementById('dd-eps').innerText = d.trailingEps ? `${curr}${d.trailingEps.toFixed(2)}` : 'N/A';
    document.getElementById('dd-divYield').innerText = d.dividendYield ? `${d.dividendYield.toFixed(2)}%` : 'N/A';

    // Profitability & Debt
    document.getElementById('dd-opMargin').innerText = d.operatingMargins ? `${d.operatingMargins.toFixed(2)}%` : 'N/A';
    document.getElementById('dd-profitMargin').innerText = d.profitMargins ? `${d.profitMargins.toFixed(2)}%` : 'N/A';
    document.getElementById('dd-roe').innerText = d.returnOnEquity ? `${d.returnOnEquity.toFixed(2)}%` : 'N/A';
    document.getElementById('dd-debtEquity').innerText = d.debtToEquity ? `${d.debtToEquity.toFixed(2)}` : 'N/A';
    document.getElementById('dd-totalCash').innerText = formatCurrency(d.totalCash, curr);
    document.getElementById('dd-totalDebt').innerText = formatCurrency(d.totalDebt, curr);
    document.getElementById('dd-freeCashflow').innerText = formatCurrency(d.freeCashflow, curr);
    document.getElementById('dd-beta').innerText = d.beta ? `${d.beta.toFixed(2)}` : 'N/A';

    // Forecast
    document.getElementById('dd-analystRating').innerText = d.recommendationKey || 'N/A';
    document.getElementById('dd-targetPrice').innerText = formatCurrency(d.targetMeanPrice, curr);

    const upsideElem = document.getElementById('dd-targetUpside');
    const uUp = (d.targetUpsidePercent || 0) >= 0;
    upsideElem.className = `delta-badge ${uUp ? 'up' : 'down'}`;
    upsideElem.innerText = formatPercent(d.targetUpsidePercent);

    document.getElementById('dd-analystCount').innerText = `${d.numberOfAnalystOpinions || 0} analysts`;

    // Description
    document.getElementById('dd-description').innerText = d.longBusinessSummary || 'No company business description available.';

    // News
    const newsList = document.getElementById('dd-news-list');
    if (d.news && d.news.length > 0) {
      newsList.innerHTML = d.news.map(n => `
        <a href="${n.link}" target="_blank" rel="noopener noreferrer" style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px 12px; text-decoration: none; color: var(--text-primary); transition: background 0.15s;">
          <span style="font-size: 13px; font-weight: 600;">${n.title}</span>
          <span style="font-size: 11px; color: #38bdf8; flex-shrink: 0; margin-left: 12px;">${n.publisher || 'Yahoo Finance'} ↗</span>
        </a>
      `).join('');
    } else {
      newsList.innerHTML = `<div style="font-size: 12px; color: var(--text-muted);">No news available.</div>`;
    }
  } catch (err) {
    console.error('Failed to load deep dive:', err);
  }
}

function closeDeepDiveModal() {
  document.getElementById('deep-dive-modal').classList.remove('open');
}

// ==================== CLEAR & DELETE ====================

async function deleteHolding(symbol) {
  if (!confirm(`Are you sure you want to remove ${symbol} from your portfolio?`)) return;
  try {
    const res = await fetch(`/api/portfolio/holding/${symbol}`, { method: 'DELETE' });
    if (res.ok) {
      showToast(`${symbol} removed`);
      await fetchPortfolioAnalysis();
    }
  } catch (err) {
    showToast(`Failed to remove ${symbol}`, true);
  }
}

async function clearPortfolioConfirm() {
  if (!confirm('Are you sure you want to delete all portfolio holdings?')) return;
  try {
    const res = await fetch('/api/portfolio/clear', { method: 'POST' });
    if (res.ok) {
      showToast('Portfolio cleared');
      await fetchPortfolioAnalysis();
    }
  } catch (err) {
    showToast('Failed to clear portfolio', true);
  }
}

function exportAnalyzedCSV() {
  window.location.href = '/api/portfolio/export';
}

// Attach functions to window object
window.fetchPortfolioAnalysis = fetchPortfolioAnalysis;
window.loadLocalPortfolioCSV = loadLocalPortfolioCSV;
window.openUploadModal = openUploadModal;
window.closeUploadModal = closeUploadModal;
window.handleFileSelect = handleFileSelect;
window.uploadFile = uploadFile;
window.openDeepDive = openDeepDive;
window.closeDeepDiveModal = closeDeepDiveModal;
window.deleteHolding = deleteHolding;
window.clearPortfolioConfirm = clearPortfolioConfirm;
window.exportAnalyzedCSV = exportAnalyzedCSV;
window.sortTable = sortTable;
window.setFilter = setFilter;
window.handleSearchFilter = handleSearchFilter;

