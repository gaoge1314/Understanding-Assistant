/* ============================
   模块：概念重组（拖拽排序）
   ============================ */
(function() {
  'use strict';

  var reorderState = { items: [], shuffledIds: [], placements: {} };
  var esc = function(s) { return AppState.escapeHtml(s); };

  function initReorder(card) {
    var items = card.decomposition.map(function(text, i) {
      return { id: i, text: text, shortLabel: text.split(/[，,。.：:]/)[0] || text };
    });
    var shuffled = [].concat(items).sort(function() { return Math.random() - 0.5; });
    reorderState = { items: items, shuffledIds: shuffled.map(function(s) { return s.id; }), placements: {} };

    document.getElementById('reorderSlots').innerHTML = items.map(function(_, i) {
      return '<div class="reorder-slot" data-slot-index="' + i + '" data-filled="false">位置 ' + (i + 1) + '</div>';
    }).join('');

    document.getElementById('reorderBlocks').innerHTML = shuffled.map(function(item) {
      return '<div class="reorder-block" draggable="true" data-item-id="' + item.id + '" data-color="' + (item.id % 8) + '">' + esc(item.shortLabel) + '</div>';
    }).join('');

    document.getElementById('reorderResult').innerHTML = '';
    document.getElementById('btnCheckReorder').disabled = true;
    setupReorderDrag();
  }

  function setupReorderDrag() {
    var blocks = document.querySelectorAll('.reorder-block');
    var slots = document.querySelectorAll('.reorder-slot');

    blocks.forEach(function(block) {
      block.addEventListener('dragstart', function(e) {
        this.classList.add('dragging');
        e.dataTransfer.setData('text/plain', this.dataset.itemId);
        document.getElementById('btnCheckReorder').disabled = true;
        document.getElementById('reorderResult').innerHTML = '';
      });
      block.addEventListener('dragend', function() {
        this.classList.remove('dragging');
        slots.forEach(function(s) { s.classList.remove('drag-over'); });
      });
    });

    slots.forEach(function(slot) {
      slot.addEventListener('dragover', function(e) {
        e.preventDefault();
        if (this.dataset.filled === 'true') return;
        this.classList.add('drag-over');
      });
      slot.addEventListener('dragleave', function() { this.classList.remove('drag-over'); });
      slot.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        if (this.dataset.filled === 'true') return;
        var itemId = parseInt(e.dataTransfer.getData('text/plain'));
        var item = reorderState.items.find(function(i) { return i.id === itemId; });
        if (!item) return;
        this.textContent = item.shortLabel;
        this.dataset.filled = 'true';
        this.classList.add('filled');
        this.classList.remove('correct', 'wrong');
        var block = document.querySelector('.reorder-block[data-item-id="' + itemId + '"]');
        if (block) block.classList.add('used');
        reorderState.placements[this.dataset.slotIndex] = itemId;
        var allFilled = Object.keys(reorderState.placements).length === reorderState.items.length;
        document.getElementById('btnCheckReorder').disabled = !allFilled;
      });
      slot.addEventListener('click', function() {
        if (this.dataset.filled !== 'true') return;
        var itemId = reorderState.placements[this.dataset.slotIndex];
        if (itemId === undefined) return;
        var block = document.querySelector('.reorder-block[data-item-id="' + itemId + '"]');
        if (block) block.classList.remove('used');
        this.textContent = '位置 ' + (parseInt(this.dataset.slotIndex) + 1);
        this.dataset.filled = 'false';
        this.classList.remove('filled', 'correct', 'wrong');
        delete reorderState.placements[this.dataset.slotIndex];
        document.getElementById('btnCheckReorder').disabled = true;
        document.getElementById('reorderResult').innerHTML = '';
      });
    });
  }

  document.getElementById('btnCheckReorder').addEventListener('click', function() {
    var slots = document.querySelectorAll('.reorder-slot');
    var correctCount = 0;
    var explainLines = [];
    var itemMap = {};
    reorderState.items.forEach(function(i) { itemMap[i.id] = i; });

    slots.forEach(function(slot) {
      var si = parseInt(slot.dataset.slotIndex);
      var placedId = reorderState.placements[si];
      var correctId = reorderState.items[si].id;
      slot.classList.remove('correct', 'wrong');
      if (placedId === correctId) {
        slot.classList.add('correct');
        correctCount++;
      } else {
        slot.classList.add('wrong');
        var correct = itemMap[correctId];
        if (correct) {
          var explain = correct.text.length > 50 ? correct.text.substring(0, 50) + '…' : correct.text;
          explainLines.push(
            '<div class="r-wrong">✗ 位置 ' + (si + 1) + '：应该是"' + correct.shortLabel + '"</div>' +
            '<div class="r-explain">→ ' + esc(explain) + '</div>'
          );
        }
      }
    });

    var resultEl = document.getElementById('reorderResult');
    var APP = window.__APP__;
    if (correctCount === reorderState.items.length) {
      resultEl.innerHTML = '<div class="r-correct">✅ 全部正确！</div>';
      var card = APP.cardData[APP.currentCardIndex];
      if (card) { AppState.getCardState(card.title).isCompleted = true; AppState.saveState(); Sidebar.renderSidebar(); }
    } else {
      resultEl.innerHTML = '<div class="r-correct">✓ 正确 ' + correctCount + '/' + reorderState.items.length + '</div>' + explainLines.join('');
    }
  });

  window.Reorder = {
    initReorder: initReorder
  };
})();