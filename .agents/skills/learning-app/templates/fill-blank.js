/* ============================
   模块：概念填空
   ============================ */
(function() {
  'use strict';

  var fillState = { blanks: [], current: 0, answered: {} };
  var esc = function(s) { return AppState.escapeHtml(s); };

  function initFillBlank(card) {
    var blanks = card.blanks || [];
    if (blanks.length === 0) {
      document.getElementById('fillSentence').innerHTML = '<p style="color:#9ca3af;">暂无填空题目</p>';
      document.getElementById('fillProgress').textContent = '0 题';
      document.getElementById('fillSubmit').disabled = true;
      document.getElementById('fillPrev').disabled = true;
      document.getElementById('fillNext').disabled = true;
      return;
    }
    fillState = { blanks: blanks, current: 0, answered: {} };
    renderBlankQuestion(0);
  }

  function renderBlankQuestion(idx) {
    var blanks = fillState.blanks;
    if (!blanks || blanks.length === 0) return;
    var item = blanks[idx];
    if (!item) return;

    document.getElementById('fillProgress').textContent = '第 ' + (idx + 1) + '/' + blanks.length + ' 题';
    document.getElementById('fillResult').innerHTML = '';
    document.getElementById('fillSubmit').disabled = false;
    document.getElementById('fillPrev').disabled = idx <= 0;
    document.getElementById('fillNext').disabled = idx >= blanks.length - 1;

    var parts = item.sentence.split('____');
    var html = '';
    parts.forEach(function(part, pi) {
      html += esc(part);
      if (pi < item.answers.length) {
        var saved = fillState.answered[idx] ? fillState.answered[idx][pi] || '' : '';
        html += '<input class="fill-input" data-blank-index="' + pi + '" value="' + esc(saved) + '" placeholder="填写" maxlength="30">';
      }
    });
    document.getElementById('fillSentence').innerHTML = html;

    if (fillState.answered[idx]) {
      var inputs = document.querySelectorAll('.fill-input');
      inputs.forEach(function(inp, i) {
        var val = fillState.answered[idx][i];
        if (val) {
          inp.value = val;
          if (fillState.answered[idx]._submitted) {
            inp.disabled = true;
            inp.classList.add(val === item.answers[i] ? 'correct' : 'wrong');
          }
        }
      });
    }
  }

  document.getElementById('fillSubmit').addEventListener('click', function() {
    var idx = fillState.current;
    var item = fillState.blanks[idx];
    if (!item) return;

    var inputs = document.querySelectorAll('.fill-input');
    var answers = {};
    var allFilled = true;

    inputs.forEach(function(inp, i) {
      var val = inp.value.trim();
      answers[i] = val || '';
      if (!val) allFilled = false;
    });

    if (!allFilled) {
      document.getElementById('fillResult').innerHTML = '<div class="fr-wrong">⚠️ 请先填写所有空位</div>';
      return;
    }

    fillState.answered[idx] = answers;
    fillState.answered[idx]._submitted = true;

    var correctCount = 0;
    inputs.forEach(function(inp, i) {
      inp.disabled = true;
      if (answers[i] === item.answers[i]) {
        inp.classList.add('correct');
        correctCount++;
      } else {
        inp.classList.add('wrong');
      }
    });

    document.getElementById('fillResult').innerHTML = correctCount === item.answers.length
      ? '<div class="fr-correct">✅ 正确！</div>'
      : '<div class="fr-wrong">✗ 正确答案：' + item.answers.join('，') + '</div>';
    this.disabled = true;
  });

  document.getElementById('fillPrev').addEventListener('click', function() {
    if (fillState.current > 0) { fillState.current--; renderBlankQuestion(fillState.current); }
  });

  document.getElementById('fillNext').addEventListener('click', function() {
    if (fillState.current < fillState.blanks.length - 1) { fillState.current++; renderBlankQuestion(fillState.current); }
  });

  window.FillBlank = {
    initFillBlank: initFillBlank
  };
})();