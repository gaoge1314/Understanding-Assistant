/* ============================
   模块：状态管理
   ============================ */
(function() {
  'use strict';

  /* ---------- 共享数据 ---------- */
  window.__APP__ = {
    state: null,              // appState（从 localStorage 加载）
    cardData: [],             // 卡片数据数组
    allTitles: [],            // 所有知识标题
    subject: '',              // 科目名
    currentCardIndex: -1,     // 当前选中的卡片索引
  };

  /* ---------- 常量 ---------- */
  const STORAGE_KEY = 'cardAppState';
  const STORAGE_VERSION = 3;
  const DEFAULT_STATE = {
    version: STORAGE_VERSION,
    cardOrder: null,
    groups: [],
    cardStates: {},
    reviewRecord: {},
    userSettings: { dailyWordQuota: 500, dailyQuotaLevel: 'B', hintCount: 2 },
    recitationGroups: [],
    isLocked: false,
    groupsExpanded: {},
    sidebarCollapsed: false,
    rightbarCollapsed: false
  };
  const INTERVALS = [0, 1, 3, 7, 21, 60, 180];
  const MAX_LEVEL = 6;
  const MIN_QUOTA_RATIO = 0.9;
  const MAX_QUOTA_RATIO = 1.08;

  /* ---------- 状态操作 ---------- */
  function loadState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        var appState = JSON.parse(saved);
        if (appState.version !== STORAGE_VERSION) {
          // 从 v1 迁移
          if (appState.version === 1) {
            appState.reviewRecord = {};
            appState.userSettings = { ...DEFAULT_STATE.userSettings };
            appState.version = STORAGE_VERSION;
          }
          // 从 v2 迁移：folded → expanded
          if (appState.version === 2) {
            if (appState.cardStates) {
              Object.keys(appState.cardStates).forEach(function(title) {
                var st = appState.cardStates[title];
                if (st.folded) {
                  st.expanded = {
                    answer: st.folded.answer !== false,
                    path: st.folded.path !== false,
                    memory: st.folded.memory !== false,
                    interface: st.folded.interface !== false,
                    relation: true
                  };
                  delete st.folded;
                }
                if (st.myCreation === undefined) st.myCreation = '';
                if (st.editedKeywords === undefined) st.editedKeywords = null;
                if (!st.customVersions) {
                  st.customVersions = {
                    answer: { content: '', selectedSource: 'original' },
                    path: { content: '', selectedSource: 'original' },
                    memory: { content: '', selectedSource: 'original' }
                  };
                }
              });
            }
            appState.recitationGroups = appState.recitationGroups || [];
            appState.isLocked = appState.isLocked || false;
            appState.groupsExpanded = appState.groupsExpanded || {};
            if (appState.userSettings && appState.userSettings.hintCount === undefined) {
              appState.userSettings.hintCount = 2;
            }
            appState.version = STORAGE_VERSION;
          }
        }
        window.__APP__.state = appState;
      }
    } catch (e) { /* ignore */ }

    var s = window.__APP__.state;
    s = { ...DEFAULT_STATE, ...s };
    if (!s.reviewRecord) s.reviewRecord = {};
    if (!s.userSettings) s.userSettings = { ...DEFAULT_STATE.userSettings };
    if (!s.cardStates) s.cardStates = {};
    if (!s.recitationGroups) s.recitationGroups = [];
    if (!s.groupsExpanded) s.groupsExpanded = {};
    window.__APP__.state = s;
  }

  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(window.__APP__.state)); }
    catch (e) { /* ignore */ }
  }

  function getCardState(title) {
    var s = window.__APP__.state;
    if (!s.cardStates[title]) {
      s.cardStates[title] = {
        expanded: { answer: true, path: true, memory: true, interface: true, relation: true },
      customVersions: { myUnderstanding: '',
        myCreation: '',
        customVersions: {
          answer: { content: '', selectedSource: 'original' },
          path: { content: '', selectedSource: 'original' },
          memory: { content: '', selectedSource: 'original' }
        },
        editedKeywords: null,
        isCompleted: false
      };
    }
    return s.cardStates[title];
  }

  function getReviewRecord(title) {
    var s = window.__APP__.state;
    if (!s.reviewRecord[title]) {
      s.reviewRecord[title] = {
        level: 0, nextReviewDate: '', interval: 1,
        reviewCount: 0, lastReviewDate: null
      };
    }
    return s.reviewRecord[title];
  }

  function calcWordCount(card) {
    if (!card || !card.answer) return 0;
    return card.answer.replace(/\s/g, '').length;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ---------- 公开 API ---------- */
  window.AppState = {
    loadState: loadState,
    saveState: saveState,
    getCardState: getCardState,
    getReviewRecord: getReviewRecord,
    calcWordCount: calcWordCount,
    escapeHtml: escapeHtml,
    INTERVALS: INTERVALS,
    MAX_LEVEL: MAX_LEVEL,
    MIN_QUOTA_RATIO: MIN_QUOTA_RATIO,
    MAX_QUOTA_RATIO: MAX_QUOTA_RATIO
  };
})();