// Client behavior for every page: language, poem font, pinyin, glosses, read-aloud,
// and on the home page search and the daily poem. No dependencies.
(function () {
  'use strict';

  var root = document.documentElement;
  var BASE = root.dataset.base || './';

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) {}
    return null;
  }

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      if (c) n.appendChild(c);
    });
    return n;
  }

  // A bilingual pair of sibling spans; CSS hides the inactive one.
  function bi(en, zh, tag) {
    var f = document.createDocumentFragment();
    f.appendChild(el(tag || 'span', { lang: 'en', text: en }));
    f.appendChild(el(tag || 'span', { lang: 'zh', text: zh }));
    return f;
  }

  function getJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' ' + r.status);
      return r.json();
    });
  }

  /* ---------- Language (same mechanism as honghao.me; the key `lang` is shared) ---------- */
  var langButtons = document.querySelectorAll('[data-set-lang]');
  function applyLang(lang) {
    root.dataset.lang = lang;
    root.lang = lang === 'zh' ? 'zh-CN' : 'en';
    langButtons.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.setLang === lang));
    });
    // Attributes cannot hold two languages at once, so swap them here.
    document.querySelectorAll('[data-ph-en]').forEach(function (n) {
      n.placeholder = n.dataset['ph' + (lang === 'zh' ? 'Zh' : 'En')];
    });
  }
  applyLang(root.dataset.lang || 'en');
  langButtons.forEach(function (b) {
    b.addEventListener('click', function () {
      applyLang(b.dataset.setLang);
      store('lang', b.dataset.setLang);
    });
  });
  if (location.protocol.indexOf('http') === 0) {
    document.querySelectorAll('[data-host]').forEach(function (n) {
      n.textContent = location.host;
    });
  }

  /* ---------- Poem font ---------- */
  var FONTS = window.SHI_FONTS || [];
  function fontByKey(key) {
    for (var i = 0; i < FONTS.length; i++) if (FONTS[i].key === key) return FONTS[i];
    return FONTS[0];
  }
  function loadFontCss(f) {
    var id = 'font-' + f.key;
    if (!f.css || document.getElementById(id)) return;
    document.head.appendChild(el('link', { id: id, rel: 'stylesheet', href: f.css }));
  }
  function applyFont(key) {
    var f = fontByKey(key);
    if (!f) return;
    loadFontCss(f);
    root.style.setProperty('--poem', "'" + f.family + "', 'LXGW WenKai', 'Songti SC', serif");
    root.dataset.font = f.key;
    document.querySelectorAll('.fonts button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.font === f.key));
    });
  }

  /* ---------- Bottom sheet ---------- */
  var sheet = document.getElementById('sheet');
  var sheetBody = sheet && sheet.querySelector('.body');
  var sheetTitle = sheet && sheet.querySelector('.top .label');
  var lastFocus = null;
  function openSheet(titleEn, titleZh, content) {
    if (!sheet) return;
    lastFocus = document.activeElement;
    sheetTitle.innerHTML = '';
    sheetTitle.appendChild(bi(titleEn, titleZh));
    sheetBody.innerHTML = '';
    sheetBody.appendChild(content);
    sheet.classList.add('open');
    sheet.setAttribute('aria-hidden', 'false');
    sheet.querySelector('.close').focus();
  }
  function closeSheet() {
    if (!sheet || !sheet.classList.contains('open')) return;
    sheet.classList.remove('open');
    sheet.setAttribute('aria-hidden', 'true');
    if (lastFocus) lastFocus.focus();
  }
  if (sheet) {
    sheet.querySelector('.shade').addEventListener('click', closeSheet);
    sheet.querySelector('.close').addEventListener('click', closeSheet);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeSheet();
    });
  }

  /* ---------- Poem page ---------- */
  var dataNode = document.getElementById('poem-data');
  var poem = dataNode ? JSON.parse(dataNode.textContent) : null;

  if (poem) {
    var lines = document.querySelectorAll('.lines .ln');

    // Pinyin: shown or hidden all at once from the toolbar.
    var pyBtn = document.getElementById('btn-pinyin');
    function setPinyinAll(on, save) {
      root.classList.toggle('py-all', on);
      if (pyBtn) pyBtn.setAttribute('aria-pressed', String(on));
      if (save) store('shi.pinyin', on ? '1' : '0');
    }
    // The pre-paint script already applied ?pinyin= or the saved choice; a link's choice is not saved.
    setPinyinAll(root.classList.contains('py-all'), false);
    if (pyBtn)
      pyBtn.addEventListener('click', function () {
        setPinyinAll(!root.classList.contains('py-all'), true);
      });

    function wordFor(li, start, end) {
      var cells = poem.lines[li].slice(start, end);
      return {
        text: cells.map(function (c) { return c[0]; }).join(''),
        pinyin: cells.map(function (c) { return c[1]; }).join(' '),
      };
    }

    // Only characters with a note (underlined) can be tapped.
    document.querySelector('.lines').addEventListener('click', function (e) {
      var c = e.target.closest('.c.gl, .c.rd');
      if (!c) return;
      var li = +c.dataset.l, pos = +c.dataset.p;
      var notes = document.createDocumentFragment();
      var title = null;
      (poem.glosses || []).forEach(function (g) {
        if (g.line === li && pos >= g.start && pos < g.end) {
          var w = wordFor(li, g.start, g.end);
          title = title || w;
          notes.appendChild(el('p', { lang: 'zh', text: g.zh }));
          notes.appendChild(el('p', { lang: 'en', text: g.en }));
        }
      });
      (poem.readings || []).forEach(function (r) {
        if (r.line === li && r.pos === pos) {
          title = title || wordFor(li, pos, pos + 1);
          notes.appendChild(el('p', { lang: 'zh', text: '读音：' + r.zh }));
          notes.appendChild(el('p', { lang: 'en', text: 'Reading: ' + r.en }));
        }
      });
      if (!title) return;
      var head = el('div', { class: 'word' }, [
        document.createTextNode(title.text),
        el('span', { class: 'mono', text: title.pinyin }),
      ]);
      var box = document.createDocumentFragment();
      box.appendChild(head);
      box.appendChild(notes);
      openSheet('Word', '字词', box);
    });

    // Font choices, shown inside the More menu.
    function fontPanel() {
      var grid = el('div', { class: 'fonts' });
      FONTS.forEach(function (f) {
        loadFontCss(f);
        var b = el('button', { type: 'button', 'data-font': f.key }, [
          el('span', { class: 's', text: poem.sample, style: "font-family:'" + f.family + "',serif" }),
          el('span', { class: 'n', lang: 'zh', text: f.zh }),
          el('span', { class: 'n', lang: 'en', text: f.en }),
        ]);
        b.addEventListener('click', function () {
          applyFont(f.key);
          store('shi.font', f.key);
        });
        grid.appendChild(b);
      });
      return grid;
    }

    // Read aloud. By default the device's own Chinese voice (the one set in its settings);
    // the More menu can switch to a Google Mandarin voice where the browser has one.
    var speakBtn = document.getElementById('btn-speak');
    var synth = window.speechSynthesis;
    var speaking = false;
    var SAMPLE = poem.speak[0];
    if (synth) synth.getVoices(); // Chrome loads its voice list on the first ask
    function googleVoices() {
      return (synth ? synth.getVoices() : []).filter(function (v) {
        return /google/i.test(v.name) && /^zh[-_]CN/i.test(v.lang);
      });
    }
    // The saved choice, if this browser still has that voice; null means the device default.
    function chosenVoice() {
      var uri = store('shi.voice');
      return uri ? googleVoices().filter(function (v) { return v.voiceURI === uri; })[0] || null : null;
    }
    function utter(text, voice) {
      var u = new SpeechSynthesisUtterance(text);
      u.lang = 'zh-CN';
      if (voice) u.voice = voice;
      u.rate = 0.75;
      return u;
    }
    function stopSpeaking() {
      speaking = false;
      if (synth) synth.cancel();
      lines.forEach(function (l) { l.classList.remove('speaking'); });
      if (speakBtn) speakBtn.setAttribute('aria-pressed', 'false');
    }
    if (speakBtn) {
      if (!synth || !window.SpeechSynthesisUtterance) {
        speakBtn.disabled = true;
      } else {
        speakBtn.addEventListener('click', function () {
          if (speaking) return stopSpeaking();
          synth.cancel();
          speaking = true;
          speakBtn.setAttribute('aria-pressed', 'true');
          var voice = chosenVoice();
          var parts = [{ text: poem.speakTitle, line: -1 }].concat(
            poem.speak.map(function (t, i) { return { text: t, line: i }; })
          );
          parts.forEach(function (part, idx) {
            var u = utter(part.text, voice);
            u.onstart = function () {
              lines.forEach(function (l) { l.classList.remove('speaking'); });
              if (part.line >= 0 && lines[part.line]) {
                lines[part.line].classList.add('speaking');
              }
            };
            if (idx === parts.length - 1) u.onend = stopSpeaking;
            synth.speak(u);
          });
        });
        window.addEventListener('pagehide', stopSpeaking);
      }
    }

    // Voice choices, shown inside the More menu: the device default, or a Google Mandarin
    // voice. Tapping one plays a sample.
    function voicePanel() {
      var box = el('div', { class: 'voices' });
      if (!synth || !window.SpeechSynthesisUtterance) {
        box.appendChild(el('p', { class: 'mono' }, [bi('This browser cannot read aloud.', '这个浏览器不能朗读。')]));
        return box;
      }
      var current = chosenVoice();
      var options = [{ voice: null, en: 'Device voice', zh: '系统默认',
        noteEn: 'The Chinese voice set in this device’s settings.', noteZh: '用这台设备设置里选的中文声音。' }]
        .concat(googleVoices().map(function (v) {
          return { voice: v, en: v.name, zh: v.name, noteEn: 'Online voice from Google.', noteZh: 'Google 的联网语音。' };
        }));
      function mark() {
        box.querySelectorAll('button').forEach(function (b, i) {
          b.setAttribute('aria-pressed', String(options[i].voice === current));
        });
      }
      options.forEach(function (o) {
        var b = el('button', { type: 'button' }, [
          el('b', {}, [bi(o.en, o.zh)]),
          el('span', { class: 'mono' }, [bi(o.noteEn, o.noteZh)]),
        ]);
        b.addEventListener('click', function () {
          current = o.voice;
          store('shi.voice', o.voice ? o.voice.voiceURI : '');
          mark();
          synth.cancel();
          synth.speak(utter(SAMPLE, o.voice));
        });
        box.appendChild(b);
      });
      if (options.length === 1) {
        box.appendChild(el('p', { class: 'mono' }, [bi(
          'This browser has no Google Mandarin voice. Chrome on a computer or on Android has one.',
          '这个浏览器没有 Google 普通话语音。电脑或安卓手机上的 Chrome 才有。')]));
      }
      mark();
      return box;
    }

    // More menu: one row per setting with its current value; a row opens that setting's
    // choices, with a way back to the menu.
    var moreBtn = document.getElementById('btn-more');
    function openMore() {
      var font = FONTS.filter(function (f) { return f.key === root.dataset.font; })[0] || FONTS[0];
      var voice = chosenVoice();
      var rows = [
        { en: 'Font', zh: '字体', nowEn: font.en, nowZh: font.zh, titleEn: 'Font', titleZh: '字体', panel: fontPanel,
          after: function () { applyFont(root.dataset.font); } },
        { en: 'Voice', zh: '声音', nowEn: voice ? voice.name : 'Device voice', nowZh: voice ? voice.name : '系统默认',
          titleEn: 'Voice', titleZh: '声音', panel: voicePanel },
      ];
      var menu = el('div', { class: 'menu' });
      rows.forEach(function (r) {
        var b = el('button', { type: 'button' }, [
          el('b', {}, [bi(r.en, r.zh)]),
          el('span', { class: 'now' }, [bi(r.nowEn, r.nowZh)]),
          el('span', { class: 'go', 'aria-hidden': 'true', text: '›' }),
        ]);
        b.addEventListener('click', function () {
          var back = el('button', { type: 'button', class: 'back' }, [bi('‹ Back', '‹ 返回')]);
          back.addEventListener('click', openMore);
          var view = el('div', {}, [back, r.panel()]);
          openSheet(r.titleEn, r.titleZh, view);
          if (r.after) r.after();
        });
        menu.appendChild(b);
      });
      openSheet('More', '更多', menu);
    }
    if (moreBtn)
      moreBtn.addEventListener('click', function () {
        stopSpeaking();
        openMore();
      });
  }

  /* ---------- Home: tabs (the index page runs its own) ---------- */
  document.querySelectorAll('.tabs:not([data-own])').forEach(function (tabs) {
    var buttons = tabs.querySelectorAll('[role=tab]');
    function show(id) {
      buttons.forEach(function (b) {
        var on = b.getAttribute('aria-controls') === id;
        b.setAttribute('aria-selected', String(on));
        document.getElementById(b.getAttribute('aria-controls')).hidden = !on;
      });
      store('shi.tab', id);
    }
    buttons.forEach(function (b) {
      b.addEventListener('click', function () { show(b.getAttribute('aria-controls')); });
    });
    var saved = store('shi.tab');
    if (saved && document.getElementById(saved)) show(saved);
  });

  /* ---------- Home: search ---------- */
  var input = document.getElementById('q');
  if (input) {
    var results = document.getElementById('results');
    var browse = document.getElementById('browse');
    var clear = document.querySelector('.search .clear');
    var index = null;
    var loading = null;

    function load() {
      if (!loading) {
        loading = getJSON(BASE + 'data/search.json').then(function (d) {
          index = d;
        });
      }
      return loading;
    }

    function norm(s) {
      return s.toLowerCase().replace(/[\s'’·,，.。]/g, '');
    }

    function score(p, q, han) {
      var s = 0;
      if (han) {
        if (p.t === q) s = 100;
        else if (p.t.indexOf(q) === 0) s = 85;
        else if (p.t.indexOf(q) >= 0) s = 70;
        else if (p.a === q) s = 60;
        else if (p.x.indexOf(q) >= 0) s = 40;
        else if (p.a.indexOf(q) >= 0) s = 30;
      } else {
        if (p.tp === q || p.ti === q) s = 95;
        else if (p.tp.indexOf(q) === 0) s = 80;
        else if (q.length >= 2 && p.ti.indexOf(q) === 0) s = 75;
        else if (p.ap === q || (q.length >= 2 && p.ai === q)) s = 60;
        else if (p.tp.indexOf(q) >= 0) s = 45;
        else if (p.ap.indexOf(q) === 0) s = 40;
      }
      if (s && p.d) s += 8;
      if (s && p.r) s += Math.max(0, 6 - p.r / 20);
      return s;
    }

    function snippet(p, q, han) {
      // Show the line that matched, or the opening line.
      var ls = p.x.split(' ');
      var line = ls[0];
      if (han) {
        for (var i = 0; i < ls.length; i++) {
          if (ls[i].indexOf(q) >= 0) { line = ls[i]; break; }
        }
      }
      var f = el('span', { class: 'fl' });
      var at = han ? line.indexOf(q) : -1;
      if (at >= 0) {
        f.appendChild(document.createTextNode(line.slice(0, at)));
        f.appendChild(el('mark', { text: q }));
        f.appendChild(document.createTextNode(line.slice(at + q.length)));
      } else {
        f.textContent = line;
      }
      return f;
    }

    function row(p, q, han) {
      var tt = el('span', { class: 'tt' }, [document.createTextNode(p.t), el('small', { text: p.a })]);
      if (!p.d) {
        tt.appendChild(el('span', { class: 'pending', lang: 'zh', text: '精读制作中' }));
        tt.appendChild(el('span', { class: 'pending', lang: 'en', text: 'notes coming' }));
      }
      return el('li', {}, [
        el('a', { href: BASE + 'p/' + p.s + '/' }, [
          el('span', { class: 'rk mono', text: p.k === 'ci' ? '词' : '诗' }),
          tt,
          snippet(p, q, han),
        ]),
      ]);
    }

    function run() {
      var raw = input.value.trim();
      clear.hidden = !raw;
      if (!raw) {
        results.hidden = true;
        browse.hidden = false;
        return;
      }
      load().then(function () {
        var q = norm(raw);
        var han = /[㐀-鿿]/.test(q);
        var hits = [];
        index.forEach(function (p) {
          var s = score(p, q, han);
          if (s) hits.push([s, p]);
        });
        hits.sort(function (a, b) { return b[0] - a[0]; });
        results.innerHTML = '';
        var head = el('p', { class: 'mono' });
        head.appendChild(bi(hits.length + ' found', '找到 ' + hits.length + ' 首'));
        results.appendChild(head);
        if (!hits.length) {
          var none = el('p', { class: 'none' });
          none.appendChild(bi('Nothing found. Try a title, a poet, a line, or pinyin such as jys.',
            '没有找到。可以试试标题、作者、诗句，或者拼音，比如 jys。'));
          results.appendChild(none);
        } else {
          var ul = el('ul', { class: 'list' });
          hits.slice(0, 60).forEach(function (h) { ul.appendChild(row(h[1], q, han)); });
          results.appendChild(ul);
        }
        results.hidden = false;
        browse.hidden = true;
      });
    }

    var timer = null;
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(run, 80);
    });
    input.addEventListener('focus', load, { once: true });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') input.blur();
    });
    clear.addEventListener('click', function () {
      input.value = '';
      run();
      input.focus();
    });
    var initial = new URLSearchParams(location.search).get('q');
    if (initial) {
      input.value = initial;
      run();
    }
  }

  /* ---------- Home: daily poem ---------- */
  var daily = document.getElementById('daily');
  if (daily) {
    var TERM_EN = {
      lichun: 'Start of Spring', yushui: 'Rain Water', jingzhe: 'Awakening of Insects', chunfen: 'Spring Equinox',
      qingming: 'Clear and Bright', guyu: 'Grain Rain', lixia: 'Start of Summer', xiaoman: 'Grain Buds',
      mangzhong: 'Grain in Ear', xiazhi: 'Summer Solstice', xiaoshu: 'Minor Heat', dashu: 'Major Heat',
      liqiu: 'Start of Autumn', chushu: 'End of Heat', bailu: 'White Dew', qiufen: 'Autumn Equinox',
      hanlu: 'Cold Dew', shuangjiang: 'Frost Descent', lidong: 'Start of Winter', xiaoxue: 'Minor Snow',
      daxue: 'Major Snow', dongzhi: 'Winter Solstice', xiaohan: 'Minor Cold', dahan: 'Major Cold',
    };
    var FEST_EN = {
      'spring-festival': 'Spring Festival', lantern: 'the Lantern Festival', duanwu: 'the Dragon Boat Festival',
      qixi: 'Qixi, the Double Seventh', midautumn: 'the Mid-Autumn Festival', chongyang: 'the Double Ninth Festival',
      'new-year-eve': "Lunar New Year's Eve", hanshi: 'Cold Food Day',
    };
    var SEASON = { spring: ['spring', '春天'], summer: ['summer', '夏天'], autumn: ['autumn', '秋天'], winter: ['winter', '冬天'] };
    var TERM_SEASON = ['spring', 'spring', 'spring', 'spring', 'spring', 'spring', 'summer', 'summer', 'summer',
      'summer', 'summer', 'summer', 'autumn', 'autumn', 'autumn', 'autumn', 'autumn', 'autumn', 'winter', 'winter',
      'winter', 'winter', 'winter', 'winter'];
    var TERM_ORDER = ['lichun', 'yushui', 'jingzhe', 'chunfen', 'qingming', 'guyu', 'lixia', 'xiaoman', 'mangzhong',
      'xiazhi', 'xiaoshu', 'dashu', 'liqiu', 'chushu', 'bailu', 'qiufen', 'hanlu', 'shuangjiang', 'lidong',
      'xiaoxue', 'daxue', 'dongzhi', 'xiaohan', 'dahan'];
    var DAYS = '初一 初二 初三 初四 初五 初六 初七 初八 初九 初十 十一 十二 十三 十四 十五 十六 十七 十八 十九 二十 廿一 廿二 廿三 廿四 廿五 廿六 廿七 廿八 廿九 三十'.split(' ');

    function iso(d) {
      var m = d.getMonth() + 1, day = d.getDate();
      return d.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
    }
    function hash(s) {
      var h = 2166136261;
      for (var i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
      return h >>> 0;
    }
    function lastOnOrBefore(list, today) {
      var hit = null;
      list.forEach(function (row) { if (row[0] <= today) hit = row; });
      return hit;
    }

    Promise.all([getJSON(BASE + 'data/calendar.json'), getJSON(BASE + 'data/daily.json')]).then(function (res) {
      var cal = res[0], poems = res[1];
      var now = new Date();
      var today = iso(now);
      var fest = cal.festivals.filter(function (f) { return f[0] === today; })[0];
      var term = cal.terms.filter(function (t) { return t[0] === today; })[0];
      var current = lastOnOrBefore(cal.terms, today);
      var season = current ? TERM_SEASON[TERM_ORDER.indexOf(current[1])] : 'spring';
      var pick = null, whyEn = '', whyZh = '';

      function choose(list) {
        return list.length ? list[hash(today) % list.length] : null;
      }
      if (fest) {
        pick = choose(poems.filter(function (p) { return p.g.festivals.indexOf(fest[1]) >= 0; }));
        whyEn = 'Today is ' + FEST_EN[fest[1]];
        whyZh = '今天是' + fest[2];
      }
      if (!pick && term) {
        pick = choose(poems.filter(function (p) {
          return p.g.solar_terms.indexOf(term[1]) >= 0 || p.g.festivals.indexOf(term[1]) >= 0;
        }));
        whyEn = 'Today is ' + TERM_EN[term[1]] + ', a solar term';
        whyZh = '今天是' + term[2] + '节气';
      }
      if (!pick) {
        pick = choose(poems.filter(function (p) { return p.g.seasons.indexOf(season) >= 0; })) || choose(poems);
        whyEn = 'A poem for ' + SEASON[season][0];
        whyZh = '一首写' + SEASON[season][1] + '的诗';
      }
      var month = lastOnOrBefore(cal.months, today);
      var lunarZh = '', lunarEn = '';
      if (month) {
        var day = Math.round((new Date(today) - new Date(month[0])) / 86400000);
        lunarZh = '农历' + month[2] + DAYS[day];
        lunarEn = 'lunar month ' + month[1] + ', day ' + (day + 1);
      }
      var why = el('p', { class: 'why mono' });
      why.appendChild(bi(today + ' · ' + lunarEn + ' · ' + whyEn, today + ' · ' + lunarZh + ' · ' + whyZh));
      var card = el('a', { class: 'daily', href: BASE + 'p/' + pick.s + '/' }, [
        why,
        el('p', { class: 'dt', text: pick.t }),
        el('p', { class: 'da', text: pick.a }),
      ]);
      var body = el('p', { class: 'dl' });
      pick.l.forEach(function (line, i) {
        if (i) body.appendChild(el('br'));
        body.appendChild(document.createTextNode(line));
      });
      card.appendChild(body);
      var go = el('p', { class: 'go mono' });
      go.appendChild(bi('Read it closely →', '去精读 →'));
      card.appendChild(go);
      daily.innerHTML = '';
      daily.appendChild(card);
    }).catch(function () {
      daily.hidden = true;
    });
  }

  /* ---------- Index: tabs, poet filter, letter bar ---------- */
  var ixData = document.getElementById('index-data');
  if (ixData) {
    var POETS = JSON.parse(ixData.textContent).poets;
    var byName = {};
    POETS.forEach(function (p) { byName[p.n] = p; });
    var ixInput = document.getElementById('poet');
    var ixClear = document.querySelector('.ix-search .clear');
    var suggest = document.getElementById('poet-list');
    var chips = document.getElementById('chips');
    var letters = document.getElementById('letters');
    var status = document.getElementById('ix-status');
    var tabButtons = document.querySelectorAll('.tabs[data-own] [role=tab]');
    var state = { kind: 'shi', poet: null };
    var CHIP_COUNT = 8;

    function panel(kind) { return document.getElementById('ix-' + kind); }

    // Hide rows by other poets, then tunes and letter groups left empty.
    function applyFilter() {
      var p = panel(state.kind);
      p.querySelectorAll('li').forEach(function (li) {
        li.hidden = !!state.poet && li.dataset.a !== state.poet;
      });
      p.querySelectorAll('.ix-tune').forEach(function (t) {
        var n = t.querySelectorAll('li:not([hidden])').length;
        t.hidden = !n;
        t.querySelector('.n').textContent = n;
      });
      p.querySelectorAll('.ix-group').forEach(function (g) {
        g.hidden = !g.querySelector('li:not([hidden])');
      });
    }

    function renderLetters() {
      letters.innerHTML = '';
      panel(state.kind).querySelectorAll('.ix-group:not([hidden])').forEach(function (g) {
        var a = el('a', { href: '#' + g.id, text: g.dataset.letter });
        a.addEventListener('click', function (e) {
          e.preventDefault();
          g.scrollIntoView({ block: 'start' });
        });
        letters.appendChild(a);
      });
    }

    function renderStatus() {
      status.hidden = !state.poet;
      if (!state.poet) return;
      var n = byName[state.poet][state.kind];
      status.innerHTML = '';
      status.appendChild(state.kind === 'shi'
        ? bi(state.poet + ' · ' + n + ' Tang poems', state.poet + ' · 唐诗 ' + n + ' 首')
        : bi(state.poet + ' · ' + n + ' Song lyrics', state.poet + ' · 宋词 ' + n + ' 首'));
    }

    // The poets with the most poems in this tab, then a chip for the full list.
    function renderChips() {
      chips.innerHTML = '';
      POETS.filter(function (p) { return p[state.kind]; })
        .sort(function (a, b) { return b[state.kind] - a[state.kind]; })
        .slice(0, CHIP_COUNT)
        .forEach(function (p) {
          var b = el('button', { type: 'button', class: 'chip', 'aria-pressed': String(p.n === state.poet) },
            [document.createTextNode(p.n), el('span', { class: 'mono', text: String(p[state.kind]) })]);
          b.addEventListener('click', function () { pick(p.n === state.poet ? null : p.n); });
          chips.appendChild(b);
        });
      var more = el('button', { type: 'button', class: 'chip more' }, [bi('All poets ›', '全部诗人 ›')]);
      more.addEventListener('click', openPoetSheet);
      chips.appendChild(more);
    }

    function render() {
      tabButtons.forEach(function (b) {
        var on = b.dataset.kind === state.kind;
        b.setAttribute('aria-selected', String(on));
        panel(b.dataset.kind).hidden = !on;
      });
      applyFilter();
      renderLetters();
      renderStatus();
      renderChips();
      ixInput.value = state.poet || '';
      ixClear.hidden = !state.poet;
      var q = new URLSearchParams(location.search);
      q.set('tab', state.kind);
      if (state.poet) q.set('poet', state.poet); else q.delete('poet');
      history.replaceState(null, '', location.pathname + '?' + q.toString() + location.hash);
    }

    // Picking a poet with nothing in this tab switches to the tab they wrote in.
    function pick(name) {
      state.poet = name && byName[name] ? name : null;
      if (state.poet && !byName[state.poet][state.kind]) state.kind = state.kind === 'shi' ? 'ci' : 'shi';
      closeSuggest();
      render();
    }

    tabButtons.forEach(function (b) {
      b.addEventListener('click', function () {
        state.kind = b.dataset.kind;
        if (state.poet && !byName[state.poet][state.kind]) state.poet = null;
        render();
      });
    });

    // Typeahead: characters anywhere in the name, or pinyin / initials from the start.
    var active = -1, matches = [];
    function closeSuggest() {
      suggest.hidden = true;
      ixInput.setAttribute('aria-expanded', 'false');
      active = -1;
    }
    function showSuggest() {
      var q = ixInput.value.toLowerCase().replace(/[\s'’]/g, '').replace(/ü/g, 'v');
      if (!q || q === (state.poet || '')) return closeSuggest();
      matches = POETS.filter(function (p) {
        return p.n.indexOf(q) >= 0 || p.p.indexOf(q) === 0 || p.i.indexOf(q) === 0;
      }).sort(function (a, b) {
        return (b[state.kind] ? 1 : 0) - (a[state.kind] ? 1 : 0) || (b.shi + b.ci) - (a.shi + a.ci);
      }).slice(0, 8);
      suggest.innerHTML = '';
      if (!matches.length) {
        suggest.appendChild(el('li', { class: 'none' }, [bi('No poet by that name', '没有这位诗人')]));
      }
      matches.forEach(function (p, i) {
        var li = el('li', { role: 'option', id: 'poet-opt-' + i }, [
          el('b', { text: p.n }),
          el('span', { class: 'mono' }, [bi(
            [p.shi ? p.shi + ' Tang' : '', p.ci ? p.ci + ' Song' : ''].filter(Boolean).join(' · '),
            [p.shi ? '唐诗 ' + p.shi : '', p.ci ? '宋词 ' + p.ci : ''].filter(Boolean).join(' · '))]),
        ]);
        li.addEventListener('mousedown', function (e) { e.preventDefault(); pick(p.n); });
        suggest.appendChild(li);
      });
      active = -1;
      suggest.hidden = false;
      ixInput.setAttribute('aria-expanded', 'true');
    }
    function highlight(i) {
      var opts = suggest.querySelectorAll('[role=option]');
      if (!opts.length) return;
      active = (i + opts.length) % opts.length;
      opts.forEach(function (o, j) { o.setAttribute('aria-selected', String(j === active)); });
      ixInput.setAttribute('aria-activedescendant', opts[active].id);
    }
    ixInput.addEventListener('input', showSuggest);
    ixInput.addEventListener('focus', showSuggest);
    ixInput.addEventListener('blur', function () {
      closeSuggest();
      ixInput.value = state.poet || '';
    });
    ixInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); highlight(active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(active - 1); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var m = matches[active >= 0 ? active : 0];
        if (!suggest.hidden && m) { pick(m.n); ixInput.blur(); }
      } else if (e.key === 'Escape') closeSuggest();
    });
    ixClear.addEventListener('click', function () { pick(null); ixInput.focus(); });

    // Every poet in this tab, by pinyin, grouped by letter.
    function openPoetSheet() {
      var box = el('div', { class: 'poets' });
      var last = '';
      POETS.forEach(function (p) {
        if (!p[state.kind]) return;
        var letter = p.p.charAt(0).toUpperCase();
        if (letter !== last) {
          box.appendChild(el('h3', { class: 'mono', text: letter }));
          last = letter;
        }
        var b = el('button', { type: 'button', 'aria-pressed': String(p.n === state.poet) },
          [document.createTextNode(p.n), el('span', { class: 'mono', text: String(p[state.kind]) })]);
        b.addEventListener('click', function () { closeSheet(); pick(p.n); });
        box.appendChild(b);
      });
      openSheet(state.kind === 'shi' ? 'Tang poets' : 'Song lyricists',
        state.kind === 'shi' ? '唐诗诗人' : '宋词词人', box);
    }

    var q0 = new URLSearchParams(location.search);
    state.kind = q0.get('tab') === 'ci' ? 'ci' : 'shi';
    pick(q0.get('poet'));
  }

  /* ---------- Saved font, applied on every page ---------- */
  applyFont(store('shi.font') || (FONTS[0] && FONTS[0].key));
})();
