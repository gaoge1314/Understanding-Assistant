/* ============================
   模块：卡片主内容渲染
   ============================ */
(function() {
  'use strict';

  function selectCard(index) {
    var APP = window.__APP__;
    if (index < 0 || index >= APP.cardData.length) return;
    if (APP.state.isLocked) return;

    APP.currentCardIndex = index;
    var card = APP.cardData[index];

    document.getElementById('contentPlaceholder').style.display = 'none';
    document.getElementById('contentCard').style.display = 'block';

    Sidebar.renderSidebar();
    renderCardContent(card);
    renderRightbar(card);
  }

  /* ---------- 卡片主内容 ---------- */
  function renderCardContent(card) {
    // 设置卡片标题 + 内容类型标签
    var typeLabel = getTypeLabel(card.content_type);
    var currentTitle = document.getElementById('cardTitle');
    currentTitle.innerHTML = AppState.escapeHtml(card.title) + (typeLabel ? ' <span class="content-type-tag type-tag-' + getTypeSafe(card.content_type) + '">' + AppState.escapeHtml(typeLabel) + '</span>' : '');

    // 设置卡片背景色
    var contentCard = document.getElementById('contentCard');
    contentCard.className = 'content-card type-' + getTypeSafe(card.content_type);

    var state = AppState.getCardState(card.title);
    var sections = document.getElementById('cardSections');
    sections.innerHTML = '';

    var sectionConfigs = [
      { id: 'answer', label: '① 答案（考试默写）', content: formatAnswer(card, state) },
      { id: 'path', label: '② 理解路径', content: formatPath(card, state) },
      { id: 'memory', label: '③ 记忆技巧（关键词' + (card.memory_techniques && card.memory_techniques.memory_aids ? '+ 口诀' : '') + '）', content: formatMemory(card.memory_techniques, state) },
      { id: 'interface', label: '④ 与其他知识的关键接口', content: formatInterfaces(card) }
    ];

    sectionConfigs.forEach(function(cfg) {
      if (!cfg.content && cfg.id !== 'memory') return;
      if (cfg.id === 'memory' && !cfg.content && !card.memory_techniques) return;

      var details = document.createElement('details');
      details.className = 'card-section';
      details.open = state.expanded[cfg.id] !== false;
      details.addEventListener('toggle', function() {
        state.expanded[cfg.id] = this.open;
        AppState.saveState();
      });

      var versionHtml = '';
      if (cfg.id !== 'interface') {
        var cv = state.customVersions[cfg.id];
        var hasCustom = cv && cv.content && cv.content.trim();
        versionHtml = [
          '<select class="version-selector" data-section="' + cfg.id + '">',
            '<option value="original"' + (!cv || cv.selectedSource !== 'custom' ? ' selected' : '') + '>原始版本</option>',
            '<option value="custom"' + (cv && cv.selectedSource === 'custom' && hasCustom ? ' selected' : '') + (hasCustom ? '' : ' disabled') + '>我的修改</option>',
          '</select>'
        ].join('');
      }

      details.innerHTML = '<summary>' + cfg.label + ' ' + versionHtml + '</summary><div class="section-body">' + cfg.content + '</div>';

      /* 创作编辑区（interface 除外） */
      if (cfg.id !== 'interface') {
        var editArea = document.createElement('details');
        editArea.className = 'custom-edit-area';
        editArea.innerHTML = [
          '<summary>✏️ 自定义此板块</summary>',
          '<textarea data-section="' + cfg.id + '" placeholder="在此修改' + cfg.label + '的内容...">' + AppState.escapeHtml(state.customVersions[cfg.id]?.content || '') + '</textarea>',
          '<div class="custom-edit-actions">',
            '<button class="btn-custom-reset" data-section="' + cfg.id + '">↺ 重置为原始</button>',
            '<button class="btn-custom-save" data-section="' + cfg.id + '">💾 保存修改</button>',
          '</div>'
        ].join('');
        details.querySelector('.section-body').appendChild(editArea);
      }

      sections.appendChild(details);
    });
  }

  function getDisplayContent(sectionId, originalContent, state) {
    var cv = state.customVersions[sectionId];
    if (cv && cv.selectedSource === 'custom' && cv.content && cv.content.trim()) {
      return cv.content;
    }
    return originalContent;
  }

  function formatAnswer(card, state) {
    if (!card.answer) return '';
    var labels = { user_specified: '用户指定', ai_extracted: 'AI提取', ai_generated: 'AI生成' };
    var src = labels[card.answer_source] || '未知';
    var display = getDisplayContent('answer', card.answer, state);
    return '<p>' + AppState.escapeHtml(display) + '</p><p style="font-size:12px;color:#9ca3af;">来源：' + src + '</p>';
  }

  function formatPath(card, state) {
    var display = getDisplayContent('path', '', state);
    if (display) {
      return '<div style="line-height:1.7;">' + AppState.escapeHtml(display) + '</div>';
    }
    var html = '';
    if (card.core_principle) html += '<p><strong>核心原理</strong>：' + AppState.escapeHtml(card.core_principle) + '</p>';
    if (card.problem_solved) html += '<p><strong>它解决了什么问题</strong>：' + AppState.escapeHtml(card.problem_solved) + '</p>';
    if (card.decomposition && card.decomposition.length > 0) {
      html += '<p><strong>分解理解</strong>：</p><ul>';
      card.decomposition.forEach(function(d) {
        if (d.startsWith('<!-- mermaid -->')) html += d;
        else html += '<li>' + AppState.escapeHtml(d) + '</li>';
      });
      html += '</ul>';
    }
    if (card.scenario_question) html += '<p><strong>典型判断情境</strong>：</p><p><strong>题目</strong>：' + AppState.escapeHtml(card.scenario_question) + '</p>';
    if (card.judgment_chain && card.judgment_chain.length > 0) {
      html += '<p><strong>判断链</strong>：</p><ul>';
      card.judgment_chain.forEach(function(j) { html += '<li>' + AppState.escapeHtml(j) + '</li>'; });
      html += '</ul>';
    }
    if (card.judgment_conclusion) html += '<p><strong>判断结论</strong>：' + AppState.escapeHtml(card.judgment_conclusion) + '</p>';
    return html;
  }

  function formatMemory(mt, state) {
    if (!mt && !state) return '';
    var display = state ? getDisplayContent('memory', '', state) : '';
    if (display) {
      var html = '<div style="line-height:1.7;">' + AppState.escapeHtml(display) + '</div>';
      html += formatKeywords(mt, state);
      return html;
    }
    if (!mt) return '';
    var html = formatKeywords(mt, state);
    // 记忆辅助（口诀/类比/意象）
    if (mt.memory_aids && mt.memory_aids.length > 0) {
      html += '<div class="memory-aids-section">';
      html += '<div class="ma-title">💡 记忆辅助</div>';
      mt.memory_aids.forEach(function(ma, i) {
        var kw = mt.keywords && mt.keywords[i] ? '<span class="ma-keyword">' + AppState.escapeHtml(mt.keywords[i]) + '</span>' : '';
        html += '<div class="ma-item">' + kw + (kw ? '：' : '') + AppState.escapeHtml(ma) + '</div>';
      });
      html += '</div>';
    }
    if (mt.hierarchy) html += '<p><strong>层级关系</strong>：</p>' + mt.hierarchy;
    if (mt.comparison_tables && mt.comparison_tables.length > 0) {
      html += '<p><strong>对比表格</strong>：</p>';
      mt.comparison_tables.forEach(function(t) { html += t; });
    }
    return html;
  }

  function formatKeywords(mt, state) {
    var keywords = state.editedKeywords || (mt ? mt.keywords : []);
    if (!keywords || keywords.length === 0) return '';
    return [
      '<p><strong>关键词</strong>：<button class="btn-small" id="btnEditKeywords" style="margin-left:8px;font-size:11px;">✏️ 编辑</button></p><ul>',
      keywords.map(function(k) { return '<li>' + AppState.escapeHtml(k) + '</li>'; }).join(''),
      '</ul>'
    ].join('');
  }

  function formatInterfaces(card) {
    if (!card.knowledge_interfaces || card.knowledge_interfaces.length === 0) return '';
    var APP = window.__APP__;
    var idToIndex = {};
    APP.cardData.forEach(function(c, i) { if (c.card_id) idToIndex[c.card_id] = i; });

    var html = '<ul>';
    card.knowledge_interfaces.forEach(function(k) {
      var iface = k;
      if (typeof k === 'string') iface = { raw_text: k, target_card_id: '', target_title: '', relation: '' };
      var displayText = iface.raw_text || (iface.target_title ? '→ ' + iface.target_title + (iface.relation ? '：' + iface.relation : '') : '');
      var targetId = iface.target_card_id;
      var targetIndex = targetId ? idToIndex[targetId] : -1;

      if (targetIndex >= 0 && targetIndex !== APP.currentCardIndex) {
        html += '<li><a class="knowledge-link" data-card-index="' + targetIndex + '" href="#">' + AppState.escapeHtml(displayText) + '</a></li>';
      } else {
        html += '<li>' + AppState.escapeHtml(displayText) + '</li>';
      }
    });
    html += '</ul>';
    return html;
  }

  /* ---------- 右侧栏 ---------- */
  function renderRightbar(card) {
    var state = AppState.getCardState(card.title);
    var types = card.reconstruct_type || [];

    var select = document.getElementById('reconstructSelect');
    var modeBadge = document.getElementById('modeBadge');
    var reorderArea = document.getElementById('reorderArea');
    var fillArea = document.getElementById('fillArea');

    if (types.length > 0) {
      select.style.display = 'block';
      modeBadge.style.display = 'none';
      Array.from(select.options).forEach(function(opt) {
        if (opt.value === 'note') opt.style.display = '';
        else opt.style.display = types.includes(opt.value) ? '' : 'none';
      });
      select.value = 'note';
    } else {
      select.style.display = 'none';
      modeBadge.style.display = 'inline-block';
      modeBadge.textContent = '📝 笔记模式';
    }

    reorderArea.style.display = 'none';
    fillArea.style.display = 'none';
  }

  /* ---------- 关键词编辑模态框 ---------- */
  function openKeywordsModal() {
    var APP = window.__APP__;
    var card = APP.cardData[APP.currentCardIndex];
    if (!card) return;
    var state = AppState.getCardState(card.title);
    var keywords = state.editedKeywords || (card.memory_techniques ? card.memory_techniques.keywords : []);
    renderKeywordsEditList(keywords);
    document.getElementById('keywordsModal').classList.add('open');
    document.getElementById('keywordsModal').dataset.cardTitle = card.title;
  }

  function renderKeywordsEditList(keywords) {
    var list = document.getElementById('keywordsEditList');
    list.innerHTML = keywords.map(function(kw, i) {
      return '<div class="keywords-edit-item"><input type="text" value="' + AppState.escapeHtml(kw) + '" data-index="' + i + '" placeholder="输入关键词"><button class="ke-remove" data-index="' + i + '">✕</button></div>';
    }).join('');
  }

  function closeKeywordsModal() {
    document.getElementById('keywordsModal').classList.remove('open');
  }

  /* ---------- 事件委托 ---------- */
  // 知识链接点击
  document.getElementById('cardSections').addEventListener('click', function(e) {
    var link = e.target.closest('.knowledge-link');
    if (link) {
      e.preventDefault();
      var index = parseInt(link.dataset.cardIndex);
      if (!isNaN(index) && index >= 0 && index < window.__APP__.cardData.length) {
        selectCard(index);
      }
      return;
    }

    // 关键词编辑
    if (e.target.id === 'btnEditKeywords') {
      openKeywordsModal();
      return;
    }

    // 创作编辑区按钮
    var saveBtn = e.target.closest('.btn-custom-save');
    var resetBtn = e.target.closest('.btn-custom-reset');
    var APP = window.__APP__;
    var card = APP.cardData[APP.currentCardIndex];
    if (!card) return;
    var state = AppState.getCardState(card.title);

    if (saveBtn) {
      var section = saveBtn.dataset.section;
      var textarea = document.querySelector('textarea[data-section="' + section + '"]');
      if (textarea) {
        state.customVersions[section].content = textarea.value;
        AppState.saveState();
        renderCardContent(card);
      }
    }
    if (resetBtn) {
      var section2 = resetBtn.dataset.section;
      state.customVersions[section2].content = '';
      state.customVersions[section2].selectedSource = 'original';
      AppState.saveState();
      renderCardContent(card);
    }
  });

  // 版本选择器切换
  document.getElementById('cardSections').addEventListener('change', function(e) {
    var sel = e.target.closest('.version-selector');
    if (!sel) return;
    var section = sel.dataset.section;
    var APP = window.__APP__;
    var card = APP.cardData[APP.currentCardIndex];
    if (!card) return;
    var state = AppState.getCardState(card.title);
    state.customVersions[section].selectedSource = sel.value;
    AppState.saveState();
    renderCardContent(card);
  });

  // 关键词模态框事件
  document.getElementById('keywordsAddBtn').addEventListener('click', function() {
    var list = document.getElementById('keywordsEditList');
    var idx = list.children.length;
    var div = document.createElement('div');
    div.className = 'keywords-edit-item';
    div.innerHTML = '<input type="text" value="" data-index="' + idx + '" placeholder="输入关键词"><button class="ke-remove" data-index="' + idx + '">✕</button>';
    list.appendChild(div);
  });

  document.getElementById('keywordsEditList').addEventListener('click', function(e) {
    if (e.target.classList.contains('ke-remove')) {
      e.target.parentElement.remove();
    }
  });

  document.getElementById('keywordsSave').addEventListener('click', function() {
    var cardTitle = document.getElementById('keywordsModal').dataset.cardTitle;
    if (!cardTitle) return;
    var APP = window.__APP__;
    var card = APP.cardData.find(function(c) { return c.title === cardTitle; });
    if (!card) return;
    var state = AppState.getCardState(card.title);
    var inputs = document.querySelectorAll('#keywordsEditList input');
    var keywords = [];
    inputs.forEach(function(inp) {
      var v = inp.value.trim();
      if (v) keywords.push(v);
    });
    state.editedKeywords = keywords.length > 0 ? keywords : null;
    AppState.saveState();
    closeKeywordsModal();
    renderCardContent(card);
  });

  document.getElementById('keywordsCancel').addEventListener('click', closeKeywordsModal);

  /* ---------- 内容类型辅助函数 ---------- */
  function getTypeLabel(type) {
    var labels = { A: '🔹 逻辑序列', B: '🔸 机制/机理', C: '🟢 结构/模型', D: '🟠 概念辨析', mixed: '🎨 混合类型' };
    return labels[type] || '';
  }

  function getTypeSafe(type) {
    var types = ['A', 'B', 'C', 'D', 'mixed'];
    return types.indexOf(type) >= 0 ? type : '';
  }

  /* ---------- 公开 API ---------- */
  window.CardView = {
    selectCard: selectCard,
    renderCardContent: renderCardContent,
    getDisplayContent: getDisplayContent
  };
})();