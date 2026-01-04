// Multi-Agent page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('ma-form');
    form.addEventListener('submit', handleMultiAgentExecute);
});

async function handleMultiAgentExecute(event) {
    event.preventDefault();

    const form = event.target;
    const url = form.url.value;
    const keywords = form.keywords.value.split(',').map(k => k.trim()).filter(k => k);
    const depth = form.depth.value;
    const enableOptimization = form.enable_optimization.checked;
    const enableRag = form.enable_rag.checked;

    const submitBtn = document.getElementById('ma-submit-btn');
    const resultsSection = document.getElementById('ma-results');
    const loadingDiv = document.getElementById('ma-loading');
    const resultsContent = document.getElementById('ma-results-content');
    const errorDiv = document.getElementById('ma-error');

    // Reset UI
    resultsSection.style.display = 'block';
    loadingDiv.style.display = 'block';
    resultsContent.style.display = 'none';
    errorDiv.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = '执行中...';

    const startTime = Date.now();

    // 获取LLM配置
    const llmConfig = getLLMConfig();

    try {
        const response = await fetch('/api/multi-agent/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                keywords: keywords,
                depth: parseInt(depth),
                enable_optimization: enableOptimization,
                enable_rag: enableRag,
                llm_config: llmConfig  // 传递LLM配置
            })
        });

        const data = await response.json();
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);

        loadingDiv.style.display = 'none';

        if (data.success) {
            displayMultiAgentResults(data, elapsed);
            resultsContent.style.display = 'block';
        } else {
            displayMultiAgentError(data.error);
            errorDiv.style.display = 'block';
        }

    } catch (error) {
        loadingDiv.style.display = 'none';
        displayMultiAgentError(error.message);
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '启动工作流';
    }
}

function displayMultiAgentResults(data, elapsed) {
    const result = data.result || {};

    // 获取workflow_state中的所有Agent结果
    const workflowState = result.workflow_state || {};

    document.getElementById('ma-status').textContent = '成功';
    document.getElementById('ma-url').textContent = data.url || 'N/A';
    document.getElementById('ma-time').textContent = `${elapsed}秒`;

    const agentDetails = document.getElementById('agent-details');
    agentDetails.innerHTML = '';

    // 1. Explorer Agent 详细结果 (优先从workflow_state读取)
    const explorationResult = workflowState.exploration_result || result.exploration_result;
    if (explorationResult) {
        const explorerCard = createAgentCard({
            icon: '🔍',
            name: 'Explorer Agent',
            status: 'completed',
            details: [
                { label: '置信度', value: `${((explorationResult.confidence || 0) * 100).toFixed(1)}%` },
                { label: '探索阶段', value: explorationResult.phase || 'N/A' }
            ],
            sections: []
        });

        // 检测到的特征
        if (explorationResult.detected_features) {
            const features = explorationResult.detected_features;
            const featureList = Object.entries(features).map(([k, v]) => `${k}: ${v}`).join(', ');
            addSection(explorerCard, '检测特征', featureList);
        }

        // 模式建议
        if (explorationResult.pattern_suggestion) {
            const pattern = explorationResult.pattern_suggestion;
            let patternHtml = '<div class="pattern-box">';
            if (pattern.list_container) patternHtml += `<p><strong>列表容器:</strong> <code>${pattern.list_container}</code></p>`;
            if (pattern.item_selector) patternHtml += `<p><strong>项目选择器:</strong> <code>${pattern.item_selector}</code></p>`;
            if (pattern.title) patternHtml += `<p><strong>标题:</strong> <code>${pattern.title}</code></p>`;
            if (pattern.link) patternHtml += `<p><strong>链接:</strong> <code>${pattern.link}</code></p>`;
            if (pattern.content) patternHtml += `<p><strong>内容:</strong> <code>${pattern.content}</code></p>`;
            patternHtml += '</div>';
            addSection(explorerCard, '爬取模式建议', patternHtml);
        }

        // 发现的链接
        if (explorationResult.discovered_links && explorationResult.discovered_links.length > 0) {
            addSection(explorerCard, '发现链接数量', explorationResult.discovered_links.length);
        }

        // 分页信息
        if (explorationResult.pagination) {
            const pagination = explorationResult.pagination;
            let paginationInfo = '';
            if (pagination.detected) paginationInfo += `已检测分页`;
            if (pagination.next_page) paginationInfo += ` | 下一页: ${pagination.next_page}`;
            if (paginationInfo) addSection(explorerCard, '分页信息', paginationInfo);
        }

        agentDetails.appendChild(explorerCard);
    }

    // 2. Optimizer Agent 详细结果 (优先从workflow_state读取)
    const optimizationResult = workflowState.optimization_result || result.optimization_result;
    if (optimizationResult) {
        const optimizerCard = createAgentCard({
            icon: '⚡',
            name: 'Optimizer Agent',
            status: 'completed',
            details: [
                { label: '优化状态', value: optimizationResult.optimized ? '已优化' : '未优化' }
            ],
            sections: []
        });

        // RAG检索结果
        if (optimizationResult.rag_patterns && optimizationResult.rag_patterns.length > 0) {
            let ragHtml = '<ul>';
            optimizationResult.rag_patterns.slice(0, 3).forEach(pattern => {
                ragHtml += `<li>相似度: ${(pattern.similarity * 100).toFixed(1)}% - ${pattern.url || 'Unknown'}</li>`;
            });
            ragHtml += '</ul>';
            addSection(optimizerCard, 'RAG检索历史模式', ragHtml);
        }

        // 优化建议
        if (optimizationResult.suggestions) {
            addSection(optimizerCard, '优化建议', optimizationResult.suggestions.join(', '));
        }

        // 优化后的模式
        if (optimizationResult.optimized_pattern) {
            const pattern = optimizationResult.optimized_pattern;
            let patternHtml = '<div class="pattern-box">';
            if (pattern.list_container) patternHtml += `<p><strong>列表容器:</strong> <code>${pattern.list_container}</code></p>`;
            if (pattern.item_selector) patternHtml += `<p><strong>项目选择器:</strong> <code>${pattern.item_selector}</code></p>`;
            if (pattern.title) patternHtml += `<p><strong>标题:</strong> <code>${pattern.title}</code></p>`;
            if (pattern.link) patternHtml += `<p><strong>链接:</strong> <code>${pattern.link}</code></p>`;
            patternHtml += '</div>';
            addSection(optimizerCard, '优化后模式', patternHtml);
        }

        agentDetails.appendChild(optimizerCard);
    }

    // 3. Crawler Agent 详细结果 (优先从workflow_state读取)
    const crawlingResult = workflowState.crawling_result || result.crawling_result;
    if (crawlingResult) {
        const fulltextCount = crawlingResult.articles_with_fulltext || 0;
        const fulltextEnabled = crawlingResult.fulltext_enabled || false;
        const skipReason = crawlingResult.skip_reason || '';

        const crawlerCard = createAgentCard({
            icon: '🕷️',
            name: 'Crawler Agent',
            status: 'completed',
            details: [
                { label: '爬取数量', value: crawlingResult.count || 0 },
                { label: '全文提取', value: fulltextEnabled ? `已启用 (${fulltextCount}篇)` : '未启用' },
                { label: '使用模式', value: crawlingResult.pattern_used ? '已应用' : '默认' }
            ],
            sections: []
        });

        // 使用的模式
        if (crawlingResult.pattern_used) {
            const pattern = crawlingResult.pattern_used;
            let patternHtml = '<div class="pattern-box">';
            if (pattern.list_container) patternHtml += `<p><strong>列表容器:</strong> <code>${pattern.list_container}</code></p>`;
            if (pattern.item_selector) patternHtml += `<p><strong>项目选择器:</strong> <code>${pattern.item_selector}</code></p>`;
            patternHtml += '</div>';
            addSection(crawlerCard, '使用模式', patternHtml);
        }

        // 全文提取统计或跳过原因
        if (fulltextEnabled) {
            const percentage = crawlingResult.count > 0
                ? ((fulltextCount / crawlingResult.count) * 100).toFixed(0)
                : 0;

            let fulltextHtml = '<div style="display: flex; align-items: center; gap: 15px;">';
            fulltextHtml += `<div style="flex: 1;">`;
            fulltextHtml += `<div style="display: flex; justify-content: space-between; margin-bottom: 5px;">`;
            fulltextHtml += `<span>全文提取成功率</span>`;
            fulltextHtml += `<span style="font-weight: bold; color: ${percentage > 80 ? '#4caf50' : percentage > 50 ? '#ff9800' : '#f44336'};">${percentage}%</span>`;
            fulltextHtml += `</div>`;
            fulltextHtml += `<div style="width: 100%; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">`;
            fulltextHtml += `<div style="width: ${percentage}%; height: 100%; background: linear-gradient(90deg, var(--primary-color), var(--success-color)); transition: width 0.3s;"></div>`;
            fulltextHtml += `</div>`;
            fulltextHtml += `<p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">`;
            fulltextHtml += `${fulltextCount} / ${crawlingResult.count} 篇文章提取到完整内容`;
            fulltextHtml += `</p>`;
            fulltextHtml += `</div>`;
            fulltextHtml += `</div>`;

            addSection(crawlerCard, '📄 全文提取', fulltextHtml);
        } else if (skipReason) {
            // 显示为什么跳过全文提取
            let skipHtml = '<div style="background: #fff3e0; padding: 12px; border-radius: 4px; border-left: 4px solid #ff9800;">';
            skipHtml += '<p style="margin: 0; color: #e65100; font-weight: 500;">⚠️ 全文提取未启用</p>';

            if (skipReason.includes('No API key')) {
                skipHtml += '<p style="margin: 8px 0 0 0; font-size: 13px; color: #666;">';
                skipHtml += '原因: 未配置API密钥<br>';
                skipHtml += '解决: 请访问 <a href="/config" style="color: #1976d2;">配置页面</a> 设置OpenAI或Anthropic API密钥';
                skipHtml += '</p>';
            } else if (skipReason.includes('Extraction failed')) {
                skipHtml += `<p style="margin: 8px 0 0 0; font-size: 13px; color: #666;">原因: ${skipReason}</p>`;
                skipHtml += '<p style="margin: 5px 0 0 0; font-size: 12px; color: #888;">将使用列表页提取的内容</p>';
            } else {
                skipHtml += `<p style="margin: 8px 0 0 0; font-size: 13px; color: #666;">${skipReason}</p>`;
            }

            skipHtml += '</div>';
            addSection(crawlerCard, '⚠️ 全文提取状态', skipHtml);
        }

        // 数据库保存状态
        const dbSave = crawlingResult.database_save;
        if (dbSave) {
            let dbHtml = '';
            if (dbSave.success) {
                dbHtml = '<div style="background: #e8f5e9; padding: 12px; border-radius: 4px; border-left: 4px solid #4caf50;">';
                dbHtml += '<p style="margin: 0; color: #2e7d32; font-weight: 500; display: flex; align-items: center; gap: 8px;">';
                dbHtml += '✅ 数据已保存到数据库';
                dbHtml += '</p>';
                dbHtml += '<div style="margin-top: 10px; display: flex; gap: 20px; font-size: 13px;">';
                dbHtml += `<div><strong>新保存:</strong> <span style="color: #2e7d32;">${dbSave.new_items_saved}</span> 条</div>`;
                if (dbSave.duplicates_skipped > 0) {
                    dbHtml += `<div><strong>重复跳过:</strong> <span style="color: #f57c00;">${dbSave.duplicates_skipped}</span> 条</div>`;
                }
                dbHtml += `<div><strong>总计:</strong> ${dbSave.total_items} 条</div>`;
                dbHtml += '</div>';
                dbHtml += '</div>';
            } else {
                dbHtml = '<div style="background: #ffebee; padding: 12px; border-radius: 4px; border-left: 4px solid #f44336;">';
                dbHtml += '<p style="margin: 0; color: #c62828; font-weight: 500;">❌ 数据库保存失败</p>';
                if (dbSave.error) {
                    dbHtml += `<p style="margin: 8px 0 0 0; font-size: 12px; color: #666;">错误: ${dbSave.error}</p>`;
                }
                dbHtml += '</div>';
            }
            addSection(crawlerCard, '💾 数据库保存', dbHtml);
        }

        agentDetails.appendChild(crawlerCard);
    }

    // 4. Analyst Agent 详细结果 (优先从workflow_state读取)
    const analysisResult = workflowState.analysis_result || result.analysis_result;
    if (analysisResult) {
        const summary = analysisResult.summary || {};
        const analystCard = createAgentCard({
            icon: '📊',
            name: 'Analyst Agent',
            status: 'completed',
            details: [
                { label: '总项目', value: summary.total_items || 0 },
                { label: '保留项目', value: summary.kept_items || 0 },
                { label: '过滤项目', value: summary.filtered_items || 0 },
                { label: '平均质量', value: `${((summary.avg_quality || 0) * 100).toFixed(1)}%` }
            ],
            sections: []
        });

        // 分类统计
        if (summary.categories && Object.keys(summary.categories).length > 0) {
            const categoryHtml = Object.entries(summary.categories)
                .map(([cat, count]) => `<span class="category-tag">${cat}: ${count}</span>`)
                .join(' ');
            addSection(analystCard, '内容分类', categoryHtml);
        }

        // 质量分析
        if (analysisResult.analyzed_items && analysisResult.analyzed_items.length > 0) {
            const highQuality = analysisResult.analyzed_items.filter(item => (item.quality_score || 0) > 0.8).length;
            addSection(analystCard, '高质量项目', `${highQuality} / ${analysisResult.analyzed_items.length}`);
        }

        agentDetails.appendChild(analystCard);
    }

    // 5. Validator Agent 详细结果 (优先从workflow_state读取)
    const validationResult = workflowState.validation_result || result.validation_result;
    if (validationResult) {
        const validatorCard = createAgentCard({
            icon: '✅',
            name: 'Validator Agent',
            status: 'completed',
            details: [
                { label: '验证总数', value: validationResult.total_validated || 0 },
                { label: '有效项目', value: validationResult.valid_items?.length || 0 },
                { label: '无效项目', value: validationResult.invalid_items || 0 },
                { label: '验证分数', value: `${((validationResult.validation_score || 0) * 100).toFixed(1)}%` }
            ],
            sections: []
        });

        // 验证问题
        if (validationResult.issues && Object.keys(validationResult.issues).length > 0) {
            const issuesHtml = Object.entries(validationResult.issues)
                .filter(([_, count]) => count > 0)
                .map(([issue, count]) => `<span class="issue-tag">${issue}: ${count}</span>`)
                .join(' ');
            if (issuesHtml) {
                addSection(validatorCard, '发现问题', issuesHtml);
            }
        }

        agentDetails.appendChild(validatorCard);
    }

    // 6. 最终结果汇总 (优先使用workflow_state中的items)
    const finalResult = result.final_result || {};

    // 如果workflow_state中有validation_result，使用验证后的items
    const validItems = workflowState.validation_result?.valid_items ||
                      workflowState.crawling_result?.items ||
                      finalResult.items ||
                      [];

    if (validItems.length > 0 || finalResult.total_items > 0) {
        const finalCard = document.createElement('div');
        finalCard.className = 'item-card';
        finalCard.style.borderLeftColor = 'var(--success-color)';
        finalCard.style.borderLeftWidth = '4px';

        let finalHtml = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h4 style="margin: 0;">🎯 最终结果汇总</h4>
                <span class="status-badge status-success">成功</span>
            </div>
            <div class="result-summary">
                <div class="summary-item">
                    <div class="summary-value">${validItems.length || finalResult.total_items || 0}</div>
                    <div class="summary-label">有效项目</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${finalResult.new_items || validItems.length || 0}</div>
                    <div class="summary-label">新增项目</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${((finalResult.quality_score || 0) * 100).toFixed(0)}%</div>
                    <div class="summary-label">质量分数</div>
                </div>
            </div>
        `;

        // 工作流日志
        if (finalResult.workflow_log && finalResult.workflow_log.length > 0) {
            finalHtml += '<div style="margin-top: 15px;"><h5 style="margin-bottom: 10px;">📝 执行日志</h5>';
            finalHtml += '<div style="max-height: 200px; overflow-y: auto; background: #f5f5f5; padding: 10px; border-radius: 4px;">';
            finalResult.workflow_log.forEach(log => {
                const icon = log.success ? '✅' : '❌';
                const quality = log.quality_score ? ` (质量: ${((log.quality_score || 0) * 100).toFixed(1)}%)` : '';
                finalHtml += `<div style="padding: 5px 0; border-bottom: 1px solid #ddd;">${icon} ${log.phase}${quality}</div>`;
            });
            finalHtml += '</div></div>';
        }

        finalCard.innerHTML = finalHtml;
        agentDetails.appendChild(finalCard);
    }

    // 7. 爬取内容详情显示
    if (validItems.length > 0) {
        const itemsCard = document.createElement('div');
        itemsCard.className = 'item-card';
        itemsCard.style.marginTop = '20px';
        itemsCard.style.borderLeft = '4px solid var(--primary-color)';

        let itemsHtml = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h4 style="margin: 0;">📄 爬取内容详情</h4>
                <span class="status-badge status-info">显示前 ${Math.min(validItems.length, 10)} 条</span>
            </div>
        `;

        // 显示前10条
        itemsHtml += '<div style="max-height: 600px; overflow-y: auto;">';
        validItems.slice(0, 10).forEach((item, index) => {
            const title = item.title || item.get?.('title') || '无标题';
            const url = item.url || item.link || item.get?.('url') || item.get?.('link') || '#';
            const content = item.content || item.get?.('content') || '';
            const date = item.date || item.published_date || item.get?.('date') || '';

            itemsHtml += `
                <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; margin-bottom: 10px; border-left: 3px solid var(--primary-color);">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <h5 style="margin: 0 0 5px 0; color: var(--primary-color);">
                                ${index + 1}. ${title}
                            </h5>
                            ${url !== '#' ? `<p style="margin: 0; font-size: 12px; color: #666;"><a href="${url}" target="_blank" style="color: #1976d2; text-decoration: none;">${url}</a></p>` : ''}
                            ${date ? `<p style="margin: 5px 0 0 0; font-size: 12px; color: #888;">📅 ${date}</p>` : ''}
                            ${content ? `<p style="margin: 5px 0 0 0; font-size: 13px; line-height: 1.4; color: #333;">${content.substring(0, 200)}${content.length > 200 ? '...' : ''}</p>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        itemsHtml += '</div>';

        if (validItems.length > 10) {
            itemsHtml += `<p style="margin-top: 10px; text-align: center; color: #666; font-size: 13px;">还有 ${validItems.length - 10} 条未显示...</p>`;
        }

        itemsCard.innerHTML = itemsHtml;
        agentDetails.appendChild(itemsCard);
    } else {
        // 显示无结果提示
        const noItemsCard = document.createElement('div');
        noItemsCard.className = 'item-card';
        noItemsCard.style.marginTop = '20px';
        noItemsCard.style.borderLeft = '4px solid #ff9800';
        noItemsCard.style.background = '#fff3e0';
        noItemsCard.style.padding = '20px';

        noItemsCard.innerHTML = `
            <div style="text-align: center;">
                <h4 style="margin: 0 0 10px 0; color: #e65100;">⚠️ 未获取到内容</h4>
                <p style="margin: 0; color: #666;">工作流执行完成，但没有获取到实际内容。</p>
                <p style="margin: 5px 0 0 0; font-size: 13px; color: #888;">请检查:</p>
                <ul style="text-align: left; display: inline-block; margin: 10px 0 0 0; padding-left: 20px; color: #666;">
                    <li>目标URL是否可访问</li>
                    <li>爬取模式是否正确匹配页面结构</li>
                    <li>网站是否有反爬虫机制</li>
                    <li>查看上方的各Agent结果了解详情</li>
                </ul>
            </div>
        `;

        agentDetails.appendChild(noItemsCard);
    }
}

function createAgentCard(config) {
    const card = document.createElement('div');
    card.className = 'item-card';
    card.style.borderLeft = '4px solid var(--primary-color)';

    let html = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h4 style="margin: 0;">${config.icon} ${config.name}</h4>
            <span class="status-badge status-success">${config.status}</span>
        </div>
    `;

    if (config.details && config.details.length > 0) {
        html += '<div class="detail-grid">';
        config.details.forEach(detail => {
            html += `
                <div class="detail-item">
                    <span class="detail-label">${detail.label}:</span>
                    <span class="detail-value">${detail.value}</span>
                </div>
            `;
        });
        html += '</div>';
    }

    card.innerHTML = html;
    return card;
}

function addSection(card, title, content) {
    const section = document.createElement('div');
    section.style.marginTop = '15px';
    section.style.paddingTop = '15px';
    section.style.borderTop = '1px solid #e0e0e0';

    section.innerHTML = `
        <h5 style="margin-bottom: 10px; color: var(--primary-color);">${title}</h5>
        <div style="font-size: 14px; line-height: 1.6;">${content}</div>
    `;

    card.appendChild(section);
}

function displayMultiAgentError(error) {
    document.getElementById('ma-error-message').textContent = error || '未知错误';
}

/**
 * Get stored LLM configuration from localStorage
 * Used for Multi-Agent workflow execution
 */
function getLLMConfig() {
    try {
        const stored = localStorage.getItem('moagent_config');
        if (stored) {
            const config = JSON.parse(stored);
            // Return only LLM-related fields
            return {
                api_key: config.api_key || '',
                llm_provider: config.llm_provider || 'openai',
                llm_model: config.llm_model || 'gpt-4o-mini',
                api_base_url: config.api_base_url || ''
            };
        }
    } catch (e) {
        console.warn('Failed to load stored config:', e);
    }

    // Return default config if not found
    return {
        api_key: '',
        llm_provider: 'openai',
        llm_model: 'gpt-4o-mini',
        api_base_url: ''
    };
}
