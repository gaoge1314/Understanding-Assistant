/* ============================
   模块：今日计划 + 结束学习
   ============================ */
(function() {
  'use strict';

  var todayPlanState = { selected: [] };

  /* ---------- 今日计划 ---------- */
  function openTodayPlanModal() {
    if (window.__APP__.state.isLocked) return;
    var quota = window.__APP__.state.userSettings.dailyWordQuota || 500;
    document.getElementById('todayPlanQuota').textContent = quota;
    updateQuotaBtnActive(quota);
    renderTodayPlanList(quota);
    document.getElementById('todayPlanModal').classList.add('open');
  }

  function updateQuotaBtnActive(val) {
    document.querySelectorAll('#todayPlanQuotaBar .quota-btn').forEach(function(btn) {
      btn.classList.toggle('active', parseInt(btn.dataset.value) === val);
    });
  }

  function renderTodayPlanList(quota) {
    var APP = window.__APP__;
    var list = document.getElementById('todayPlanList');
    var order = APP.state.cardOrder;

    var unlearned = order.filter(function(cid) {
      var card = APP.cardData[cid];
      if (!card) return false;
      var rec = AppState.getReviewRecord(card.title);
      return rec.level === 0;
    });

    if (unlearned.length === 0) {
      list.innerHTML = '<p style="text-align:center;color:#9ca3af;padding:20px;">🎉 所有卡片已学习完毕</p>';
      return;
    }

    var items = unlearned.map(function(cid) {
      var card = APP.cardData[cid];
      return { id: cid, title: card.title, words: AppState.calcWordCount(card), related: [] };
    });

    var titleMap = {};
    order.forEach(function(cid) { var c = APP.cardData[cid]; if (c) titleMap[c.title] = cid; });

    items.forEach(function(item) {
      var card = APP.cardData[item.id];
      if (!card || !card.knowledge_interfaces) return;
      card.knowledge_interfaces.forEach(function(k) {
        var targetTitle = typeof k === 'string' ? '' : (k.target_title || '');
        if (targetTitle && titleMap[targetTitle] !== undefined) {
          var targetId = titleMap[targetTitle];
          if (!item.related.includes(targetId)) item.related.push(targetId);
        }
      });
    });

    items.sort(function(a, b) { return b.related.length - a.related.length; });

    todayPlanState.selected = [];
    var currentWords = 0;
    for (var i = 0; i < items.length; i++) {
      if (currentWords >= quota * AppState.MIN_QUOTA_RATIO) break;
      var item = items[i];
      if (todayPlanState.selected.includes(item.id)) continue;
      if (currentWords + item.words > quota * AppState.MAX_QUOTA_RATIO) continue;
      todayPlanState.selected.push(item.id);
      currentWords += item.words;

      for (var j = 0; j < item.related.length; j++) {
        if (currentWords >= quota * AppState.MAX_QUOTA_RATIO) break;
        var rid = item.related[j];
        var rItem = null;
        for (var k = 0; k < items.length; k++) { if (items[k].id === rid) { rItem = items[k]; break; } }
        if (!rItem || todayPlanState.selected.includes(rid)) continue;
        if (currentWords + rItem.words > quota * AppState.MAX_QUOTA_RATIO) continue;
        todayPlanState.selected.push(rid);
        currentWords += rItem.words;
      }
    }

    var html = '';
    items.forEach(function(item) {
      var isSelected = todayPlanState.selected.includes(item.id);
      html += [
        '<label class="today-plan-item">',
          '<input type="checkbox" data-card-id="' + item.id + '"' + (isSelected ? ' checked' : '') + '>',
          '<span class="tpi-title">' + AppState.escapeHtml(item.title) + '</span>',
          '<span class="tpi-words">' + item.words + ' 字</span>',
          item.related.length > 0
            ? '<span class="tpi-status related">关联 ' + item.related.length + '</span>'
            : '<span class="tpi-status new-card">新卡片</span>',
        '</label>'
      ].join('');
    });
    list.innerHTML = html;

    list.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
      cb.addEventListener('change', function() { updateTodayPlanSummary(); });
    });

    updateTodayPlanSummary();
  }

  function updateTodayPlanSummary() {
    var checked = document.querySelectorAll('#todayPlanList input[type="checkbox"]:checked');
    var totalWords = 0;
    var ids = [];
    checked.forEach(function(cb) {
      var id = parseInt(cb.dataset.cardId);
      if (!isNaN(id)) {
        ids.push(id);
        totalWords += AppState.calcWordCount(window.__APP__.cardData[id]);
      }
    });
    todayPlanState.selected = ids;
    var quota = window.__APP__.state.userSettings.dailyWordQuota || 500;
    document.getElementById('todayPlanSummary').innerHTML = '已选 ' + ids.length + ' 张，' + totalWords + ' 字 / 配额 <span id="todayPlanQuota">' + quota + '</span> 字';
    document.getElementById('todayPlanConfirm').disabled = ids.length === 0;
  }

  /* ---------- 事件绑定 ---------- */
  document.getElementById('btnTodayPlan').addEventListener('click', function() {
    openTodayPlanModal();
  });

  document.querySelectorAll('#todayPlanQuotaBar .quota-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var val = parseInt(this.dataset.value);
      window.__APP__.state.userSettings.dailyWordQuota = val;
      var lMap = { 200: 'A', 500: 'B', 1000: 'C', 3000: 'D' };
      window.__APP__.state.userSettings.dailyQuotaLevel = lMap[val] || 'B';
      AppState.saveState();
      openTodayPlanModal();
    });
  });

  document.getElementById('todayPlanCancel').addEventListener('click', function() {
    document.getElementById('todayPlanModal').classList.remove('open');
  });

  document.getElementById('todayPlanConfirm').addEventListener('click', function() {
    document.getElementById('todayPlanModal').classList.remove('open');
    var ids = todayPlanState.selected;
    if (ids.length === 0) return;

    var groups = window.__APP__.state.groups || [];
    var groupNum = groups.filter(function(g) { return g.name && /^第[一二三四五六七八九十\d]+组$/.test(g.name); }).length + 1;
    var groupNames = ['第一', '第二', '第三', '第四', '第五'];
    var groupName = (groupNames[groupNum - 1] || groupNum + '组') + '组';
    if (!window.__APP__.state.groups) window.__APP__.state.groups = [];
    window.__APP__.state.groups.push({ name: groupName, cardIds: ids });
    AppState.saveState();
    Sidebar.renderSidebar();

    Flashcard.setSession({ cards: ids, current: 0, started: true, groupName: groupName });
    document.querySelector('.tab-btn[data-view="flashcard"]').click();
    Flashcard.renderFlashcard();
  });

  /* ---------- 结束学习 ---------- */
  document.getElementById('btnEndStudy').addEventListener('click', function() {
    if (window.__APP__.state.isLocked) return;
    document.getElementById('endStudyModal').classList.add('open');
  });

  document.getElementById('endStudyCancel').addEventListener('click', function() {
    document.getElementById('endStudyModal').classList.remove('open');
  });

  document.getElementById('endStudyConfirm').addEventListener('click', function() {
    document.getElementById('endStudyModal').classList.remove('open');
    window.__APP__.state.isLocked = true;
    AppState.saveState();
    document.getElementById('btnEndStudy').disabled = true;
    document.querySelector('.tab-btn[data-view="flashcard"]').click();
  });

  window.Plan = {
    openTodayPlanModal: openTodayPlanModal,
    renderTodayPlanList: renderTodayPlanList
  };
})();