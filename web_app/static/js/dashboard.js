// Dashboard page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const refreshBtn = document.getElementById('refresh-dashboard');
    refreshBtn.addEventListener('click', loadDashboard);

    const loadItemsBtn = document.getElementById('load-items');
    loadItemsBtn.addEventListener('click', loadRecentItems);

    loadDashboard();
    addSystemLogs();
});

async function loadDashboard() {
    await Promise.all([
        loadSystemInfo(),
        loadStorageStats(),
        loadRagStats(),
        checkFeatureStatus()
    ]);
}

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system/info');
        const data = await response.json();

        if (data.success) {
            const features = data.info.features || {};
            updateFeatureStatus(features);
        }
    } catch (error) {
        console.error('Failed to load system info:', error);
    }
}

async function loadStorageStats() {
    try {
        const response = await fetch('/api/storage/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('dash-total').textContent = stats.total_items || 0;
        }
    } catch (error) {
        console.error('Failed to load storage stats:', error);
        document.getElementById('dash-total').textContent = 'Error';
    }
}

async function loadRagStats() {
    try {
        const response = await fetch('/api/rag/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('dash-rag').textContent = stats.total_patterns || 0;
            const successRate = stats.average_success_rate || 0;
            document.getElementById('dash-success').textContent = (successRate * 100).toFixed(1) + '%';
        } else {
            document.getElementById('dash-rag').textContent = 'N/A';
            document.getElementById('dash-success').textContent = 'N/A';
        }
    } catch (error) {
        console.error('Failed to load RAG stats:', error);
        document.getElementById('dash-rag').textContent = 'N/A';
    }
}

function updateFeatureStatus(features) {
    const statusMap = {
        'crawling': 'status-crawling',
        'parsing': 'status-parsing',
        'storage': 'status-storage',
        'rag': 'status-rag',
        'multi_agent': 'status-multiagent',
        'notify': 'status-notify'
    };

    for (const [key, elementId] of Object.entries(statusMap)) {
        const element = document.getElementById(elementId);
        if (element) {
            const enabled = features[key];
            element.textContent = enabled ? '✓ 活跃' : '✗ 不可用';
            element.className = 'status ' + (enabled ? 'active' : 'inactive');
        }
    }
}

async function checkFeatureStatus() {
    // This is already handled by loadSystemInfo
    // Kept for potential additional checks
}

async function loadRecentItems() {
    const itemsDiv = document.getElementById('recent-items');
    itemsDiv.innerHTML = '<p>加载中...</p>';

    try {
        const response = await fetch('/api/storage/items?limit=10');
        const data = await response.json();

        if (data.success && data.items && data.items.length > 0) {
            itemsDiv.innerHTML = '';

            data.items.forEach((item, index) => {
                const itemCard = document.createElement('div');
                itemCard.className = 'item-card';

                const title = item.title || item.url || `Item ${index + 1}`;
                const url = item.url || '';
                const timestamp = item.timestamp || '';

                itemCard.innerHTML = `
                    <h4>${escapeHtml(title)}</h4>
                    ${url ? `<p><strong>URL:</strong> ${escapeHtml(url)}</p>` : ''}
                    ${timestamp ? `<p><strong>时间:</strong> ${escapeHtml(timestamp)}</p>` : ''}
                `;

                itemsDiv.appendChild(itemCard);
            });
        } else {
            itemsDiv.innerHTML = '<p>没有找到项目</p>';
        }
    } catch (error) {
        console.error('Failed to load recent items:', error);
        itemsDiv.innerHTML = `<p>加载失败: ${escapeHtml(error.message)}</p>`;
    }
}

function addSystemLogs() {
    const logsContainer = document.getElementById('system-logs');

    const now = new Date();
    const timestamp = now.toISOString().replace('T', ' ').substring(0, 19);

    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.innerHTML = `
        <span class="log-time">${timestamp}</span>
        <span class="log-level INFO">INFO</span>
        <span class="log-message">监控面板已加载</span>
    `;

    logsContainer.insertBefore(logEntry, logsContainer.firstChild);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
