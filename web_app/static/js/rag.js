// RAG page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const similarForm = document.getElementById('similar-form');
    similarForm.addEventListener('submit', handleSimilarSearch);

    const refreshBtn = document.getElementById('refresh-rag-stats');
    refreshBtn.addEventListener('click', loadRagStats);

    const loadPatternsBtn = document.getElementById('load-patterns');
    loadPatternsBtn.addEventListener('click', loadPatterns);

    loadRagStats();
});

async function loadRagStats() {
    try {
        const response = await fetch('/api/rag/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('rag-total').textContent = stats.total_patterns || 0;
            document.getElementById('rag-success').textContent =
                stats.average_success_rate ? (stats.average_success_rate * 100).toFixed(1) + '%' : 'N/A';
            document.getElementById('rag-dim').textContent = stats.embedding_dimension || 'N/A';
        } else {
            document.getElementById('rag-total').textContent = 'N/A';
            document.getElementById('rag-success').textContent = 'N/A';
            document.getElementById('rag-dim').textContent = 'N/A';
        }
    } catch (error) {
        console.error('Failed to load RAG stats:', error);
        document.getElementById('rag-total').textContent = 'Error';
    }
}

async function handleSimilarSearch(event) {
    event.preventDefault();

    const form = event.target;
    const url = form.url.value;
    const limit = form.limit.value;

    const resultsDiv = document.getElementById('similar-results');
    const listDiv = document.getElementById('similar-list');

    resultsDiv.style.display = 'block';
    listDiv.innerHTML = '<p>搜索中...</p>';

    try {
        const response = await fetch('/api/rag/similar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                limit: parseInt(limit)
            })
        });

        const data = await response.json();

        if (data.success && data.similar_patterns && data.similar_patterns.length > 0) {
            listDiv.innerHTML = '';

            data.similar_patterns.forEach((pattern, index) => {
                const patternCard = document.createElement('div');
                patternCard.className = 'item-card';

                const similarity = pattern.confidence || pattern.similarity || 0;
                const successRate = pattern.success_rate || 0;

                patternCard.innerHTML = `
                    <h4>模式 #${index + 1}</h4>
                    <p><strong>相似度:</strong> ${(similarity * 100).toFixed(1)}%</p>
                    <p><strong>成功率:</strong> ${(successRate * 100).toFixed(1)}%</p>
                    ${pattern.url ? `<p><strong>来源:</strong> ${escapeHtml(pattern.url)}</p>` : ''}
                    ${pattern.pattern ? `<p><strong>模式:</strong> <code>${escapeHtml(JSON.stringify(pattern.pattern, null, 2))}</code></p>` : ''}
                `;

                listDiv.appendChild(patternCard);
            });
        } else {
            listDiv.innerHTML = '<p>未找到相似模式</p>';
        }
    } catch (error) {
        console.error('Failed to search similar patterns:', error);
        listDiv.innerHTML = `<p>搜索失败: ${escapeHtml(error.message)}</p>`;
    }
}

async function loadPatterns() {
    const listDiv = document.getElementById('patterns-list');
    listDiv.innerHTML = '<p>加载中...</p>';

    try {
        const response = await fetch('/api/rag/patterns');
        const data = await response.json();

        if (data.success && data.patterns && data.patterns.length > 0) {
            listDiv.innerHTML = '';

            data.patterns.forEach((pattern, index) => {
                const patternCard = document.createElement('div');
                patternCard.className = 'item-card';

                const successRate = pattern.success_rate || 0;

                patternCard.innerHTML = `
                    <h4>最佳模式 #${index + 1}</h4>
                    <p><strong>成功率:</strong> ${(successRate * 100).toFixed(1)}%</p>
                    ${pattern.url ? `<p><strong>URL:</strong> ${escapeHtml(pattern.url)}</p>` : ''}
                    ${pattern.pattern ? `<p><strong>模式:</strong> <code>${escapeHtml(JSON.stringify(pattern.pattern, null, 2))}</code></p>` : ''}
                `;

                listDiv.appendChild(patternCard);
            });
        } else {
            listDiv.innerHTML = '<p>没有可用模式</p>';
        }
    } catch (error) {
        console.error('Failed to load patterns:', error);
        listDiv.innerHTML = `<p>加载失败: ${escapeHtml(error.message)}</p>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
