/* ============================
   模块：背诵视图（翻转卡 + 记忆曲线）
   ============================ */
(function() {
  'use strict';

  var flashSession = { cards: [], current: 0, started: false, groupName: '' };

  function initFlashcardView() {
    if (!flashSession.started) {
      var planGroup = (window.__APP__.state.groups || []).find(function(g) { return g.name && /^第[一二三四五六七八九十\d]+组$/.test(g.name); });
      if (planGroup && planGroup.cardIds && planGroup.cardIds.length > 0) {
        flashSession = { cards: planGroup.cardIds, current: 0, started: true, groupName: planGroup.name };
      } else {
        document.getElementById('flashcardView').innerHTML = [
          '<div class="flashcard-view">',
            '<p style="color:#9ca3af;margin-bottom:12px;">请先在【学习】视图中设置今日计划</p>',
            '<button class="btn-primary" onclick="document.querySelector(\'.tab-btn[data-view=\\\'learn\\\']\').click()">去学习视图</button>',
          '</div>'
        ].join('\n');
        return;
      }
    }
    renderFlashcard();
  }

  function renderFlashcard() {
    var view = document.getElementById('flashcardView');
    var cards = flashSession.cards;
    var idx = flashSession.current;

    if (!cards || cards.length === 0 || idx >= cards.length) {
      view.innerHTML = [
        '<div class="flashcard-view">',
          '<div class="flashcard-summary">',
            '<div class="fs-done" style="font-size:24px;">🎉 今日背诵完成！</div>',
            '<p style="margin-top:12px;">共复习 ' + (flashSession.cards ? flashSession.cards.length : 0) + ' 张卡片</p>',
          '</div>',
        '</div>'
      ].join('\n');
      flashSession.started = false;
      window.__APP__.state.isLocked = false;
      document.getElementById('btnEndStudy').disabled = false;
      AppState.saveState();
      return;
    }

    var APP = window.__APP__;
    var card = APP.cardData[cards[idx]];
    if (!card) {
      flashSession.current++;
      renderFlashcard();
      return;
    }

    var rec = AppState.getReviewRecord(card.title);
    var levelLabel = rec.level > 0 ? 'Level ' + rec.level + '（间隔 ' + (AppState.INTERVALS[rec.level] || 1) + ' 天）' : '新卡片';
    var state = AppState.getCardState(card.title);

    view.innerHTML = [
      '<div class="flashcard-view">',
      '<div class="flashcard-progress">第 ' + (idx + 1) + '/' + cards.length + ' 张 · ' + levelLabel + '</div>',
      '<div class="flashcard-container" id="flashcardContainer">',
      '<div class="flashcard-inner" id="flashcardInner">',
      '<div class="flashcard-front">',
      '<div class="fc-title">' + AppState.escapeHtml(card.title) + '</div>',
      '<div class="flashcard-hint-area">',
      '<button class="btn-hint" id="btnHint">💡 显示提示</button>',
      '<div class="hint-content" id="hintContent" style="display:none;">',
      formatHintKeywords(card, state),
      '</div></div>',
      '<div class="fc-hint" style="margin-top:16px;">👆 点击翻转查看答案</div>',
      '</div>',
      '<div class="flashcard-back">',
      '<div class="fc-answer">' + (getFlashcardAnswer(card, state) || '（无答案）') + '</div>',
      '</div></div></div>',
      '<div class="flashcard-actions" id="flashcardActions" style="display:none;">',
      '<button class="btn-forgot" id="btnForgot">👎 忘了</button>',
      '<button class="btn-remember" id="btnRemember">👍 记得</button>',
      '</div></div>'
    ].join('\n');

    var flipped = false;
    var container = document.getElementById('flashcardContainer');
    var inner = document.getElementById('flashcardInner');
    var actions = document.getElementById('flashcardActions');

    container.addEventListener('click', function() {
      if (flipped) return;
      flipped = true;
      inner.classList.add('flipped');
      actions.style.display = 'flex';
    });

    document.getElementById('btnHint').addEventListener('click', function(e) {
      e.stopPropagation();
      var hintContent = document.getElementById('hintContent');
      if (hintContent.style.display === 'none') {
        hintContent.style.display = 'block';
        this.textContent = '🙈 隐藏提示';
      } else {
        hintContent.style.display = 'none';
        this.textContent = '💡 显示提示';
      }
    });

    document.getElementById('btnRemember').addEventListener('click', function(e) {
      e.stopPropagation();
      handleFlashcardResult(cards[idx], true);
    });

    document.getElementById('btnForgot').addEventListener('click', function(e) {
      e.stopPropagation();
      handleFlashcardResult(cards[idx], false);
    });
  }

  function formatHintKeywords(card, state) {
    var keywords = state.editedKeywords || (card.memory_techniques ? card.memory_techniques.keywords : []);
    var count = window.__APP__.state.userSettings.hintCount || 2;
    var selected = keywords.slice(0, count).map(function(k) {
      return k.length > 25 ? k.substring(0, 25) + '…' : k;
    });
    if (selected.length === 0) return '<span style="color:#9ca3af;">暂无关键词提示</span>';
    return '<ul>' + selected.map(function(k) { return '<li>' + AppState.escapeHtml(k) + '</li>'; }).join('') + '</ul>';
  }

  function getFlashcardAnswer(card, state) {
    var cv = state.customVersions.answer;
    if (cv && cv.selectedSource === 'custom' && cv.content && cv.content.trim()) {
      return cv.content;
    }
    return card.answer;
  }

  function handleFlashcardResult(cardId, remembered) {
    var APP = window.__APP__;
    var card = APP.cardData[cardId];
    if (!card) return;
    var rec = AppState.getReviewRecord(card.title);

    if (remembered) {
      rec.level = Math.min(rec.level + 1, AppState.MAX_LEVEL);
    } else {
      rec.level = 1;
    }

    rec.interval = AppState.INTERVALS[rec.level] || 1;
    rec.reviewCount = (rec.reviewCount || 0) + 1;
    rec.lastReviewDate = new Date().toISOString().split('T')[0];

    var next = new Date();
    next.setDate(next.getDate() + rec.interval);
    rec.nextReviewDate = next.toISOString().split('T')[0];

    AppState.saveState();

    flashSession.current++;
    renderFlashcard();
  }

  window.Flashcard = {
    initFlashcardView: initFlashcardView,
    renderFlashcard: renderFlashcard,
    setSession: function(s) { flashSession = s; }
  };
})();