// Index page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadSystemInfo();
    loadQuickStats();
});

async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system/info');
        const data = await response.json();

        if (data.success) {
            document.getElementById('version').textContent = data.info.version || '1.0.0';

            const featuresList = document.getElementById('features');
            featuresList.innerHTML = '';

            const features = data.info.features;
            for (const [key, enabled] of Object.entries(features)) {
                const li = document.createElement('li');
                li.textContent = `${enabled ? '✓' : '✗'} ${key}`;
                featuresList.appendChild(li);
            }
        }
    } catch (error) {
        console.error('Failed to load system info:', error);
        document.getElementById('version').textContent = '加载失败';
    }
}

async function loadQuickStats() {
    try {
        // Load storage stats
        const storageResponse = await fetch('/api/storage/stats');
        const storageData = await storageResponse.json();

        if (storageData.success) {
            const stats = storageData.stats;
            document.getElementById('total-crawled').textContent = stats.total_items || 0;
        }

        // Load RAG stats
        const ragResponse = await fetch('/api/rag/stats');
        const ragData = await ragResponse.json();

        if (ragData.success) {
            const stats = ragData.stats;
            document.getElementById('rag-patterns').textContent = stats.total_patterns || 0;
        } else {
            document.getElementById('rag-patterns').textContent = 'N/A';
        }

        // Storage size (simplified)
        document.getElementById('storage-size').textContent = 'MB';

    } catch (error) {
        console.error('Failed to load stats:', error);
        document.getElementById('total-crawled').textContent = '-';
        document.getElementById('rag-patterns').textContent = '-';
    }
}
