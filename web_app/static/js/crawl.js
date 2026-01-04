// Crawling page JavaScript

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get stored LLM configuration from localStorage
 * Used for pattern generation and refinement APIs
 */
function getStoredLLMConfig() {
    try {
        const stored = localStorage.getItem('moagent_config');
        if (stored) {
            return JSON.parse(stored);
        }
    } catch (e) {
        console.warn('Failed to load stored config:', e);
    }

    // Return default config if not found
    return {
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        api_key: '',
        api_base_url: 'https://api.openai.com/v1',
        temperature: 0.3,
        max_tokens: 800
    };
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('crawl-form');
    form.addEventListener('submit', handleCrawl);

    const refreshBtn = document.getElementById('refresh-stats');
    refreshBtn.addEventListener('click', loadStorageStats);

    // Pattern Generator Event Listeners
    const toggleBtn = document.getElementById('toggle-generator');
    toggleBtn.addEventListener('click', toggleGenerator);

    const fetchHtmlBtn = document.getElementById('fetch-html-btn');
    fetchHtmlBtn.addEventListener('click', fetchHtmlFromUrl);

    const generateBtn = document.getElementById('generate-pattern-btn');
    generateBtn.addEventListener('click', generatePattern);

    const testBtn = document.getElementById('test-pattern-btn');
    testBtn.addEventListener('click', testPattern);

    const refineBtn = document.getElementById('refine-btn');
    refineBtn.addEventListener('click', showRefineSection);

    const submitRefineBtn = document.getElementById('submit-refine-btn');
    submitRefineBtn.addEventListener('click', refinePattern);

    const applyBtn = document.getElementById('apply-pattern-btn');
    applyBtn.addEventListener('click', applyPatternAndCrawl);

    // Feedback quick buttons
    document.querySelectorAll('.feedback-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const feedback = this.getAttribute('data-feedback');
            document.getElementById('feedback-input').value = feedback;
        });
    });

    loadStorageStats();
});

// =============================================================================
// Crawling Functions
// =============================================================================

async function handleCrawl(event) {
    event.preventDefault();

    const form = event.target;
    const url = form.url.value;
    const mode = form.mode.value;
    const depth = form.depth.value;
    const useRag = form['use-rag'].checked;

    const submitBtn = document.getElementById('submit-btn');
    const resultsSection = document.getElementById('results-section');
    const loadingDiv = document.getElementById('loading');
    const resultsContent = document.getElementById('results-content');
    const errorContent = document.getElementById('error-content');

    // Reset UI
    resultsSection.style.display = 'block';
    loadingDiv.style.display = 'block';
    resultsContent.style.display = 'none';
    errorContent.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = '爬取中...';

    try {
        // Prepare request body
        const requestBody = {
            url: url,
            mode: mode,
            depth: parseInt(depth),
            use_rag: useRag
        };

        // Add pattern if available from LLM generator
        if (currentPattern) {
            requestBody.pattern = currentPattern;
            console.log('Using LLM-generated pattern for crawling');
        }

        const response = await fetch('/api/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        loadingDiv.style.display = 'none';

        if (data.success) {
            displayResults(data);
            resultsContent.style.display = 'block';
            loadStorageStats();

            // Show pattern usage info if applicable
            if (data.pattern_used) {
                const confidence = (data.pattern_confidence * 100).toFixed(1);
                console.log(`✅ Used LLM-generated pattern (confidence: ${confidence}%)`);
            }
        } else {
            displayError(data.error);
            errorContent.style.display = 'block';
        }

    } catch (error) {
        loadingDiv.style.display = 'none';
        displayError(error.message);
        errorContent.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '开始爬取';
    }
}

function displayResults(data) {
    document.getElementById('crawled-count').textContent = data.crawled_count;
    document.getElementById('parsed-count').textContent = data.parsed_count;
    document.getElementById('stored-count').textContent = data.stored_count;

    const itemsList = document.getElementById('items-list');
    itemsList.innerHTML = '';

    if (data.items && data.items.length > 0) {
        data.items.forEach((item, index) => {
            const itemCard = document.createElement('div');
            itemCard.className = 'item-card';

            const title = item.title || item.url || `Item ${index + 1}`;
            const url = item.url || '';
            const content = item.content || item.summary || '';

            itemCard.innerHTML = `
                <h4>${escapeHtml(title)}</h4>
                ${url ? `<p><strong>URL:</strong> ${escapeHtml(url)}</p>` : ''}
                ${content ? `<p>${escapeHtml(content.substring(0, 200))}${content.length > 200 ? '...' : ''}</p>` : ''}
            `;

            itemsList.appendChild(itemCard);
        });
    } else {
        itemsList.innerHTML = '<p>没有找到任何项目</p>';
    }
}

function displayError(error) {
    document.getElementById('error-message').textContent = error || '未知错误';
}

async function loadStorageStats() {
    try {
        const response = await fetch('/api/storage/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('stat-total').textContent = stats.total_items || 0;
            document.getElementById('stat-latest').textContent = stats.recent_count || 0;
        }
    } catch (error) {
        console.error('Failed to load storage stats:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// Pattern Generator Functions
// =============================================================================

let currentPattern = null;
let currentHtml = '';
let currentUrl = '';

function toggleGenerator() {
    const content = document.getElementById('generator-content');
    const isVisible = content.style.display !== 'none';
    content.style.display = isVisible ? 'none' : 'block';
}

async function fetchHtmlFromUrl() {
    const urlInput = document.getElementById('pattern-url');
    const url = urlInput.value.trim();

    if (!url) {
        // Show inline error
        urlInput.style.borderColor = '#d32f2f';
        urlInput.placeholder = '请先输入URL';
        return;
    }

    urlInput.style.borderColor = ''; // Reset border

    const btn = document.getElementById('fetch-html-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '获取中...';

    try {
        // Check if this might be a JavaScript-heavy site
        const useJs = await checkIfNeedsJavaScript(url);

        // Try to fetch HTML via a proxy or CORS workaround
        const apiUrl = use_js
            ? `/api/fetch-html?url=${encodeURIComponent(url)}&use_js=true`
            : `/api/fetch-html?url=${encodeURIComponent(url)}`;

        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error('无法获取HTML');
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById('html-input').value = data.html;
            currentUrl = url;

            // Show success message with details
            btn.textContent = '✅ 获取成功';
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-success');

            // Log details
            console.log('✅ HTML获取成功:');
            console.log(`   - 大小: ${(data.size / 1024).toFixed(1)} KB`);
            console.log(`   - 方法: ${data.method || '未知'}`);
            if (data.truncated) {
                console.warn(`   ⚠️  HTML已截断 (原始大小: ${(data.original_size / 1024).toFixed(1)} KB)`);
            }

            setTimeout(() => {
                btn.textContent = originalText;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-secondary');
            }, 2000);
        } else {
            throw new Error(data.error || '获取失败');
        }
    } catch (error) {
        // Show error message in button
        btn.textContent = '❌ 获取失败';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-danger');

        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-secondary');
        }, 3000);

        // Log error and show manual instructions in console
        console.error('❌ 获取HTML失败:', error.message);
        console.log('');
        console.log('🔧 可能的解决方案:');
        console.log('   1. 检查URL是否正确');
        console.log('   2. 网站可能需要JavaScript渲染，请手动获取');
        console.log('   3. 网站可能有反爬虫机制');
        console.log('');
        console.log('📝 手动获取HTML步骤:');
        console.log('   1. 在浏览器中访问网站');
        console.log('   2. 右键点击页面');
        console.log('   3. 选择"查看网页源代码"');
        console.log('   4. 复制所有HTML (Ctrl+A, Ctrl+C)');
        console.log('   5. 粘贴到上方文本框 (Ctrl+V)');
    } finally {
        btn.disabled = false;
        if (btn.textContent === '获取中...') {
            btn.textContent = originalText;
        }
    }
}

/**
 * Check if URL might need JavaScript rendering
 * Simple heuristic based on URL patterns
 */
async function checkIfNeedsJavaScript(url) {
    // List of sites that typically need JavaScript
    const jsSites = [
        'spa',
        'react',
        'vue',
        'angular',
        'next',
        'nuxt'
    ];

    const urlLower = url.toLowerCase();

    // Check if URL matches JavaScript patterns
    return jsSites.some(pattern => urlLower.includes(pattern));
}

async function generatePattern() {
    const html = document.getElementById('html-input').value.trim();
    const url = document.getElementById('pattern-url').value.trim();

    // Hide previous error
    document.getElementById('generate-error').style.display = 'none';

    if (!html) {
        showError('generate-error', 'generate-error-text', '请先提供HTML内容');
        return;
    }

    const btn = document.getElementById('generate-pattern-btn');
    btn.disabled = true;
    btn.textContent = '🤖 生成中...';

    try {
        // Get LLM config from localStorage
        const llmConfig = getStoredLLMConfig();

        // Log the request for debugging
        console.log('Generating pattern with config:', {
            provider: llmConfig.llm_provider,
            model: llmConfig.llm_model,
            hasApiKey: !!llmConfig.api_key,
            apiBaseUrl: llmConfig.api_base_url
        });

        // Warn if using custom base_url
        if (llmConfig.api_base_url && llmConfig.api_base_url !== 'https://api.openai.com/v1' && llmConfig.api_base_url !== 'https://api.anthropic.com') {
            console.warn('⚠️  Using custom API base URL:', llmConfig.api_base_url);
            console.warn('   Make sure this URL is correct and accessible!');
        }

        const response = await fetch('/api/pattern/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                html: html,
                url: url,
                api_key: llmConfig.api_key || undefined,
                llm_provider: llmConfig.llm_provider || undefined,
                llm_model: llmConfig.llm_model || undefined
            })
        });

        const data = await response.json();

        if (data.success) {
            currentPattern = data.pattern;
            currentHtml = html;
            currentUrl = url;

            displayGeneratedPattern(data.pattern);
            document.getElementById('generated-pattern-section').style.display = 'block';

            // Scroll to pattern section
            document.getElementById('generated-pattern-section').scrollIntoView({ behavior: 'smooth' });
        } else {
            // Show error on page
            let errorMsg = data.error || '未知错误';

            // Add helpful hints for common errors
            if (errorMsg.includes('API key')) {
                errorMsg += '\n\n提示：\n' +
                    '1. 请访问配置页面设置API密钥: http://127.0.0.1:5000/config\n' +
                    '2. 或者创建 configs/.env 文件并添加 OPENAI_API_KEY=sk-your-key-here\n' +
                    '3. 确保API密钥格式正确（以 sk- 开头）';
            } else if (errorMsg.includes('404') || errorMsg.includes('Not Found')) {
                errorMsg += '\n\n⚠️ API端点404错误\n\n' +
                    '可能原因：\n' +
                    '1. API Base URL 配置错误\n' +
                    '2. 代理地址不可访问\n\n' +
                    '解决方案：\n' +
                    '• 访问配置页面: http://127.0.0.1:5000/config\n' +
                    '• 检查 "API Base URL" 设置\n' +
                    '• Anthropic 官方端点: https://api.anthropic.com\n' +
                    '• OpenAI 官方端点: https://api.openai.com/v1\n' +
                    '• 如果使用代理，确保代理地址正确\n\n' +
                    '💡 建议：除非使用代理，否则将 "API Base URL" 留空';
            } else if (errorMsg.includes('connection') || errorMsg.includes('network')) {
                errorMsg += '\n\n提示：请检查网络连接或API地址是否正确';
            } else if (errorMsg.includes('timeout')) {
                errorMsg += '\n\n提示：请求超时，请稍后重试或检查网络';
            }

            showError('generate-error', 'generate-error-text', errorMsg);

            // Log full error for debugging
            console.error('Pattern generation failed:', data);
            if (data.traceback) {
                console.error('Traceback:', data.traceback);
            }
        }
    } catch (error) {
        // Show error on page
        let errorMsg = error.message || '网络请求失败';

        if (error.name === 'TypeError' && errorMsg.includes('fetch')) {
            errorMsg = '无法连接到服务器\n\n请确保Web应用正在运行: http://127.0.0.1:5000';
        }

        showError('generate-error', 'generate-error-text', errorMsg);
        console.error('Request failed:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = '🤖 生成爬取模式';
    }
}

/**
 * Show error message in error box
 * @param {string} errorBoxId - The error box element ID
 * @param {string} errorTextId - The error text element ID
 * @param {string} message - The error message to display
 */
function showError(errorBoxId, errorTextId, message) {
    const errorBox = document.getElementById(errorBoxId);
    const errorText = document.getElementById(errorTextId);

    if (errorBox && errorText) {
        errorText.textContent = message;
        errorBox.style.display = 'block';

        // Scroll to error
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function displayGeneratedPattern(pattern) {
    const display = document.getElementById('pattern-display');

    let html = '<h4>✅ 模式生成成功</h4>';

    // Confidence
    const confidence = pattern.confidence || 0;
    const confidencePercent = (confidence * 100).toFixed(1);
    html += `
        <div class="pattern-field">
            <label>置信度</label>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
            </div>
            <small>${confidencePercent}%</small>
        </div>
    `;

    // List Container
    if (pattern.list_container) {
        html += `
            <div class="pattern-field">
                <label>列表容器</label>
                <code>${pattern.list_container.tag || ''}${pattern.list_container.class ? '.' + pattern.list_container.class : ''}</code>
            </div>
        `;
    }

    // Item Selector
    if (pattern.item_selector) {
        html += `
            <div class="pattern-field">
                <label>项目选择器</label>
                <code>${pattern.item_selector.tag || ''}${pattern.item_selector.class ? '.' + pattern.item_selector.class : ''}</code>
            </div>
        `;
    }

    // Title Selector
    if (pattern.title_selector) {
        html += `
            <div class="pattern-field">
                <label>标题选择器</label>
                <code>${pattern.title_selector.tag || ''}${pattern.title_selector.class ? '.' + pattern.title_selector.class : ''}</code>
            </div>
        `;
    }

    // URL Selector
    if (pattern.url_selector) {
        html += `
            <div class="pattern-field">
                <label>链接选择器</label>
                <code>${pattern.url_selector.tag || ''}${pattern.url_selector.class ? '.' + pattern.url_selector.class : ''}</code>
            </div>
        `;
    }

    // Post Process
    if (pattern.post_process && Object.keys(pattern.post_process).length > 0) {
        html += `
            <div class="pattern-field">
                <label>后处理过滤器</label>
                <pre style="background: white; padding: 10px; border-radius: 4px; overflow-x: auto;">${JSON.stringify(pattern.post_process, null, 2)}</pre>
            </div>
        `;
    }

    // Reasoning
    if (pattern.reasoning) {
        html += `
            <div class="pattern-field">
                <label>推理说明</label>
                <p>${pattern.reasoning}</p>
            </div>
        `;
    }

    display.innerHTML = html;
}

async function testPattern() {
    if (!currentPattern || !currentHtml) {
        showError('test-error', 'test-error-text', '请先生成模式');
        document.getElementById('test-results-section').style.display = 'block';
        return;
    }

    // Hide previous error
    document.getElementById('test-error').style.display = 'none';

    const btn = document.getElementById('test-pattern-btn');
    btn.disabled = true;
    btn.textContent = '🧪 测试中...';

    try {
        // Get LLM config from localStorage (for consistency)
        const llmConfig = getStoredLLMConfig();

        console.log('Testing pattern with config:', {
            provider: llmConfig.llm_provider,
            model: llmConfig.llm_model,
            hasApiKey: !!llmConfig.api_key
        });

        const response = await fetch('/api/pattern/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pattern: currentPattern,
                html: currentHtml,
                base_url: currentUrl,
                api_key: llmConfig.api_key || undefined,
                llm_provider: llmConfig.llm_provider || undefined,
                llm_model: llmConfig.llm_model || undefined
            })
        });

        const data = await response.json();

        if (data.success) {
            displayTestResults(data.items, data.stats);
            document.getElementById('test-results-section').style.display = 'block';
            document.getElementById('test-results-section').scrollIntoView({ behavior: 'smooth' });
        } else {
            let errorMsg = data.error || '未知错误';

            if (errorMsg.includes('API key')) {
                errorMsg += '\n\n提示：请访问配置页面设置API密钥';
            }

            showError('test-error', 'test-error-text', errorMsg);
            document.getElementById('test-results-section').style.display = 'block';
            console.error('Pattern test failed:', data);
        }
    } catch (error) {
        let errorMsg = error.message || '网络请求失败';

        if (error.name === 'TypeError' && errorMsg.includes('fetch')) {
            errorMsg = '无法连接到服务器';
        }

        showError('test-error', 'test-error-text', errorMsg);
        document.getElementById('test-results-section').style.display = 'block';
        console.error('Test request failed:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = '🧪 测试模式';
    }
}

function displayTestResults(items, stats) {
    // Display statistics
    const statsDiv = document.getElementById('test-stats');
    statsDiv.innerHTML = `
        <div class="test-stat">
            <div class="test-stat-value">${stats.items_found || 0}</div>
            <div class="test-stat-label">找到项目</div>
        </div>
        <div class="test-stat">
            <div class="test-stat-value">${stats.items_with_title || 0}</div>
            <div class="test-stat-label">有标题</div>
        </div>
        <div class="test-stat">
            <div class="test-stat-value">${stats.items_with_url || 0}</div>
            <div class="test-stat-label">有链接</div>
        </div>
        <div class="test-stat">
            <div class="test-stat-value">${stats.items_filtered || 0}</div>
            <div class="test-stat-label">已过滤</div>
        </div>
    `;

    // Display items preview
    const previewDiv = document.getElementById('items-preview');
    previewDiv.innerHTML = '';

    const previewItems = items.slice(0, 5);
    if (previewItems.length > 0) {
        previewItems.forEach(item => {
            const div = document.createElement('div');
            div.className = 'item-preview';
            div.innerHTML = `
                <div class="item-preview-title">${escapeHtml(item.title || '无标题')}</div>
                <div class="item-preview-url">${escapeHtml(item.url || '无链接')}</div>
            `;
            previewDiv.appendChild(div);
        });
    } else {
        previewDiv.innerHTML = '<p>未提取到任何项目</p>';
    }
}

function showRefineSection() {
    if (!currentPattern) {
        // Show inline error
        const refineSection = document.getElementById('refine-section');
        refineSection.style.display = 'block';
        refineSection.innerHTML = `
            <div class="error-message-box" style="background: #ffebee; padding: 15px; border-radius: 4px; border-left: 4px solid #d32f2f;">
                <h4 style="color: #d32f2f; margin-top: 0;">❌ 请先生成模式</h4>
                <p>请先在步骤1中提供HTML内容并生成爬取模式，然后再进行优化。</p>
            </div>
        `;
        return;
    }

    document.getElementById('refine-section').style.display = 'block';
    document.getElementById('refine-section').scrollIntoView({ behavior: 'smooth' });
}

async function refinePattern() {
    const feedback = document.getElementById('feedback-input').value.trim();

    // Hide previous error
    document.getElementById('refine-error').style.display = 'none';

    if (!feedback) {
        showError('refine-error', 'refine-error-text', '请提供反馈');
        return;
    }

    if (!currentPattern || !currentHtml) {
        showError('refine-error', 'refine-error-text', '请先生成模式');
        return;
    }

    const btn = document.getElementById('submit-refine-btn');
    btn.disabled = true;
    btn.textContent = '⚡ 优化中...';

    try {
        // Get LLM config from localStorage
        const llmConfig = getStoredLLMConfig();

        console.log('Refining pattern with config:', {
            provider: llmConfig.llm_provider,
            model: llmConfig.llm_model,
            hasApiKey: !!llmConfig.api_key
        });

        const response = await fetch('/api/pattern/refine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_pattern: currentPattern,
                feedback: feedback,
                html: currentHtml,
                api_key: llmConfig.api_key || undefined,
                llm_provider: llmConfig.llm_provider || undefined,
                llm_model: llmConfig.llm_model || undefined
            })
        });

        const data = await response.json();

        if (data.success) {
            displayRefinementResults(data);

            // Update current pattern to refined version
            currentPattern = data.refined_pattern;
        } else {
            let errorMsg = data.error || '未知错误';

            if (errorMsg.includes('API key')) {
                errorMsg += '\n\n提示：请访问配置页面设置API密钥';
            }

            showError('refine-error', 'refine-error-text', errorMsg);
            console.error('Pattern refinement failed:', data);
        }
    } catch (error) {
        let errorMsg = error.message || '网络请求失败';

        if (error.name === 'TypeError' && errorMsg.includes('fetch')) {
            errorMsg = '无法连接到服务器';
        }

        showError('refine-error', 'refine-error-text', errorMsg);
        console.error('Refinement request failed:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ 提交优化';
    }
}

function displayRefinementResults(data) {
    const resultsDiv = document.getElementById('refine-results');
    resultsDiv.style.display = 'block';

    const improvementScore = data.improvement_score || 0;
    const improvementPercent = (improvementScore * 100).toFixed(1);

    let badgeClass = 'improvement-low';
    if (improvementScore > 0.7) badgeClass = 'improvement-high';
    else if (improvementScore > 0.4) badgeClass = 'improvement-medium';

    let html = `
        <h4>⚡ 优化结果</h4>

        <div style="margin: 15px 0;">
            <span class="improvement-badge ${badgeClass}">
                改进分数: ${improvementPercent}%
            </span>
        </div>

        <div class="test-stats">
            <div class="test-stat">
                <div class="test-stat-value">${((data.original_pattern.confidence || 0) * 100).toFixed(1)}%</div>
                <div class="test-stat-label">原始置信度</div>
            </div>
            <div class="test-stat">
                <div class="test-stat-value">${((data.refined_pattern.confidence || 0) * 100).toFixed(1)}%</div>
                <div class="test-stat-label">优化后置信度</div>
            </div>
        </div>

        <div class="pattern-field">
            <label>验证状态</label>
            <p>${data.validation_passed ? '✅ 通过' : '❌ 失败'}</p>
            ${data.validation_errors && data.validation_errors.length > 0 ?
                `<ul>${data.validation_errors.map(e => `<li>${e}</li>`).join('')}</ul>` :
                ''}
        </div>
    `;

    if (data.changes && Object.keys(data.changes).length > 0) {
        html += '<div class="pattern-field"><label>变更内容</label><ul>';
        for (const [field, change] of Object.entries(data.changes)) {
            if (field === 'confidence') {
                html += `<li>置信度: ${((change.original || 0) * 100).toFixed(1)}% → ${((change.refined || 0) * 100).toFixed(1)}%</li>`;
            } else {
                html += `<li>${field}: 已更新</li>`;
            }
        }
        html += '</ul></div>';
    }

    if (data.report) {
        html += `
            <div class="pattern-field">
                <label>详细报告</label>
                <pre style="background: white; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto;">${escapeHtml(data.report)}</pre>
            </div>
        `;
    }

    html += `
        <button class="btn btn-success" onclick="applyRefinedPattern()" style="margin-top: 15px;">
            ✅ 应用优化后的模式
        </button>
    `;

    resultsDiv.innerHTML = html;
}

function applyRefinedPattern() {
    // Show inline success message
    const btn = document.getElementById('apply-pattern-btn');
    const originalText = btn.textContent;

    btn.textContent = '✅ 模式已更新';
    btn.classList.remove('btn-success');
    btn.classList.add('btn-primary');

    setTimeout(() => {
        btn.textContent = originalText;
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-success');
    }, 2000);
}

async function applyPatternAndCrawl() {
    if (!currentPattern) {
        showError('generate-error', 'generate-error-text', '请先生成模式');
        return;
    }

    // Auto-fill URL
    if (currentUrl) {
        document.getElementById('url').value = currentUrl;
    }

    const confidence = (currentPattern.confidence * 100).toFixed(1);

    // Show success message inline
    const btn = document.getElementById('apply-pattern-btn');
    const originalText = btn.textContent;

    btn.textContent = `✅ 已准备 (置信度: ${confidence}%)`;
    btn.classList.remove('btn-success');
    btn.classList.add('btn-primary');

    // Scroll to crawl form
    document.getElementById('crawl-form').scrollIntoView({ behavior: 'smooth' });

    // Show instruction
    const form = document.getElementById('crawl-form');
    const instruction = document.createElement('div');
    instruction.id = 'apply-instruction';
    instruction.style.cssText = 'background: #e8f5e9; padding: 15px; border-radius: 4px; margin-top: 15px; border-left: 4px solid #4caf50;';
    instruction.innerHTML = `
        <h4 style="color: #2e7d32; margin-top: 0;">✅ 模式已准备就绪</h4>
        <p><strong>模式置信度:</strong> ${confidence}%</p>
        <p><strong>目标URL:</strong> ${currentUrl || '请手动填写'}</p>
        <p style="margin-bottom: 0;">现在点击"开始爬取"按钮，系统将自动使用此LLM生成的模式进行爬取。</p>
    `;

    form.insertBefore(instruction, form.firstChild);

    setTimeout(() => {
        btn.textContent = originalText;
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-success');

        // Remove instruction after 10 seconds
        setTimeout(() => {
            const el = document.getElementById('apply-instruction');
            if (el) {
                el.remove();
            }
        }, 10000);
    }, 2000);
}
