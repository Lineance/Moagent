// Configuration page JavaScript

// Configuration presets
const PRESETS = {
    'openai-mini': {
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        api_base_url: 'https://api.openai.com/v1',
        temperature: 0.3,
        max_tokens: 800
    },
    'openai-full': {
        llm_provider: 'openai',
        llm_model: 'gpt-4o',
        api_base_url: 'https://api.openai.com/v1',
        temperature: 0.3,
        max_tokens: 2000
    },
    'anthropic': {
        llm_provider: 'anthropic',
        llm_model: 'claude-3-5-sonnet-20241022',
        api_base_url: 'https://api.anthropic.com',
        temperature: 0.3,
        max_tokens: 1000
    },
    'custom': {
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        api_base_url: '',
        temperature: 0.3,
        max_tokens: 800
    }
};

document.addEventListener('DOMContentLoaded', function() {
    loadCurrentConfig();
    loadSystemConfig();

    // LLM config form
    const llmForm = document.getElementById('llm-config-form');
    llmForm.addEventListener('submit', saveLLMConfig);

    // System config form
    const systemForm = document.getElementById('system-config-form');
    systemForm.addEventListener('submit', saveSystemConfig);

    // Test config button
    const testBtn = document.getElementById('test-config');
    testBtn.addEventListener('click', testLLMConfig);
});

function loadCurrentConfig() {
    const config = getStoredConfig();
    displayCurrentConfig(config);
    fillForm(config);
}

function getStoredConfig() {
    const stored = localStorage.getItem('moagent_config');
    if (stored) {
        return JSON.parse(stored);
    }
    return {
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        api_key: '',
        api_base_url: 'https://api.openai.com/v1',
        temperature: 0.3,
        max_tokens: 800
    };
}

function displayCurrentConfig(config) {
    const container = document.getElementById('current-config');

    const hasApiKey = !!config.api_key;
    const maskedKey = config.api_key ?
        config.api_key.substring(0, 7) + '...' + config.api_key.substring(config.api_key.length - 4) :
        '未设置';

    container.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div>
                <p><strong>提供商:</strong> ${config.llm_provider || 'N/A'}</p>
                <p><strong>模型:</strong> ${config.llm_model || 'N/A'}</p>
                <p><strong>API密钥:</strong> <span class="status-badge ${hasApiKey ? 'valid' : 'invalid'}">${maskedKey}</span></p>
            </div>
            <div>
                <p><strong>API地址:</strong> ${config.api_base_url || '默认'}</p>
                <p><strong>温度:</strong> ${config.temperature || 0.3}</p>
                <p><strong>最大Token:</strong> ${config.max_tokens || 800}</p>
            </div>
        </div>
    `;
}

function fillForm(config) {
    document.getElementById('llm_provider').value = config.llm_provider || 'openai';
    document.getElementById('llm_model').value = config.llm_model || 'gpt-4o-mini';
    document.getElementById('api_key').value = config.api_key || '';
    document.getElementById('api_base_url').value = config.api_base_url || '';
    document.getElementById('temperature').value = config.temperature || 0.3;
    document.getElementById('max_tokens').value = config.max_tokens || 800;
}

function loadSystemConfig() {
    const config = getStoredConfig();

    document.getElementById('enable_rag').checked = config.enable_rag || false;
    document.getElementById('use_llm_parsing').checked = config.use_llm_parsing || false;
    document.getElementById('log_level').value = config.log_level || 'INFO';
    document.getElementById('max_concurrent').value = config.max_concurrent || 5;
    document.getElementById('timeout').value = config.timeout || 30;
}

async function saveLLMConfig(event) {
    event.preventDefault();

    const form = event.target;
    const config = {
        llm_provider: form.llm_provider.value,
        llm_model: form.llm_model.value,
        api_key: form.api_key.value,
        api_base_url: form.api_base_url.value,
        temperature: parseFloat(form.temperature.value),
        max_tokens: parseInt(form.max_tokens.value),
        // Preserve system config
        enable_rag: document.getElementById('enable_rag').checked,
        use_llm_parsing: document.getElementById('use_llm_parsing').checked,
        log_level: document.getElementById('log_level').value,
        max_concurrent: parseInt(document.getElementById('max_concurrent').value),
        timeout: parseInt(document.getElementById('timeout').value)
    };

    // Save to localStorage
    localStorage.setItem('moagent_config', JSON.stringify(config));

    // Show success message
    showNotification('LLM配置已保存！', 'success');

    // Update display
    displayCurrentConfig(config);
}

async function saveSystemConfig(event) {
    event.preventDefault();

    const form = event.target;
    const existingConfig = getStoredConfig();

    const config = {
        ...existingConfig,
        enable_rag: document.getElementById('enable_rag').checked,
        use_llm_parsing: document.getElementById('use_llm_parsing').checked,
        log_level: document.getElementById('log_level').value,
        max_concurrent: parseInt(document.getElementById('max_concurrent').value),
        timeout: parseInt(document.getElementById('timeout').value)
    };

    // Save to localStorage
    localStorage.setItem('moagent_config', JSON.stringify(config));

    // Show success message
    showNotification('系统配置已保存！', 'success');

    if (config.enable_rag) {
        showNotification('RAG系统已启用，请重启应用以加载RAG模块', 'warning');
    }
}

function applyPreset(presetName) {
    const preset = PRESETS[presetName];
    if (!preset) {
        showNotification('未找到预设配置', 'error');
        return;
    }

    document.getElementById('llm_provider').value = preset.llm_provider;
    document.getElementById('llm_model').value = preset.llm_model;
    document.getElementById('api_base_url').value = preset.api_base_url;
    document.getElementById('temperature').value = preset.temperature;
    document.getElementById('max_tokens').value = preset.max_tokens;

    showNotification(`已应用预设: ${presetName}`, 'success');
}

async function testLLMConfig() {
    const config = getStoredConfig();

    if (!config.api_key) {
        showNotification('请先设置API密钥', 'error');
        return;
    }

    const testBtn = document.getElementById('test-config');
    const resultDiv = document.getElementById('test-result');

    testBtn.disabled = true;
    testBtn.textContent = '测试中...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<p>正在测试LLM连接...</p>';

    try {
        const response = await fetch('/api/config/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                llm_provider: config.llm_provider,
                llm_model: config.llm_model,
                api_key: config.api_key,
                api_base_url: config.api_base_url
            })
        });

        const data = await response.json();

        if (data.success) {
            resultDiv.innerHTML = `
                <div style="background: #d1fae5; padding: 15px; border-radius: 8px; border-left: 4px solid var(--success-color);">
                    <h4 style="color: var(--success-color); margin-bottom: 10px;">✅ 测试成功！</h4>
                    <p><strong>响应时间:</strong> ${data.latency || 'N/A'}</p>
                    <p><strong>模型:</strong> ${data.model || config.llm_model}</p>
                    <p><strong>测试响应:</strong> ${data.response || 'OK'}</p>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div style="background: #fee; padding: 15px; border-radius: 8px; border-left: 4px solid var(--danger-color);">
                    <h4 style="color: var(--danger-color); margin-bottom: 10px;">❌ 测试失败</h4>
                    <p>${data.error || '未知错误'}</p>
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div style="background: #fee; padding: 15px; border-radius: 8px; border-left: 4px solid var(--danger-color);">
                <h4 style="color: var(--danger-color); margin-bottom: 10px;">❌ 测试失败</h4>
                <p>${escapeHtml(error.message)}</p>
            </div>
        `;
    } finally {
        testBtn.disabled = false;
        testBtn.textContent = '测试连接';
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#d1fae5' : type === 'error' ? '#fee' : '#dbeafe'};
        color: ${type === 'success' ? '#065f46' : type === 'error' ? '#991b1b' : '#1e40af'};
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
