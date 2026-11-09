"""双模式、阶段导航、阶段0参数页；阶段1～4先放占位。"""
from pathlib import Path
import gradio as gr
import experiment
import stages
from tasks import TASKS, DEFAULTS, CHECK_BY_TASK, visible_question

LATEX_DELIMITERS = [
    {"left": "\\(", "right": "\\)", "display": False},
    {"left": "\\[", "right": "\\]", "display": True},
    {"left": "$$", "right": "$$", "display": True},
]


def md(value="", **kwargs):
    return gr.Markdown(value, latex_delimiters=LATEX_DELIMITERS, **kwargs)


def _student_manual():
    text = (Path(__file__).resolve().parent / "knowledge" / "torsion_pendulum.md").read_text(encoding="utf-8")
    text = text.split("## 工具结果")[0].rstrip()
    return text.replace("\\[", "$$").replace("\\]", "$$")


MANUAL = _student_manual()

ONBOARDING_MD = r"""
### 3 分钟上手

1. **选模式**：真实实验模式用来记录你自己测的数据；虚拟实验模式的器材参数由程序给定，数据由点击测量生成。
2. **阶段0 器材参数**：登记质量、直径、长度和测量设置。参数随时可改、可追加；每保存一次生成一个新版本，旧版本保留。
3. **阶段1 标定**：空盘和加圆柱，不限组数；学生填 \(I_1\)、\(K\)、\(I_0\)，由程序算不确定度和有效数字；先点「核对结果（本地）」，再需要时点「请 AI 解释」。
4. **阶段2 规则刚体**：圆筒、球体、细杆；学生填 \(I_{\\text{实验}}\)、\(I_{\\text{几何}}\)、百分偏差，AI 检查并回答阶段问题。
5. **阶段3 平行轴**：细杆基准、五个对称距离、四组不对称；学生填 \(I_{\\text{总}}\)、斜率、截距，程序按数据画图。
6. **阶段4 图表与报告**：点击生成图表和标准实验报告草稿，不自动提交。

**参数修改**：阶段0 保存的是版本，不覆盖旧版；阶段1～3 使用你选定的“当前采用版本”。  
**问 AI**：选中页面任意文字，浮出的「询问 AI」会把这段和上下文填进问题框。  
**当前版本**：阶段0～4 均可用；虚拟模式在阶段1～3 用「生成一组数据」。
"""

HEADER_HTML = """
<header class="lab-head">
  <div class="lab-head-copy">
    <p class="eyebrow">物理教学实验 · 扭摆法</p>
    <h1>扭摆法测转动惯量</h1>
    <p class="lede">真实实验和虚拟实验分开记录；参数可改可追加，计算用你选定的版本。</p>
    <div class="chips">
      <span>真实 / 虚拟双模式</span>
      <span>阶段0～4</span>
      <span>参数版本可追加</span>
    </div>
  </div>
  <svg class="lab-head-art" viewBox="0 0 240 170" aria-hidden="true">
    <circle cx="150" cy="28" r="9" fill="none" stroke="#e7c7a4" stroke-width="2"/>
    <path d="M150 37 L150 88" stroke="#e7c7a4" stroke-width="2" stroke-dasharray="4 4"/>
    <ellipse cx="150" cy="98" rx="70" ry="14" fill="none" stroke="#e7c7a4" stroke-width="2"/>
    <ellipse cx="150" cy="98" rx="26" ry="5" fill="#e7c7a4" opacity="0.35"/>
    <path d="M80 98 L220 98" stroke="#e7c7a4" stroke-width="2"/>
    <rect x="112" y="54" width="18" height="30" rx="4" fill="#e7c7a4" opacity="0.65"/>
    <rect x="188" y="54" width="18" height="30" rx="4" fill="#e7c7a4" opacity="0.65"/>
    <path d="M150 112 A 62 62 0 0 1 201 132" fill="none" stroke="#e7c7a4" stroke-width="1.6"/>
  </svg>
</header>
"""

MODE_NOTE = ("**真实实验模式**：参数、周期、计算结果都由你填写和保存。  \n"
             "**虚拟实验模式**：器材参数由程序给定，只读；周期由点击测量生成。")
PRE_START_MD = "填学号，点「开始学习」。开始后先到 **阶段0 器材参数** 登记本次实验的器材。"

PAGE_JS = """
() => {
  document.documentElement.style.colorScheme = 'light';
  document.documentElement.classList.remove('dark');
  document.body.classList.remove('dark');
  if (!window.__tutorKeys) {
    window.__tutorKeys = true;
    const shown = (node) => {
      if (!node) return false;
      const style = window.getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
      return node.getClientRects().length > 0;
    };
    const buttonOf = (id) => {
      const node = document.getElementById(id);
      if (!node) return null;
      return node.tagName === 'BUTTON' ? node : node.querySelector('button');
    };
    const typing = (el) => {
      if (!el) return false;
      const tag = el.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable;
    };
    let returnFocus = null;
    let wasOpen = false;
    const makeResizable = (dock) => {
      if (!dock || dock.__edgeResize || window.innerWidth <= 860) return;
      dock.__edgeResize = true;
      const EDGE = 8, MIN_W = 320, MIN_H = 400;
      let drag = null;
      const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
      const cursorFor = (hit) => {
        if ((hit.left && hit.top) || (hit.right && hit.bottom)) return 'nwse-resize';
        if ((hit.right && hit.top) || (hit.left && hit.bottom)) return 'nesw-resize';
        if (hit.left || hit.right) return 'ew-resize';
        return 'ns-resize';
      };
      const atEdge = (event) => {
        const rect = dock.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const hit = {
          left: x <= EDGE,
          right: x >= rect.width - EDGE,
          top: y <= EDGE,
          bottom: y >= rect.height - EDGE,
        };
        return (hit.left || hit.right || hit.top || hit.bottom) ? hit : null;
      };
      const onPointerMove = (event) => {
        if (drag) return;
        const hit = atEdge(event);
        dock.style.cursor = hit ? cursorFor(hit) : '';
        dock.classList.toggle('tutor-resize-hover', !!hit);
      };
      const onPointerDown = (event) => {
        if (event.button !== 0 || window.innerWidth <= 860) return;
        const hit = atEdge(event);
        if (!hit) return;
        event.preventDefault();
        event.stopPropagation();
        const rect = dock.getBoundingClientRect();
        drag = {
          hit, startX: event.clientX, startY: event.clientY,
          width: rect.width, height: rect.height, top: rect.top,
        };
        dock.classList.add('tutor-resizing');
        dock.style.cursor = cursorFor(hit);
        document.body.style.userSelect = 'none';
        window.addEventListener('pointermove', onPointerDrag, true);
        window.addEventListener('pointerup', stopDrag, true);
      };
      const onPointerDrag = (event) => {
        if (!drag) return;
        event.preventDefault();
        const dx = event.clientX - drag.startX;
        const dy = event.clientY - drag.startY;
        const maxW = Math.max(MIN_W, window.innerWidth - 24);
        const maxH = Math.max(MIN_H, window.innerHeight - 24);
        let width = drag.width;
        let height = drag.height;
        let top = drag.top;
        if (drag.hit.left) width = clamp(drag.width - dx, MIN_W, maxW);
        else if (drag.hit.right) width = clamp(drag.width + dx, MIN_W, maxW);
        if (drag.hit.top) {
          height = clamp(drag.height - dy, MIN_H, maxH);
          top = clamp(drag.top + (drag.height - height), 12,
                      Math.max(12, window.innerHeight - 12 - height));
        } else if (drag.hit.bottom) {
          height = clamp(drag.height + dy, MIN_H, maxH);
        }
        dock.style.width = width + 'px';
        dock.style.height = height + 'px';
        if (drag.hit.top) dock.style.top = top + 'px';
      };
      const stopDrag = () => {
        if (!drag) return;
        drag = null;
        dock.classList.remove('tutor-resizing');
        dock.style.cursor = '';
        document.body.style.userSelect = '';
        window.removeEventListener('pointermove', onPointerDrag, true);
        window.removeEventListener('pointerup', stopDrag, true);
      };
      dock.addEventListener('pointermove', onPointerMove);
      dock.addEventListener('pointerdown', onPointerDown, true);
      dock.addEventListener('pointerleave', () => {
        if (!drag) {
          dock.style.cursor = '';
          dock.classList.remove('tutor-resize-hover');
        }
      });
    };
    const watch = new MutationObserver(() => {
      const dock = document.getElementById('tutor-dock');
      if (dock) makeResizable(dock);
      const open = !!(dock && dock.classList.contains('tutor-open') && shown(dock));
      document.body.classList.toggle('tutor-open-page', open);
      if (open && !wasOpen) {
        setTimeout(() => {
          const box = document.querySelector('#ask-box textarea, #ask-box input');
          if (box) box.focus();
        }, 60);
      }
      if (!open && wasOpen) {
        const back = returnFocus;
        setTimeout(() => {
          if (back && typeof back.focus === 'function') back.focus();
          else {
            const launch = buttonOf('tutor-open');
            if (launch) launch.focus();
          }
        }, 40);
      }
      wasOpen = open;
    });
    const arm = () => {
      const dock = document.getElementById('tutor-dock');
      if (!dock) { setTimeout(arm, 300); return; }
      makeResizable(dock);
      watch.observe(dock, {attributes: true, attributeFilter: ['class', 'style']});
    };
    arm();
    document.addEventListener('click', (event) => {
      const launch = event.target.closest && event.target.closest('#tutor-open');
      if (launch) returnFocus = buttonOf('tutor-open') || launch;
    }, true);
    document.addEventListener('keydown', (event) => {
      const dock = document.getElementById('tutor-dock');
      const open = !!(dock && dock.classList.contains('tutor-open') && shown(dock));
      if (event.key === 'Escape' && open) {
        const close = buttonOf('tutor-close');
        if (close && shown(close)) {
          event.preventDefault();
          close.click();
        }
        return;
      }
      const askKey = event.key === '?' || event.key === '？';
      if (askKey && !event.ctrlKey && !event.metaKey && !event.altKey && !typing(event.target)) {
        const launch = buttonOf('tutor-open');
        if (launch && shown(launch)) {
          event.preventDefault();
          returnFocus = document.activeElement;
          launch.click();
        }
      }
    });
  }

  if (window.__askSelection) return;
  window.__askSelection = true;
  const pill = document.createElement('div');
  pill.className = 'ask-pop';
  pill.innerHTML = '<button type="button">✨ 询问 AI</button>';
  document.body.appendChild(pill);

  let payload = null;
  let hideTimer = null;
  let suppress = 0;
  const hide = () => {
    pill.style.display = 'none';
    payload = null;
  };
  const editable = (el) => !!(el && el.closest('input, textarea, [contenteditable="true"]'));
  const panelMap = [
    ['#params-panel', 'measure', '器材参数'],
    ['#version-panel', 'measure', '参数版本'],
    ['#param-preview', 'measure', '参数预览'],
    ['#stage-hint', 'task', '阶段说明'],
    ['#tutor-dock', 'chat', '助教对话'],
  ];
  const panelOf = (el) => {
    for (const [selector, panel, label] of panelMap) {
      const box = el.closest(selector);
      if (box) return {panel, label, box};
    }
    return {panel: 'generic', label: '页面', box: document.body};
  };
  const headingOf = (el, stop) => {
    let node = el;
    while (node && node !== stop && node !== document.body) {
      let prev = node.previousElementSibling;
      while (prev) {
        if (/^H[1-6]$/.test(prev.tagName)) {
          const text = (prev.textContent || '').replace(/\\s+/g, ' ').trim();
          if (text) return text.slice(0, 80);
        }
        prev = prev.previousElementSibling;
      }
      node = node.parentElement;
    }
    return '';
  };
  const capture = () => {
    if (Date.now() < suppress) return hide();
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return hide();
    const range = selection.getRangeAt(0);
    const node = range.startContainer;
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el || editable(el)) return hide();
    const fragment = range.cloneContents();
    fragment.querySelectorAll('.katex-mathml').forEach((item) => item.remove());
    let text = (fragment.textContent || '').replace(/\\s+/g, ' ').trim();
    const katexNodes = [...document.querySelectorAll('.katex')].filter((item) => {
      try { return range.intersectsNode(item); } catch (error) { return false; }
    });
    const endNode = range.endContainer;
    const endEl = endNode.nodeType === 1 ? endNode : endNode.parentElement;
    const touchedKatex = el.closest('.katex') || (endEl && endEl.closest('.katex'));
    const inFormulaPanel = !!(el.closest('#formula-panel') ||
      (endEl && endEl.closest('#formula-panel')));
    if ((touchedKatex || inFormulaPanel) && katexNodes.length) {
      const latex = katexNodes.map((item) => {
        const annotation = item.querySelector('annotation[encoding="application/x-tex"]');
        return annotation ? annotation.textContent.trim() : '';
      }).filter(Boolean);
      if (latex.length) {
        text = latex.map((item) => '\\\\(' + item + '\\\\)').join('；');
      }
    }
    if (text.length < 2) return hide();
    const info = panelOf(el);
    const rects = range.getClientRects();
    const rect = rects.length ? rects[rects.length - 1] : range.getBoundingClientRect();
    if (!rect || (!rect.width && !rect.height)) return hide();
    const block = el.closest('[id]') || info.box;
    const blockText = (block.textContent || '').replace(/\\s+/g, ' ').trim();
    const index = blockText.indexOf(text);
    payload = {
      text: text.slice(0, 600),
      panel: info.panel,
      label: headingOf(el, info.box) || info.label,
      case_id: null,
      before: index > 0 ? blockText.slice(Math.max(0, index - 240), index) : '',
      after: index >= 0 ? blockText.slice(index + text.length, index + text.length + 240) : '',
    };
    pill.style.display = 'block';
    const top = Math.min(window.innerHeight - 52, rect.bottom + 8);
    const left = Math.min(window.innerWidth - 132, Math.max(8, rect.left));
    pill.style.top = Math.max(8, top) + 'px';
    pill.style.left = left + 'px';
  };
  document.addEventListener('mouseup', () => {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(capture, 80);
  }, true);
  document.addEventListener('keyup', (event) => {
    if (event.key === 'Shift' || event.shiftKey) {
      clearTimeout(hideTimer);
      hideTimer = setTimeout(capture, 80);
    }
  }, true);
  pill.addEventListener('mousedown', (event) => event.preventDefault());
  pill.addEventListener('click', () => {
    if (!payload) return;
    suppress = Date.now() + 600;
    const sink = document.querySelector('#cite-text textarea, #cite-text input');
    const fireNode = document.getElementById('cite-selection');
    const fire = fireNode && (fireNode.tagName === 'BUTTON'
      ? fireNode : fireNode.querySelector('button'));
    if (!sink || !fire) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(sink, JSON.stringify(payload));
    sink.dispatchEvent(new Event('input', {bubbles: true}));
    sink.dispatchEvent(new Event('change', {bubbles: true}));
    fire.click();
    setTimeout(() => {
      const box = document.querySelector('#ask-box textarea, #ask-box input');
      if (box) box.focus();
    }, 1000);
    hide();
  });
  document.addEventListener('mousedown', (event) => {
    if (!pill.contains(event.target)) hide();
  }, true);
  document.addEventListener('scroll', hide, true);
  window.addEventListener('resize', hide);
}
"""

THEME = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="stone",
    neutral_hue="stone",
    text_size="lg",
    radius_size="lg",
    spacing_size="md",
).set(
    body_background_fill="#efe6da",
    body_text_color="#1f2a30",
    body_text_size="17px",
    block_background_fill="#fffdf8",
    block_border_color="#e4d9cc",
    block_border_width="1px",
    block_label_text_size="15px",
    block_title_text_size="18px",
    block_label_text_color="#3d4a46",
    input_background_fill="#fffdf8",
    input_text_size="17px",
    button_large_text_size="18px",
    button_small_text_size="15px",
    button_primary_background_fill="#1f6f6a",
    button_primary_background_fill_hover="#185e59",
    button_primary_text_color="#fffdf8",
    button_secondary_background_fill="#f3ece3",
    button_secondary_text_color="#1f2a30",
    button_secondary_border_color="#e4d9cc",
    shadow_drop="0 10px 28px rgba(48, 36, 24, 0.06)",
    input_placeholder_color="#6d675f",
    body_background_fill_dark="#efe6da",
    body_text_color_dark="#1f2a30",
    block_background_fill_dark="#fffdf8",
    block_border_color_dark="#e4d9cc",
    input_background_fill_dark="#fffdf8",
    button_primary_background_fill_dark="#1f6f6a",
    button_primary_text_color_dark="#fffdf8",
    button_secondary_background_fill_dark="#f3ece3",
    button_secondary_text_color_dark="#1f2a30",
)

CSS = """
:root, body, .gradio-container { color-scheme: light !important; }
body { background: #efe6da !important; color: #1f2a30 !important; }
.gradio-container {
    max-width: 1360px !important;
    --font: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
    --body-text-color: #1f2a30;
    --body-text-color-subdued: #5c564e;
    --block-title-text-color: #1b3a4b;
    --block-info-text-color: #5c564e;
    --input-background-fill: #fffdf8;
    --block-background-fill: #fffdf8;
    --background-fill-primary: #efe6da;
    --background-fill-secondary: #fffdf8;
    --color-accent: #1f6f6a;
    color: #1f2a30 !important;
    background:
        radial-gradient(900px 320px at 8% -8%, rgba(31, 111, 106, 0.10), transparent 62%),
        radial-gradient(800px 280px at 100% 0%, rgba(184, 92, 56, 0.07), transparent 60%),
        #efe6da !important;
    padding: 10px 18px 48px;
    box-sizing: border-box;
}
.lab-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 18px;
    align-items: center;
    background:
        radial-gradient(600px 200px at 90% 10%, rgba(231, 199, 164, 0.18), transparent 60%),
        linear-gradient(135deg, #16323f 0%, #1b4b50 55%, #1f6f6a 100%);
    color: #f7f1e8;
    margin: 8px 0 14px;
    padding: 26px 32px 24px;
    border-radius: 24px;
    box-shadow: 0 18px 44px rgba(27, 58, 75, 0.20);
}
.lab-head-copy { min-width: 0; }
header.lab-head h1, header.lab-head p {
    color: #f7f1e8 !important;
    -webkit-text-fill-color: #f7f1e8 !important;
}
header.lab-head .eyebrow {
    margin: 0 0 8px; font-size: 13px; letter-spacing: 0.18em;
    color: #e7c7a4 !important; -webkit-text-fill-color: #e7c7a4 !important;
}
header.lab-head h1 { margin: 0 0 8px; font-size: 34px; line-height: 1.25; font-weight: 700; }
header.lab-head .lede { margin: 0 0 14px; font-size: 16px; line-height: 1.7; }
header.lab-head .chips { display: flex; flex-wrap: wrap; gap: 8px; }
header.lab-head .chips span {
    display: inline-flex; align-items: center; padding: 5px 11px;
    border-radius: 999px; border: 1px solid rgba(247, 241, 232, 0.28);
    background: rgba(247, 241, 232, 0.10); color: #f7f1e8; font-size: 12px;
}
.lab-head-art { width: 220px; height: auto; opacity: 0.9; }
#session-bar {
    background: rgba(255, 253, 248, 0.96) !important;
    border: 1px solid #e4d9cc; border-radius: 18px;
    padding: 10px 14px; margin: 0 0 10px;
    box-shadow: 0 8px 22px rgba(48, 36, 24, 0.05);
}
#session-bar .session-row { align-items: center; gap: 8px; }
#session-bar .session-actions { justify-content: flex-end; gap: 8px; }
#onboarding {
    background: #fffdf8 !important; border: 1px solid #e4d9cc;
    border-radius: 18px; margin: 0 0 12px;
    box-shadow: 0 10px 26px rgba(48, 36, 24, 0.05);
}
#onboarding .label-wrap { font-size: 17px; font-weight: 700; color: #1b3a4b !important; }
#onboarding-md p, #onboarding-md li { font-size: 16px; line-height: 1.75; }
#mode-row, #stage-row {
    background: #fffdf8 !important; border: 1px solid #e4d9cc;
    border-radius: 18px; padding: 10px 16px; margin: 0 0 10px;
    align-items: flex-start; gap: 16px;
    box-shadow: 0 8px 20px rgba(48, 36, 24, 0.04);
}
#mode-select, #stage-select { background: transparent !important; border: none !important; flex: 1; }
#mode-select .wrap, #stage-select .wrap { flex-wrap: wrap !important; gap: 6px !important; }
#mode-select label, #stage-select label {
    border: 1px solid #e4d9cc; background: #fffdf8; border-radius: 999px;
    padding: 8px 13px !important; cursor: pointer; transition: all 0.18s ease;
}
#mode-select label:hover, #stage-select label:hover { border-color: #1f6f6a; }
#mode-select label:has(input:checked), #stage-select label:has(input:checked) {
    background: #1f6f6a; border-color: #1f6f6a; color: #fffdf8 !important;
    box-shadow: 0 8px 18px rgba(31, 111, 106, 0.20);
}
#mode-select label:has(input:checked) span,
#stage-select label:has(input:checked) span { color: #fffdf8 !important; }
#mode-note p { font-size: 13px; line-height: 1.6; color: #5c564e !important; margin: 2px 0; }
#stage-hint p, #learning-status p {
    font-size: 14px; line-height: 1.65; color: #3d4a46 !important;
    -webkit-text-fill-color: #3d4a46 !important; margin: 2px 0 6px;
}
#pre-start p {
    margin: 4px 0 12px; padding: 12px 16px; background: #eaf4f0;
    border-left: 5px solid #1f6f6a; border-radius: 12px; font-size: 15px;
}
#page-row { align-items: flex-start !important; gap: 18px; }
#work-column { min-width: 0 !important; }
.section-head { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
.section-head h3 { margin: 4px 0 4px; font-size: 24px; color: #1b3a4b; }
.section-head p { margin: 0; color: #5c564e; font-size: 15px; line-height: 1.65; }
.card, #params-panel .card, #later-panel .card, #version-panel, #param-preview {
    background: #fffdf8 !important; border: 1px solid #e4d9cc; border-radius: 18px;
    padding: 14px 18px 16px; margin: 8px 0 12px;
    box-shadow: 0 10px 26px rgba(48, 36, 24, 0.05);
}
.card h3, #version-panel h3, #param-preview h3 {
    margin: 2px 0 8px; font-size: 19px; color: #1b3a4b;
}
#param-preview table, #param-versions table, #virtual-params table {
    display: table !important;
    width: 100% !important; border-collapse: collapse; font-size: 14px; margin: 8px 0;
}
.gradio-container .prose table { display: table !important; width: 100% !important; }
#param-preview th, #param-versions th, #virtual-params th {
    background: #f3ece3; color: #1b3a4b; font-weight: 700; text-align: left;
}
#param-preview th, #param-preview td, #param-versions th, #param-versions td,
#virtual-params th, #virtual-params td {
    border: 1px solid #e4d9cc; padding: 7px 9px; vertical-align: top;
}
#param-preview tr:nth-child(even) td, #param-versions tr:nth-child(even) td,
#virtual-params tr:nth-child(even) td { background: #fbf6ee; }
#param-active p {
    margin: 2px 0 10px; padding: 9px 12px; background: #e6f3ee;
    border-left: 4px solid #1f6f6a; border-radius: 9px; font-size: 14px;
}
#param-preview p, #param-preview li { font-size: 14px; line-height: 1.65; }
#stage-placeholder p, #stage-placeholder li { font-size: 15px; line-height: 1.8; }
#tutor-open {
    position: fixed !important; right: 18px !important; bottom: 18px !important;
    left: auto !important; top: auto !important; width: max-content !important;
    min-width: 0 !important; z-index: 45; margin: 0 !important;
    box-shadow: 0 12px 30px rgba(27, 58, 75, 0.22); border-radius: 999px !important;
}
#tutor-dock, #tutor-dock.tutor-open {
    position: fixed !important; top: 12px; right: 12px; bottom: auto;
    left: auto !important; width: min(410px, calc(100vw - 24px));
    min-width: 320px; max-width: calc(100vw - 24px);
    height: min(760px, calc(100vh - 24px)); min-height: 400px;
    max-height: calc(100vh - 24px);
    z-index: 50; margin: 0 !important; overflow: auto;
    display: flex !important; flex-direction: column !important;
    align-items: stretch !important; gap: 8px;
    resize: none; box-sizing: border-box;
    background: #fffdf8 !important; border: 1px solid #e4d9cc; border-radius: 18px;
    padding: 10px 14px 14px; box-shadow: 0 24px 60px rgba(48, 36, 24, 0.24);
}
#tutor-dock > .wrap.hide { display: none !important; }
#tutor-dock #tutor-head { flex: 0 0 auto; width: 100% !important; }
#tutor-dock #tutor-chat { flex: 1 1 0 !important; width: 100% !important;
    min-height: 240px !important; height: auto !important; }
#tutor-dock #tutor-chat .bubble-wrap { height: 100% !important; }
#tutor-dock.tutor-resize-hover { border-color: #1f6f6a !important; }
#tutor-dock.tutor-resizing {
    border-color: #1f6f6a !important;
    box-shadow: 0 24px 60px rgba(48, 36, 24, 0.32);
}
#tutor-head { align-items: center; gap: 8px; }
#tutor-head .prose { flex: 1; }
#tutor-head h3 { margin: 0; font-size: 20px; color: #1b3a4b; }
#tutor-head p { margin: 2px 0 0; font-size: 13px; color: #5c564e; }
#tutor-close { min-width: 64px; }
body:has(#tutor-dock.tutor-open) .gradio-container {
    padding-right: min(430px, 46vw); box-sizing: border-box;
}
body:has(#tutor-dock.tutor-open) .lab-head { grid-template-columns: 1fr; }
body:has(#tutor-dock.tutor-open) .lab-head-art { display: none; }
body:has(#tutor-dock.tutor-open) #mode-select label,
body:has(#tutor-dock.tutor-open) #stage-select label { font-size: 14px; padding: 6px 9px !important; }
.gradio-container label, .gradio-container .label-wrap span {
    color: #3d4a46 !important; -webkit-text-fill-color: #3d4a46 !important;
}
.gradio-container input, .gradio-container textarea {
    background-color: #fffdf8 !important; color: #1f2a30 !important;
    -webkit-text-fill-color: #1f2a30 !important; caret-color: #1f2a30;
    border-radius: 10px !important;
}
.gradio-container input::placeholder, .gradio-container textarea::placeholder {
    color: #6d675f !important; -webkit-text-fill-color: #6d675f !important; opacity: 1 !important;
}
.ask-pop { position: fixed; z-index: 90; display: none; margin: 0; padding: 0; }
.ask-pop button {
    border: none; border-radius: 999px; padding: 8px 14px;
    background: #1b3a4b; color: #fffdf8; font-size: 13px; font-weight: 700;
    box-shadow: 0 10px 24px rgba(27, 58, 75, 0.28); cursor: pointer;
}
.ask-pop button:hover { background: #1f6f6a; }
.ask-sink {
    display: none !important; position: fixed !important;
    left: -10000px !important; top: 0 !important;
    width: 1px !important; height: 1px !important;
    opacity: 0 !important; pointer-events: none !important;
}
@media (max-width: 980px) {
    .lab-head { grid-template-columns: 1fr; padding: 20px 18px; }
    .lab-head-art { display: none; }
    #page-row { flex-direction: column !important; }
    #mode-row, #stage-row { flex-wrap: wrap !important; }
}
@media (max-width: 860px) {
    body:has(#tutor-dock.tutor-open) { overflow: hidden; }
    body:has(#tutor-dock.tutor-open) .gradio-container { padding-right: 0 !important; }
    #tutor-dock.tutor-open {
        inset: 0 !important; z-index: 80 !important; width: 100% !important;
        max-width: none !important; height: 100% !important; min-width: 0 !important;
        min-height: 0 !important; max-height: none !important;
        border-radius: 0; resize: none !important;
        padding: 12px 12px 28px !important; box-sizing: border-box;
    }
    .lab-head h1 { font-size: 27px; }
    .gradio-container { padding: 6px 10px 40px; }
}
@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
}
"""


def render_view(state, controls):
    active, busy, ready = state["active"], state["busy"], state["ready"]
    status = state["status"]
    updates = {
        controls["student"]: gr.update(interactive=state["can_start"]),
        controls["start"]: gr.update(visible=not active, interactive=state["can_start"],
                                     variant="primary" if state["can_start"] else "secondary"),
        controls["save_line"]: state["save_line"],
        controls["new"]: gr.update(visible=active, interactive=ready),
        controls["retry"]: gr.update(visible=state["save_failed"], interactive=ready),
        controls["status"]: status,
        controls["onboarding"]: gr.update(open=state["onboarding_open"]),
        controls["pre_start"]: gr.update(visible=not active),
        controls["demo_button"]: gr.update(visible=not active, interactive=state["can_start"]),
        controls["demo_note"]: gr.update(
            visible=(not active or state["demo_mode"]),
            value=("**演示数据**：阶段1～3 的周期、学生计算和回答都已填好；"
                   "阶段3/4 的图需要点「生成」按钮。"
                   if state["demo_mode"] else
                   "想直接验收？点左边按钮，会创建一个所有阶段都填好的演示会话。")),
        controls["mode"]: gr.update(value=state["mode"], interactive=ready),
        controls["stage"]: gr.update(value=state["exp_stage"], interactive=ready),
        controls["stage_hint"]: state["stage_hint"],
        controls["params_panel"]: gr.update(visible=active and state["params_visible"]),
        controls["real_params"]: gr.update(visible=active and state["real_params_visible"]),
        controls["virtual_params"]: gr.update(visible=active and state["virtual_params_visible"]),
        controls["cal_panel"]: gr.update(visible=active and state["cal_panel_visible"]),
        controls["cal_manual"]: gr.update(visible=state["real_mode"]),
        controls["cal_virtual"]: gr.update(visible=state["virtual_mode"]),
        controls["virt_cal_generate"]: gr.update(interactive=ready and state["virtual_mode"]),
        controls["cal_groups_md"]: state["cal_groups_md"],
        controls["cal_group_pick"]: gr.update(
            choices=state["cal_group_choices"], value=None, interactive=ready),
        controls["cal_preview_md"]: state["cal_preview_md"],
        controls["cal_i1"]: gr.update(value=state["cal_i1"], interactive=ready),
        controls["cal_k"]: gr.update(value=state["cal_k"], interactive=ready),
        controls["cal_i0"]: gr.update(value=state["cal_i0"], interactive=ready),
        controls["cal_check_md"]: state["cal_check_md"],
        controls["add_cal_group"]: gr.update(interactive=ready),
        controls["void_cal_group"]: gr.update(interactive=ready),
        controls["check_cal"]: gr.update(interactive=ready),
        controls["ai_cal"]: gr.update(interactive=ready and state["cal_has_check"]),
        controls["shp_panel"]: gr.update(visible=active and state["shp_panel_visible"]),
        controls["shp_manual"]: gr.update(visible=state["real_mode"]),
        controls["shp_virtual"]: gr.update(visible=state["virtual_mode"]),
        controls["virt_shp_generate"]: gr.update(interactive=ready and state["virtual_mode"]),
        controls["shp_groups_md"]: state["shp_groups_md"],
        controls["shp_group_pick"]: gr.update(
            choices=state["shp_group_choices"], value=None, interactive=ready),
        controls["shp_preview_md"]: state["shp_preview_md"],
        controls["shp_table"]: gr.update(value=state["shp_table"], interactive=ready),
        controls["shp_check_md"]: state["shp_check_md"],
        controls["shp_q1"]: gr.update(value=state["shp_q1"], interactive=ready),
        controls["shp_q2"]: gr.update(value=state["shp_q2"], interactive=ready),
        controls["shp_q3"]: gr.update(value=state["shp_q3"], interactive=ready),
        controls["review_shp_answers"]: gr.update(interactive=ready),
        controls["shp_answers_md"]: state["shp_answers_feedback"],
        controls["add_shp_group"]: gr.update(interactive=ready),
        controls["void_shp_group"]: gr.update(interactive=ready),
        controls["check_shapes"]: gr.update(interactive=ready),
        controls["ai_shapes"]: gr.update(interactive=ready and state["shp_has_check"]),
        controls["save_shp_answers"]: gr.update(interactive=ready),
        controls["par_panel"]: gr.update(visible=active and state["par_panel_visible"]),
        controls["par_manual"]: gr.update(visible=state["real_mode"]),
        controls["par_virtual"]: gr.update(visible=state["virtual_mode"]),
        controls["virt_par_generate"]: gr.update(interactive=ready and state["virtual_mode"]),
        controls["par_groups_md"]: state["par_groups_md"],
        controls["par_group_pick"]: gr.update(
            choices=state["par_group_choices"], value=None, interactive=ready),
        controls["par_preview_md"]: state["par_preview_md"],
        controls["par_table"]: gr.update(value=state["par_table"], interactive=ready),
        controls["par_slope_sym"]: gr.update(value=state["par_slope_sym"], interactive=ready),
        controls["par_intercept_sym"]: gr.update(value=state["par_intercept_sym"], interactive=ready),
        controls["par_slope_asym"]: gr.update(value=state["par_slope_asym"], interactive=ready),
        controls["par_intercept_asym"]: gr.update(value=state["par_intercept_asym"], interactive=ready),
        controls["par_check_md"]: state["par_check_md"],
        controls["par_q1"]: gr.update(value=state["par_q1"], interactive=ready),
        controls["par_q2"]: gr.update(value=state["par_q2"], interactive=ready),
        controls["par_q3"]: gr.update(value=state["par_q3"], interactive=ready),
        controls["review_par_answers"]: gr.update(interactive=ready),
        controls["par_answers_md"]: state["par_answers_feedback"],
        controls["par_plot"]: gr.update(value=state["par_figure"],
                                        visible=state["par_figure"] is not None),
        controls["draw_par"]: gr.update(interactive=ready),
        controls["add_par_group"]: gr.update(interactive=ready),
        controls["void_par_group"]: gr.update(interactive=ready),
        controls["check_parallel"]: gr.update(interactive=ready),
        controls["ai_parallel"]: gr.update(interactive=ready and state["par_has_check"]),
        controls["save_par_answers"]: gr.update(interactive=ready),
        controls["summary_panel"]: gr.update(visible=active and state["summary_panel_visible"]),
        controls["summary_table_md"]: state["summary_table_md"],
        controls["export_csv"]: gr.update(interactive=ready),
        controls["csv_file"]: gr.update(value=state.get("csv_path"),
                                        visible=bool(state.get("csv_path"))),
        controls["export_docx"]: gr.update(interactive=ready),
        controls["docx_file"]: gr.update(value=state.get("docx_path"),
                                         visible=bool(state.get("docx_path"))),
        controls["summary_text"]: state["summary_text"],
        controls["summary_shapes_plot"]: gr.update(
            value=state["summary_shapes_figure"],
            visible=state["summary_shapes_figure"] is not None),
        controls["summary_parallel_plot"]: gr.update(
            value=state["summary_parallel_figure"],
            visible=state["summary_parallel_figure"] is not None),
        controls["generate_summary"]: gr.update(interactive=ready),
        controls["draw_summary"]: gr.update(interactive=ready),
        controls["later_panel"]: gr.update(visible=active and state["later_visible"]),
        controls["stage_placeholder"]: state["stage_placeholder"],
        controls["version_pick"]: gr.update(
            choices=state["version_choices"], value=state["version_id"],
            interactive=state["can_edit_params"] and bool(state["version_choices"])),
        controls["save_param"]: gr.update(interactive=state["can_edit_params"] and ready),
        controls["load_param"]: gr.update(
            interactive=state["can_edit_params"] and ready and bool(state["version_choices"])),
        controls["param_active_md"]: state["param_active_md"],
        controls["param_versions_md"]: state["param_versions_md"],
        controls["param_preview_md"]: state["param_preview_md"],
        controls["virtual_param_md"]: state["virtual_param_md"],
        controls["tutor_launch"]: gr.update(visible=active and not state["tutor_open"],
                                            interactive=ready, value=state["tutor_label"]),
        controls["tutor_dock"]: gr.update(
            visible=active and state["tutor_open"],
            elem_classes=["tutor-open"] if state["tutor_open"] else []),
        controls["tutor_close"]: gr.update(interactive=ready),
        controls["ask"]: gr.update(interactive=active and ready),
        controls["hint"]: gr.update(interactive=active and ready),
        controls["ask_box"]: gr.update(value=state["ask_draft"], interactive=active and ready),
        controls["chat"]: state["history"],
        controls["cite_selection"]: gr.update(interactive=active and ready),
    }
    for key in experiment.FIELD_KEYS:
        updates[controls[key]] = gr.update(value=state.get(key, ""),
                                           interactive=ready and state["can_edit_params"])
    return updates


def build_ui(handle, get_view_state):
    with gr.Blocks(title="扭摆法测转动惯量") as demo:
        with gr.Column(elem_id="session-bar"):
            with gr.Row(elem_classes=["session-row"]):
                student = gr.Textbox(
                    label="学号", placeholder="例如 20260001", elem_id="student-id", scale=3,
                    info="1～24 位数字；只用于保存记录，不发给 AI。")
                start = gr.Button("开始学习", variant="primary", elem_id="start-learning", scale=0)
                save_line = md("尚未开始", elem_id="save-line", scale=3)
            with gr.Row(elem_classes=["session-actions"]):
                tutor_launch = gr.Button("问助教", visible=False, elem_id="tutor-open", scale=0)
                new = gr.Button("结束并新建会话", visible=False, interactive=False, scale=0)
                retry = gr.Button("重试保存记录", visible=False, interactive=False, scale=0)

        gr.HTML(HEADER_HTML)
        with gr.Accordion("使用流程与功能说明", open=True, elem_id="onboarding") as onboarding:
            md(ONBOARDING_MD, elem_id="onboarding-md")

        pre_start = md(PRE_START_MD, elem_id="pre-start")
        with gr.Row(elem_id="demo-row"):
            demo_button = gr.Button("载入完整演示数据", variant="secondary",
                                    elem_id="demo-start")
            demo_note = md("想直接验收？点左边按钮，会创建一个所有阶段都填好的演示会话。",
                           elem_id="demo-note")

        with gr.Row(elem_id="mode-row"):
            mode = gr.Radio(
                choices=[(experiment.MODE_LABELS[item], item) for item in experiment.MODES],
                value=experiment.MODE_REAL, label="实验模式", elem_id="mode-select")
            md(MODE_NOTE, elem_id="mode-note")

        with gr.Row(elem_id="stage-row"):
            stage = gr.Radio(
                choices=[(experiment.STAGE_LABELS[item], item) for item in experiment.STAGES],
                value=experiment.STAGE_PARAMS, label="实验阶段", elem_id="stage-select")
            status = md("就绪", elem_id="learning-status")
        stage_hint = md("", elem_id="stage-hint")

        with gr.Row(elem_id="page-row"):
            with gr.Column(scale=4, min_width=320, elem_id="work-column"):
                with gr.Column(visible=False, elem_id="params-panel") as params_panel:
                    md("### 阶段0 器材参数\n\n先登记本次实验的器材和测量设置。"
                       "参数可随时修改、追加；不要求一次填满，缺项会在预览里标出。"
                       "多个读数用逗号、顿号、空格或换行分开。",
                       elem_classes=["section-head"])
                    with gr.Column(visible=True, elem_id="real-params") as real_params:
                        with gr.Column(elem_classes=["card"]):
                            md("### 测量设置")
                            with gr.Row():
                                p_n = gr.Textbox(label="周期数 N", value="10", placeholder="例如 10",
                                                 info="5～20 的整数；一次计时包含几个周期。", scale=1)
                                p_angle = gr.Textbox(label="摆角 / °", value="60", placeholder="例如 60",
                                                     info="本实验固定 60°，允许 40°～90°。", scale=1)
                            with gr.Row():
                                p_timer = gr.Textbox(label="计时器分辨力 / s", value="0.001",
                                                     placeholder="例如 0.001",
                                                     info="用于 B 类不确定度。", scale=1)
                                p_balance = gr.Textbox(label="天平误差限 / g", value="0.1",
                                                       placeholder="例如 0.1",
                                                       info="用于质量 B 类不确定度。", scale=1)
                            with gr.Row():
                                p_caliper = gr.Textbox(label="卡尺误差限 / mm", value="0.02",
                                                       placeholder="例如 0.02",
                                                       info="用于直径/长度 B 类不确定度。", scale=1)
                                p_ruler = gr.Textbox(label="钢尺误差限 / mm", value="1.0",
                                                     placeholder="例如 1.0",
                                                     info="量较长尺寸时使用。", scale=1)

                        param_fields = {}
                        for object_key, name, fields in experiment.OBJECT_FIELDS:
                            with gr.Column(elem_classes=["card"]):
                                md(f"### {name}")
                                with gr.Row():
                                    for field_key, label, unit, example, info in fields:
                                        key = experiment.ui_key(object_key, field_key)
                                        param_fields[key] = gr.Textbox(
                                            label=f"{label} / {unit}" if unit else label,
                                            placeholder=example, info=info, scale=1,
                                            min_width=180)
                        with gr.Column(elem_classes=["card"]):
                            md("### 备注")
                            p_note = gr.Textbox(
                                label="本次参数备注（可选）", lines=2,
                                placeholder="例如 第一版；换了圆柱；第三次读数偏大",
                                info="只作记录，不当作指令。")
                            save_param = gr.Button("保存为新版本", variant="primary",
                                                   elem_id="save-param")
                            md("保存后自动设为当前采用版本；旧版本保留在版本表里。"
                               "不要求填满才能进入下一阶段；缺项会在预览里标出。"
                               "要追加读数，直接在对应输入框里加数字，再保存为新版本。")

                        with gr.Column(elem_id="version-panel"):
                            md("### 参数版本")
                            with gr.Row():
                                version_pick = gr.Dropdown(
                                    choices=[], value=None, label="选择参数版本",
                                    info="只列真实模式的版本；载入会把版本写回表单。")
                                load_param = gr.Button("载入并采用", variant="secondary")
                            param_active_md = md("", elem_id="param-active")
                            param_versions_md = md("", elem_id="param-versions")

                        with gr.Column(elem_id="param-preview"):
                            md("### 参数预览")
                            param_preview_md = md("")

                    with gr.Column(visible=False, elem_id="virtual-params") as virtual_params:
                        with gr.Column(elem_classes=["card"]):
                            virtual_param_md = md("")
                            md("虚拟模式的参数只读；周期数据由阶段1～4 的测量按钮生成。")

                with gr.Column(visible=False, elem_id="cal-panel") as cal_panel:
                    md("### 阶段1 标定\n\n"
                       "空盘和加圆柱各测 N 个周期的总时间。标定组不限数量；"
                       "多组会一起参与 T₀、T₁ 的平均。学生填 I₁、K、I₀，"
                       "程序负责不确定度和有效数字，AI 负责解释检查结果。",
                       elem_classes=["section-head"])
                    with gr.Column(elem_classes=["card"], visible=True,
                                     elem_id="cal-manual") as cal_manual:
                        md("### 添加标定组")
                        cal_n = gr.Textbox(
                            label="周期数 N", value="10", placeholder="例如 10",
                            info="5～20 的整数；同一组内 N 一致。", scale=1)
                        cal_t0 = gr.Textbox(
                            label="空盘 N 个周期的总时间 / s", lines=2,
                            placeholder="例如 7.695, 7.697, 7.696",
                            info="多个读数用逗号、顿号、空格或换行分开。")
                        cal_t1 = gr.Textbox(
                            label="加圆柱后 N 个周期的总时间 / s", lines=2,
                            placeholder="例如 12.443, 12.447, 12.445",
                            info="多个读数用逗号、顿号、空格或换行分开。")
                        cal_note = gr.Textbox(
                            label="这一组备注（可选）", lines=1,
                            placeholder="例如 第一次；换了圆柱；第 3 次读数偏大")
                        add_cal_group = gr.Button("添加一组", variant="primary")
                        md("不要求一次测满；可以先添加一组，之后继续追加。")
                    with gr.Column(visible=False, elem_classes=["card"],
                                   elem_id="cal-virtual") as cal_virtual:
                        md("### 虚拟标定数据")
                        virt_cal_generate = gr.Button("生成一组标定数据", variant="primary")
                        md("标定固定用这只塑料圆柱，I₁ 各组共用。每点一次生成一组独立计时，"
                           "周期带随机起伏；连点 2～5 次得到多组，程序用多组算平均值和 A 类不确定度。")
                    with gr.Column(elem_classes=["card"]):
                        md("### 已记录的标定组")
                        cal_groups_md = md("", elem_id="cal-groups-md")
                        md("表里是每组自己的总时间和周期；下面的「当前标定预览」是多组平均。")
                        cal_group_pick = gr.Dropdown(
                            choices=[], value=None, label="选择要作废的组",
                            info="作废的组保留在表里，不再参与平均。")
                        void_cal_group = gr.Button("作废选中的组（旧记录保留）",
                                                   variant="secondary")
                    with gr.Column(elem_classes=["card"]):
                        md("### 当前标定预览")
                        cal_preview_md = md("")
                    with gr.Column(elem_classes=["card"]):
                        md("### 学生填写的最终结果")
                        with gr.Row():
                            cal_i1 = gr.Textbox(
                                label="圆柱 I₁ / kg·m²", placeholder="填你算出的数",
                                info="自己算；只填数值。", scale=1)
                            cal_k = gr.Textbox(
                                label="扭转常数 K / N·m/rad", placeholder="填你算出的数",
                                info="自己算；只填数值。", scale=1)
                            cal_i0 = gr.Textbox(
                                label="载物盘 I₀ / kg·m²", placeholder="填你算出的数",
                                info="自己算；只填数值。", scale=1)
                        check_cal = gr.Button("核对结果（本地）", variant="primary")
                        ai_cal = gr.Button("请 AI 解释", variant="secondary")
                        cal_check_md = md("填好结果后点「核对结果」。")

                with gr.Column(visible=False, elem_id="shp-panel") as shp_panel:
                    md("### 阶段2 规则刚体\n\n"
                       "圆筒、球体、细杆分别测周期。每个对象可以添加多组；"
                       "程序按同一来源的 K、I₀ 和阶段0 参数计算，学生填最终结果，"
                       "AI 负责解释检查结果。",
                       elem_classes=["section-head"])
                    with gr.Column(elem_classes=["card"]):
                        md("### 选择对象")
                        shp_condition = gr.Dropdown(
                            choices=[(stages.SHAPE_LABELS[key], key)
                                     for key in stages.SHAPE_CONDITIONS],
                            value="tube", label="对象",
                            info="真实模式和虚拟模式都用这个选择。")
                    with gr.Column(elem_classes=["card"], visible=True,
                                     elem_id="shp-manual") as shp_manual:
                        md("### 添加测量组")
                        shp_n = gr.Textbox(label="周期数 N", value="10",
                                           placeholder="例如 10",
                                           info="5～20 的整数。")
                        shp_times = gr.Textbox(
                            label="N 个周期的总时间 / s", lines=2,
                            placeholder="例如 12.443, 12.447, 12.445",
                            info="多个读数用逗号、顿号、空格或换行分开。")
                        shp_note = gr.Textbox(
                            label="这一组备注（可选）", lines=1,
                            placeholder="例如 第二次；换了球体")
                        add_shp_group = gr.Button("添加一组", variant="primary")
                    with gr.Column(visible=False, elem_classes=["card"],
                                   elem_id="shp-virtual") as shp_virtual:
                        md("### 虚拟测量")
                        virt_shp_generate = gr.Button("按上面选择的对象生成一组数据",
                                                      variant="primary")
                        md("虚拟模式使用固定器材参数；先选对象，再点击生成。")
                    with gr.Column(elem_classes=["card"]):
                        md("### 已记录的测量组")
                        shp_groups_md = md("", elem_id="shp-groups-md")
                        shp_group_pick = gr.Dropdown(
                            choices=[], value=None, label="选择要作废的组",
                            info="作废的组保留在表里，不再参与平均。")
                        void_shp_group = gr.Button("作废选中的组（旧记录保留）",
                                                   variant="secondary")
                    with gr.Column(elem_classes=["card"]):
                        md("### 当前测量预览")
                        shp_preview_md = md("")
                    with gr.Column(elem_classes=["card"]):
                        md("### 学生填写的最终结果")
                        shp_table = gr.Dataframe(
                            headers=["对象", "I实验 / kg·m²", "I几何 / kg·m²", "E / %"],
                            datatype=["str", "number", "number", "number"],
                            value=[["金属圆筒", "", "", ""],
                                   ["实心球体", "", "", ""],
                                   ["金属细杆", "", "", ""]],
                            type="array", interactive=True, label="规则刚体结果")
                        check_shapes = gr.Button("核对结果（本地）", variant="primary")
                        ai_shapes = gr.Button("请 AI 解释", variant="secondary")
                        shp_check_md = md("填好表后点「核对结果」。")
                    with gr.Column(elem_classes=["card"]):
                        md("### 阶段2 问题")
                        shp_q1 = gr.Textbox(label="问题1：圆筒和圆柱质量、外径接近，为什么 I 仍可能差很多？",
                                            lines=2, placeholder="写下你的解释")
                        shp_q2 = gr.Textbox(label="问题2：哪些物体要减 I₀，哪些不要？为什么？",
                                            lines=2, placeholder="写下你的解释")
                        shp_q3 = gr.Textbox(label="问题3：球体为什么用 2/5，而不是 1/2？",
                                            lines=2, placeholder="写下你的解释")
                        save_shp_answers = gr.Button("保存阶段2 回答", variant="secondary")
                        review_shp_answers = gr.Button("请 AI 批改回答", variant="primary")
                        shp_answers_md = md("")

                with gr.Column(visible=False, elem_id="par-panel") as par_panel:
                    md("### 阶段3 平行轴\n\n"
                       "细杆基准、五个对称距离、四组不对称。每个条件可以添加多组；"
                       "学生填 I总、斜率和截距，程序按学生填的点画图并检查。",
                       elem_classes=["section-head"])
                    with gr.Column(elem_classes=["card"]):
                        md("### 选择条件")
                        par_condition = gr.Dropdown(
                            choices=[(label, key) for key, label in stages.parallel_conditions()],
                            value="rod", label="条件",
                            info="真实模式和虚拟模式都用这个选择。")
                    with gr.Column(elem_classes=["card"], visible=True,
                                     elem_id="par-manual") as par_manual:
                        md("### 添加测量组")
                        par_n = gr.Textbox(label="周期数 N", value="10",
                                           placeholder="例如 10",
                                           info="5～20 的整数。")
                        par_times = gr.Textbox(
                            label="N 个周期的总时间 / s", lines=2,
                            placeholder="例如 14.235, 14.239, 14.237",
                            info="多个读数用逗号、顿号、空格或换行分开。")
                        par_note = gr.Textbox(
                            label="这一组备注（可选）", lines=1,
                            placeholder="例如 第二次；换滑块距离")
                        add_par_group = gr.Button("添加一组", variant="primary")
                    with gr.Column(visible=False, elem_classes=["card"],
                                   elem_id="par-virtual") as par_virtual:
                        md("### 虚拟测量")
                        virt_par_generate = gr.Button("按上面选择的条件生成一组数据",
                                                      variant="primary")
                        md("虚拟模式使用固定器材参数；先选条件，再点击生成。")
                    with gr.Column(elem_classes=["card"]):
                        md("### 已记录的测量组")
                        par_groups_md = md("", elem_id="par-groups-md")
                        par_group_pick = gr.Dropdown(
                            choices=[], value=None, label="选择要作废的组",
                            info="作废的组保留在表里，不再参与平均。")
                        void_par_group = gr.Button("作废选中的组（旧记录保留）",
                                                   variant="secondary")
                    with gr.Column(elem_classes=["card"]):
                        md("### 当前测量预览")
                        par_preview_md = md("")
                    with gr.Column(elem_classes=["card"]):
                        md("### 学生填写的 I总")
                        par_table = gr.Dataframe(
                            headers=["条件", "I总 / kg·m²"],
                            datatype=["str", "number"],
                            value=[[label, ""] for _key, label in stages.parallel_conditions()],
                            type="array", interactive=True, label="平行轴 I总")
                        md("### 学生填写的斜率与截距")
                        with gr.Row():
                            par_slope_sym = gr.Textbox(
                                label="对称斜率 / kg", placeholder="填你算出的数",
                                info="I–d² 图；自己算。", scale=1)
                            par_intercept_sym = gr.Textbox(
                                label="对称截距 / kg·m²", placeholder="填你算出的数",
                                info="I–d² 图；自己算。", scale=1)
                        with gr.Row():
                            par_slope_asym = gr.Textbox(
                                label="不对称斜率 / kg", placeholder="填你算出的数",
                                info="I–(d₁²+d₂²) 图；自己算。", scale=1)
                            par_intercept_asym = gr.Textbox(
                                label="不对称截距 / kg·m²", placeholder="填你算出的数",
                                info="I–(d₁²+d₂²) 图；自己算。", scale=1)
                        check_parallel = gr.Button("核对结果（本地）", variant="primary")
                        ai_parallel = gr.Button("请 AI 解释", variant="secondary")
                        par_check_md = md("填好表后点「核对结果」。")
                    with gr.Column(elem_classes=["card"]):
                        md("### 按你填的 I总 画图")
                        draw_par = gr.Button("生成/更新图", variant="primary")
                        par_chart_note = md("点按钮后，程序按你填的 I总 画图；至少一个点就能显示。")
                        par_plot = gr.Plot(label="平行轴 I–距离平方")
                    with gr.Column(elem_classes=["card"]):
                        md("### 阶段3 问题")
                        par_q1 = gr.Textbox(label="问题1：对称放置时，斜率和截距各对应什么？",
                                            lines=2, placeholder="写下你的解释")
                        par_q2 = gr.Textbox(label="问题2：不对称时为什么用 d₁²+d₂²？斜率对应什么？",
                                            lines=2, placeholder="写下你的解释")
                        par_q3 = gr.Textbox(label="问题3：细杆单独的点为什么不能当成 d = 0？",
                                            lines=2, placeholder="写下你的解释")
                        save_par_answers = gr.Button("保存阶段3 回答", variant="secondary")
                        review_par_answers = gr.Button("请 AI 批改回答", variant="primary")
                        par_answers_md = md("")

                with gr.Column(visible=False, elem_id="summary-panel") as summary_panel:
                    md("### 阶段4 图表与报告\n\n"
                       "按已经记录的学生数据生成图表和标准实验报告草稿。报告是草稿，不会自动提交。",
                       elem_classes=["section-head"])
                    with gr.Column(elem_classes=["card"]):
                        md("### 当前记录")
                        summary_table_md = md("")
                        with gr.Row():
                            export_csv = gr.Button("生成原始数据 CSV", variant="secondary")
                            md("生成后点下面的文件名下载；含阶段1～3 每组的总时间和周期。",
                               elem_id="csv-note")
                        csv_file = gr.File(label="原始数据 CSV", file_count="single",
                                           interactive=False, visible=False)
                        with gr.Row():
                            export_docx = gr.Button("导出实验报告 .docx", variant="primary")
                            md("含参数、数据表、结果和两张图；讨论与结论留空，自己写。",
                               elem_id="docx-note")
                        docx_file = gr.File(label="实验报告 .docx", file_count="single",
                                            interactive=False, visible=False)
                    with gr.Column(elem_classes=["card"]):
                        md("### 阶段2：I实验 / I几何")
                        summary_shapes_plot = gr.Plot(label="阶段2 I实验 / I几何")
                    with gr.Column(elem_classes=["card"]):
                        md("### 阶段3：I总–距离平方")
                        summary_parallel_plot = gr.Plot(label="阶段3 I–距离平方")
                    with gr.Column(elem_classes=["card"]):
                        generate_summary = gr.Button("生成实验报告草稿", variant="primary")
                        summary_text = md("")
                    with gr.Column(elem_classes=["card"]):
                        md("### 生成图表")
                        draw_summary = gr.Button("生成阶段2/3 图", variant="primary")
                        summary_chart_note = md("点按钮后生成阶段2 和阶段3 的图；不会自动提交。")

                with gr.Column(visible=False, elem_id="later-panel") as later_panel:
                    with gr.Column(elem_classes=["card"]):
                        stage_placeholder = md("", elem_id="stage-placeholder")

            with gr.Column(visible=False, scale=0, min_width=0, elem_id="tutor-dock") as tutor_dock:
                with gr.Row(elem_id="tutor-head"):
                    md("### 实验助教\n\n选中页面文字会填进这里；发送前可以改。可拖动四边或角调整大小。")
                    tutor_close = gr.Button("收起", elem_id="tutor-close")
                chat = gr.Chatbot(
                    label="实验助教", height="100%", min_height=240,
                    group_consecutive_messages=False, layout="bubble",
                    elem_id="tutor-chat", allow_tags=False,
                    latex_delimiters=[
                        {"left": "$$", "right": "$$", "display": True},
                        {"left": "\\[", "right": "\\]", "display": True},
                        {"left": "\\(", "right": "\\)", "display": False},
                    ])
                ask_box = gr.Textbox(
                    label="问题", lines=3, interactive=False, elem_id="ask-box",
                    placeholder="例如：K 和 I₀ 为什么不能只测一次得到？",
                    info="也可以先选中页面文字，再点浮出的「询问 AI」。")
                with gr.Row():
                    ask = gr.Button("向 AI 提问", variant="primary", interactive=False,
                                    elem_id="ask-submit")
                    hint = gr.Button("给我提示", interactive=False)

        cite_text = gr.Textbox(value="", lines=1, label="选区", elem_id="cite-text",
                               elem_classes=["ask-sink"])
        cite_selection = gr.Button("引用选区", elem_id="cite-selection",
                                   elem_classes=["ask-sink"])

        controls = {
            "student": student, "start": start, "save_line": save_line,
            "new": new, "retry": retry, "status": status,
            "onboarding": onboarding, "pre_start": pre_start,
            "demo_button": demo_button, "demo_note": demo_note,
            "mode": mode, "stage": stage, "stage_hint": stage_hint,
            "params_panel": params_panel, "real_params": real_params,
            "virtual_params": virtual_params, "later_panel": later_panel,
            "cal_panel": cal_panel,
            "cal_manual": cal_manual, "cal_virtual": cal_virtual,
            "virt_cal_generate": virt_cal_generate,
            "cal_groups_md": cal_groups_md, "cal_preview_md": cal_preview_md,
            "cal_group_pick": cal_group_pick,
            "cal_i1": cal_i1, "cal_k": cal_k, "cal_i0": cal_i0,
            "cal_check_md": cal_check_md, "add_cal_group": add_cal_group,
            "void_cal_group": void_cal_group,
            "check_cal": check_cal, "ai_cal": ai_cal,
            "cal_n": cal_n, "cal_t0": cal_t0,
            "cal_t1": cal_t1, "cal_note": cal_note,
            "shp_panel": shp_panel, "shp_groups_md": shp_groups_md,
            "shp_group_pick": shp_group_pick,
            "shp_manual": shp_manual, "shp_virtual": shp_virtual,
            "virt_shp_generate": virt_shp_generate,
            "shp_preview_md": shp_preview_md, "shp_table": shp_table,
            "shp_check_md": shp_check_md, "shp_q1": shp_q1, "shp_q2": shp_q2,
            "shp_q3": shp_q3, "add_shp_group": add_shp_group,
            "void_shp_group": void_shp_group,
            "check_shapes": check_shapes, "ai_shapes": ai_shapes,
            "save_shp_answers": save_shp_answers,
            "review_shp_answers": review_shp_answers,
            "shp_answers_md": shp_answers_md,
            "shp_condition": shp_condition, "shp_n": shp_n, "shp_times": shp_times,
            "shp_note": shp_note,
            "par_panel": par_panel, "par_groups_md": par_groups_md,
            "par_group_pick": par_group_pick,
            "par_manual": par_manual, "par_virtual": par_virtual,
            "virt_par_generate": virt_par_generate,
            "par_preview_md": par_preview_md, "par_table": par_table,
            "par_slope_sym": par_slope_sym, "par_intercept_sym": par_intercept_sym,
            "par_slope_asym": par_slope_asym, "par_intercept_asym": par_intercept_asym,
            "par_check_md": par_check_md, "par_q1": par_q1, "par_q2": par_q2,
            "par_q3": par_q3, "par_plot": par_plot,
            "par_chart_note": par_chart_note, "draw_par": draw_par, "add_par_group": add_par_group,
            "void_par_group": void_par_group,
            "check_parallel": check_parallel, "ai_parallel": ai_parallel,
            "save_par_answers": save_par_answers,
            "review_par_answers": review_par_answers,
            "par_answers_md": par_answers_md,
            "par_condition": par_condition, "par_n": par_n, "par_times": par_times,
            "par_note": par_note,
            "summary_panel": summary_panel, "summary_table_md": summary_table_md,
            "export_csv": export_csv, "csv_file": csv_file,
            "export_docx": export_docx, "docx_file": docx_file,
            "summary_text": summary_text, "summary_shapes_plot": summary_shapes_plot,
            "summary_parallel_plot": summary_parallel_plot,
            "generate_summary": generate_summary,
            "draw_summary": draw_summary, "summary_chart_note": summary_chart_note,
            "stage_placeholder": stage_placeholder,
            "save_param": save_param, "load_param": load_param,
            "version_pick": version_pick,
            "param_active_md": param_active_md, "param_versions_md": param_versions_md,
            "param_preview_md": param_preview_md, "virtual_param_md": virtual_param_md,
            "tutor_launch": tutor_launch, "tutor_dock": tutor_dock, "tutor_close": tutor_close,
            "chat": chat, "ask_box": ask_box, "ask": ask, "hint": hint,
            "cite_text": cite_text, "cite_selection": cite_selection,
        }
        controls.update(param_fields)
        controls.update({
            "p_n": p_n, "p_angle": p_angle, "p_timer": p_timer,
            "p_balance": p_balance, "p_caliper": p_caliper, "p_ruler": p_ruler,
            "p_note": p_note,
        })

        outputs = [
            student, start, save_line, new, retry, status, onboarding, pre_start,
            demo_button, demo_note,
            mode, stage, stage_hint, params_panel, real_params, virtual_params,
            cal_panel, cal_groups_md, cal_preview_md, cal_i1, cal_k, cal_i0,
            cal_check_md, add_cal_group, void_cal_group, check_cal, ai_cal,
            cal_manual, cal_virtual, virt_cal_generate, cal_group_pick,
            shp_panel, shp_groups_md, shp_preview_md, shp_table, shp_check_md,
            shp_q1, shp_q2, shp_q3, add_shp_group, void_shp_group,
            check_shapes, ai_shapes, save_shp_answers, review_shp_answers,
            shp_answers_md, shp_manual, shp_virtual,
            virt_shp_generate, shp_group_pick,
            par_panel, par_groups_md, par_preview_md, par_table,
            par_slope_sym, par_intercept_sym, par_slope_asym, par_intercept_asym,
            par_check_md, par_q1, par_q2, par_q3, par_plot,
            par_chart_note, draw_par,
            add_par_group, void_par_group, check_parallel, ai_parallel,
            save_par_answers, review_par_answers, par_answers_md,
            par_manual, par_virtual, virt_par_generate, par_group_pick,
            summary_panel, summary_table_md, summary_text, summary_shapes_plot,
            summary_parallel_plot, generate_summary,
            export_csv, csv_file, export_docx, docx_file,
            draw_summary, summary_chart_note,
            later_panel, stage_placeholder, save_param, load_param,
            version_pick, param_active_md, param_versions_md, param_preview_md,
            virtual_param_md, tutor_launch, tutor_dock, tutor_close, chat, ask, hint,
            ask_box, cite_selection,
            p_n, p_angle, p_timer, p_balance, p_caliper, p_ruler,
            *[param_fields[key] for key in param_fields], p_note,
        ]

        def on_event(*args):
            for view in handle(*args):
                yield render_view(view, controls)

        def bind(component, action, event="click"):
            inputs = [
                gr.State(action), student, gr.State("calibrate"), gr.State(None),
                gr.State(10), gr.State(0), ask_box, gr.State("same"),
                gr.State(None), gr.State(None), gr.State(None),
                gr.State(None), gr.State(None), gr.State(None), gr.State(None),
                gr.State("virtual"), gr.State("measure"), gr.State("total_time"),
                gr.State(""), gr.State(""), gr.State(None),
                gr.State(None), cite_text, gr.State(None), gr.State("latest"),
                *[gr.State(None) for _ in range(14)],
                gr.State(None),
                mode, stage, version_pick,
                p_n, p_angle, p_timer, p_balance, p_caliper, p_ruler,
                param_fields["p_cylinder_mass"], param_fields["p_cylinder_diameter"],
                param_fields["p_tube_mass"], param_fields["p_tube_outer"],
                param_fields["p_tube_inner"], param_fields["p_sphere_mass"],
                param_fields["p_sphere_diameter"], param_fields["p_rod_mass"],
                param_fields["p_rod_length"], param_fields["p_slider_mass"],
                param_fields["p_slider_diameter"], p_note,
                cal_n, cal_t0, cal_t1, cal_note, cal_i1, cal_k, cal_i0,
                shp_condition, shp_n, shp_times, shp_note, shp_table,
                shp_q1, shp_q2, shp_q3,
                par_condition, par_n, par_times, par_note, par_table,
                par_slope_sym, par_intercept_sym, par_slope_asym, par_intercept_asym,
                par_q1, par_q2, par_q3,
                cal_group_pick, shp_group_pick, par_group_pick,
            ]
            kwargs = dict(fn=on_event, inputs=inputs, outputs=outputs,
                          concurrency_id="single_user", concurrency_limit=1,
                          api_visibility="private")
            if event == "click":
                component.click(**kwargs)
            else:
                component.input(**kwargs)

        for component, action in [
            (start, "start"), (new, "new"), (retry, "retry"),
            (demo_button, "seed_demo"),
            (save_param, "save_param"), (load_param, "load_param"),
            (add_cal_group, "add_cal_group"), (void_cal_group, "void_cal_group"),
            (check_cal, "check_cal"), (ai_cal, "ai_cal"),
            (virt_cal_generate, "virt_cal_group"),
            (add_shp_group, "add_shp_group"), (void_shp_group, "void_shp_group"),
            (check_shapes, "check_shapes"), (ai_shapes, "ai_shapes"),
            (save_shp_answers, "save_shp_answers"),
            (review_shp_answers, "review_shp_answers"),
            (virt_shp_generate, "virt_shp_group"),
            (add_par_group, "add_par_group"), (void_par_group, "void_par_group"),
            (check_parallel, "check_parallel"), (ai_parallel, "ai_parallel"),
            (save_par_answers, "save_par_answers"),
            (review_par_answers, "review_par_answers"),
            (draw_par, "draw_par"),
            (virt_par_generate, "virt_par_group"),
            (generate_summary, "generate_summary"),
            (export_csv, "export_csv"),
            (export_docx, "export_docx"),
            (draw_summary, "draw_summary"),
            (tutor_launch, "open_tutor"),
            (tutor_close, "close_tutor"), (ask, "ask"), (hint, "hint"),
            (cite_selection, "cite_selection"),
        ]:
            bind(component, action)
        bind(mode, "set_mode", event="input")
        bind(stage, "set_exp_stage", event="input")

        demo.load(lambda: render_view(get_view_state(), controls), outputs=outputs, js=PAGE_JS,
                  concurrency_id="single_user", concurrency_limit=1, api_visibility="private")
    return demo, controls
