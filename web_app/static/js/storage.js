// Storage page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    loadStatistics();
    loadArticles();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('refresh-btn').addEventListener('click', loadArticles);
    document.getElementById('limit-select').addEventListener('change', loadArticles);
    document.getElementById('source-filter').addEventListener('change', filterArticles);
    document.getElementById('export-btn').addEventListener('click', exportArticles);
}

async function loadStatistics() {
    try {
        const response = await fetch('/api/storage/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('stat-total').textContent = stats.total_items || 0;
            document.getElementById('stat-sources').textContent = Object.keys(stats.sources || {}).length;
            document.getElementById('stat-recent').textContent = stats.last_updated ? '刚刚' : '无';

            // Update source filter
            const sourceFilter = document.getElementById('source-filter');
            sourceFilter.innerHTML = '<option value="">全部来源</option>';
            Object.keys(stats.sources || {}).forEach(source => {
                const option = document.createElement('option');
                option.value = source;
                option.textContent = `${source} (${stats.sources[source]})`;
                sourceFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

let allArticles = [];

async function loadArticles() {
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('empty-state');
    const articlesGrid = document.getElementById('articles-grid');
    const limit = document.getElementById('limit-select').value;

    // Show loading
    loading.style.display = 'block';
    emptyState.style.display = 'none';
    articlesGrid.innerHTML = '';

    try {
        const limitParam = limit === 'all' ? 10000 : parseInt(limit);
        const response = await fetch(`/api/storage/items?limit=${limitParam}`);
        const data = await response.json();

        loading.style.display = 'none';

        if (data.success && data.items.length > 0) {
            allArticles = data.items;
            displayArticles(allArticles);
        } else {
            emptyState.style.display = 'block';
        }
    } catch (error) {
        loading.style.display = 'none';
        console.error('Failed to load articles:', error);
        alert('加载失败: ' + error.message);
    }
}

function displayArticles(articles) {
    const articlesGrid = document.getElementById('articles-grid');
    articlesGrid.innerHTML = '';

    articles.forEach(article => {
        const card = createArticleCard(article);
        articlesGrid.appendChild(card);
    });
}

function createArticleCard(article) {
    const card = document.createElement('div');
    card.className = 'article-card';

    const title = article.title || '无标题';
    const content = article.content || '无内容';
    const url = article.url || '#';
    const source = article.source || 'unknown';
    const timestamp = article.timestamp || article.created_at || '未知时间';

    // Format date
    const date = new Date(timestamp);
    const dateStr = isNaN(date) ? timestamp : date.toLocaleString('zh-CN');

    card.innerHTML = `
        <div class="article-header">
            <h3 class="article-title">${escapeHtml(title)}</h3>
        </div>
        <div class="article-meta">
            <span class="article-source">${escapeHtml(source)}</span>
            <span>${dateStr}</span>
        </div>
        <div class="article-content">
            ${escapeHtml(content.substring(0, 200))}${content.length > 200 ? '...' : ''}
        </div>
        <div class="article-footer">
            <a href="${escapeHtml(url)}" target="_blank" class="article-link">查看原文 →</a>
            <span class="article-date">${dateStr}</span>
        </div>
    `;

    return card;
}

function filterArticles() {
    const source = document.getElementById('source-filter').value;
    const filtered = source ? allArticles.filter(a => a.source === source) : allArticles;
    displayArticles(filtered);
}

function exportArticles() {
    if (allArticles.length === 0) {
        alert('没有可导出的数据');
        return;
    }

    const dataStr = JSON.stringify(allArticles, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `moagent_articles_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
