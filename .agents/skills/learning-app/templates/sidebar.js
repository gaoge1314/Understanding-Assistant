/* ============================
   模块：左侧栏目录渲染
   ============================ */
(function() {
  'use strict';

  function renderSidebar() {
    var container = document.getElementById('sidebarGroups');
    container.innerHTML = '';

    var APP = window.__APP__;
    var order = APP.state.cardOrder;
    var groups = APP.state.groups || [];
    var groupedIds = new Set();

    groups.forEach(function(g) { (g.cardIds || []).forEach(function(id) { groupedIds.add(id); }); });

    groups.forEach(function(group, gi) {
      var div = document.createElement('div');
      var isExpanded = APP.state.groupsExpanded[gi] !== false;
      div.className = 'group-item';
      div.draggable = true;
      div.dataset.groupIndex = gi;
      div.innerHTML =
        '<div class="group-header" data-group-index="' + gi + '">' +
          '<span class="group-toggle ' + (isExpanded ? '' : 'collapsed') + '">▼</span>' +
          '<span class="group-name">' + AppState.escapeHtml(group.name) + '</span>' +
          '<span class="card-count" style="font-weight:400;">' + (group.cardIds || []).length + '</span>' +
        '</div>' +
        '<div class="group-cards ' + (isExpanded ? '' : 'collapsed') + '" id="groupCards_' + gi + '">' +
          (group.cardIds || []).map(function(cid) { return renderCardItem(cid); }).join('') +
        '</div>';
      container.appendChild(div);

      /* 组拖拽 */
      div.addEventListener('dragstart', function(e) {
        this.classList.add('dragging');
        e.dataTransfer.setData('text/plain', 'group_' + gi);
      });
      div.addEventListener('dragend', function() {
        this.classList.remove('dragging');
        document.querySelectorAll('.group-item').forEach(function(el) { el.classList.remove('drag-over'); });
      });
      div.addEventListener('dragover', function(e) {
        e.preventDefault();
        if (e.dataTransfer.types[0] === 'text/plain' && e.dataTransfer.getData('text/plain').startsWith('group_')) {
          this.classList.add('drag-over');
        }
      });
      div.addEventListener('dragleave', function() { this.classList.remove('drag-over'); });
      div.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        var data = e.dataTransfer.getData('text/plain');
        if (data && data.startsWith('group_')) {
          var fromIdx = parseInt(data.split('_')[1]);
          var toIdx = parseInt(this.dataset.groupIndex);
          if (fromIdx !== toIdx && !isNaN(fromIdx) && !isNaN(toIdx)) {
            var gs = APP.state.groups;
            var moved = gs.splice(fromIdx, 1)[0];
            gs.splice(toIdx, 0, moved);
            APP.state.groups = gs;
            AppState.saveState();
            renderSidebar();
          }
        }
      });

      var header = div.querySelector('.group-header');
      header.addEventListener('click', function(e) {
        if (e.target.closest('.card-item')) return;
        var toggle = this.querySelector('.group-toggle');
        var cards = document.getElementById('groupCards_' + gi);
        var collapsed = cards.classList.toggle('collapsed');
        toggle.classList.toggle('collapsed');
        APP.state.groupsExpanded[gi] = !collapsed;
        AppState.saveState();
      });
    });

    /* 未分组卡片 */
    var ungrouped = order.filter(function(id) { return !groupedIds.has(id); });
    if (ungrouped.length > 0) {
      if (groups.length > 0) {
        var label = document.createElement('div');
        label.className = 'ungrouped-label';
        label.textContent = '未分组';
        container.appendChild(label);
      }
      ungrouped.forEach(function(id) {
        container.appendChild(renderCardItemRaw(id));
      });
    }
  }

  function isCardUnlearned(cardTitle) {
    var rec = AppState.getReviewRecord(cardTitle);
    return rec.level === 0;
  }

  function renderCardItem(cardId) {
    var APP = window.__APP__;
    var card = APP.cardData[cardId];
    if (!card) return '';
    var state = AppState.getCardState(card.title);
    var active = APP.currentCardIndex === cardId ? 'active' : '';
    var unlearned = isCardUnlearned(card.title) ? 'unlearned' : '';
    return [
      '<div class="card-item ' + active + ' ' + unlearned + '" data-card-id="' + cardId + '" draggable="true">',
        '<span class="card-drag" draggable="true">⠿</span>',
        state.isCompleted ? '<span class="card-check">✓</span>' : '',
        '<span>' + AppState.escapeHtml(card.title) + '</span>',
      '</div>'
    ].join('');
  }

  function renderCardItemRaw(cardId) {
    var APP = window.__APP__;
    var card = APP.cardData[cardId];
    if (!card) return document.createElement('div');
    var state = AppState.getCardState(card.title);
    var active = APP.currentCardIndex === cardId ? 'active' : '';
    var unlearned = isCardUnlearned(card.title) ? 'unlearned' : '';
    var div = document.createElement('div');
    div.className = 'card-item ' + active + ' ' + unlearned;
    div.dataset.cardId = cardId;
    div.draggable = true;
    div.innerHTML =
      '<span class="card-drag">⠿</span>' +
      (state.isCompleted ? '<span class="card-check">✓</span>' : '') +
      '<span>' + AppState.escapeHtml(card.title) + '</span>';

    div.addEventListener('click', function() { CardView.selectCard(parseInt(this.dataset.cardId)); });

    /* 卡片拖拽 */
    div.addEventListener('dragstart', function(e) {
      this.classList.add('dragging');
      e.dataTransfer.setData('text/plain', 'card_' + this.dataset.cardId);
    });
    div.addEventListener('dragend', function() {
      this.classList.remove('dragging');
      document.querySelectorAll('.card-item').forEach(function(el) { el.classList.remove('drag-over'); });
    });
    div.addEventListener('dragover', function(e) { e.preventDefault(); this.classList.add('drag-over'); });
    div.addEventListener('dragleave', function() { this.classList.remove('drag-over'); });
    div.addEventListener('drop', function(e) {
      e.preventDefault();
      this.classList.remove('drag-over');
      var data = e.dataTransfer.getData('text/plain');
      if (data && data.startsWith('card_')) {
        var fromId = parseInt(data.split('_')[1]);
        var toId = parseInt(this.dataset.cardId);
        if (fromId !== toId) {
          var order = APP.state.cardOrder;
          var fromIdx = order.indexOf(fromId);
          var toIdx = order.indexOf(toId);
          if (fromIdx > -1 && toIdx > -1) {
            order.splice(fromIdx, 1);
            order.splice(toIdx, 0, fromId);
            APP.state.cardOrder = order;
            AppState.saveState();
            renderSidebar();
          }
        }
      }
    });
    return div;
  }

  window.Sidebar = {
    renderSidebar: renderSidebar
  };
})();