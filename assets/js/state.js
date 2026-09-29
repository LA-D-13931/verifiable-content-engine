/* ============================================================
 * 模块 2：全局状态与配色
 * 一个 App 对象承载「当前实验场景」的全部可渲染字段；
 * 渲染器只读它，交互器只写它，引擎判定它。
 * ============================================================ */
/* 画布配色统一从主题 token 读取（assets/css/theme-tokens.css），
   这样界面层换主题时画布上的数学对象色会跟着走，不会出现两套配色。
   读取失败时回落到内置值，保证单独打开也能用。 */
function readToken(name, fallback) {
    try {
        const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return v || fallback;
    } catch (err) {
        return fallback;
    }
}

window.COLORS = {
    v: readToken('--m-v', '#e8c46a'),        // 主向量（金）
    av: readToken('--m-av', '#6fbf8f'),      // 变换后的向量 Av（绿）
    ai: readToken('--m-ai', '#e08a96'),      // 第 1 列 / Aî（玫红）
    aj: readToken('--m-aj', '#a99cd8'),      // 第 2 列 / Aĵ（紫）
    ak: readToken('--m-ak', '#7ea6d8'),      // 第 3 列 / Ak̂（蓝）
    grid: readToken('--m-grid', 'rgba(142,197,255,0.16)'),
    tgrid: readToken('--m-tgrid', 'rgba(110,231,200,0.34)'),
    axis: readToken('--m-axis', 'rgba(238,246,251,0.34)'),
    prev: readToken('--ink-faint', '#7b8ea0'),
    target: readToken('--m-target', '#e8c46a')
};

/* 换主题后重新读一遍 token（渲染器每帧都从 COLORS 取色，所以改完立即生效） */
window.refreshColors = function () {
    const map = {
        v: '--m-v', av: '--m-av', ai: '--m-ai', aj: '--m-aj', ak: '--m-ak',
        grid: '--m-grid', tgrid: '--m-tgrid', axis: '--m-axis',
        prev: '--ink-faint', target: '--m-target'
    };
    Object.keys(map).forEach(k => {
        const v = readToken(map[k], window.COLORS[k]);
        if (v) window.COLORS[k] = v;
    });
    // 面板和画布上的颜色是从 COLORS 取的，换主题后必须重绘，
    // 否则会出现「面板还在用暗色主题的玫红」这种对比度不足的问题。
    if (window.UI && UI.updatePanels) UI.updatePanels();
    if (window.Render2D) Render2D.render();
};

window.App = {
    mode: 'lab',              // 'lab' | 'sandbox'
    labId: null,
    space: '2d',              // '2d' | '3d'
    matrix: null,             // 当前矩阵，null = 本实验无矩阵
    matrixSize: 2,
    vectors: [],              // {id,data,color,label,draggable,dashed,showTransform,transformLabel}
    shape: null,              // 'square' | 'cube'
    lines: [],                // 行图像直线 {a,b,c,label,color?}
    targetPoint: null,        // {point,label}
    grid: true,
    axes: true,
    tgrid: true,              // 变换后的网格
    basis: false,             // 画基向量与列落点
    comboPath: false,         // v = x·col1 + y·col2 的组合路径
    metric: null,             // 右侧面板换成指标卡：'det' | 'rank' | null
    spanView: false,          // 显示列空间（rank 1 画一条过原点的直线，rank 2 铺满平面）
    nullView: false,          // 显示零空间（A 压到原点的那些方向，一条过原点的直线）
    basisCoords: false,       // 基变换课：显示 v 在新基下的坐标路径与读数
    numLine: null,            // 点积/对偶课：{range:[a,b], marks:[..]} 画一条水平数轴
    oneDim: null,             // 点积/对偶课：{basis:[x,y]} 把向量投影到这条 1D 方向上
    dotPair: null,            // 点积课：{a:'u', b:'v', proj:true} 画投影与 u·v 读数
    cross: null,              // 叉积课：{colA:0, colB:1, label:'a×b'} 实时绘制列向量的叉积
    interact: {               // 本实验允许的交互
        clickPlace: false,
        dragVectors: true,
        dragColumns: false,
        orbit: false
    },
    toolbar: [],              // [{id,label,action,...}]
    cam2d: { scale: 46, panX: 0, panY: 0 },
    cam3d: { yaw: -0.7, pitch: 0.4, dist: 11 },
    anim: null,               // {from,to,t,dur,start,after}
    actionLog: [],            // 过程性任务的判定依据
    taskStatus: {},           // taskId -> true
    choices: {},              // 辨析题作答：taskId -> 选中的选项下标
                              // 用 map 而不是单个值，因为同一关可能有多道辨析题，
                              // 必须各存各的，否则后一题会把前一题的反馈挤掉
    completed: [],            // 已完成实验 id
    running: false,           // 动画循环是否在跑
    hover: null,              // {kind,index} 命中对象，渲染器用来高亮
    showEigen: false          // 沙盒/特征课：是否显示特征方向虚线
};

window.DEFAULT_SCALE = 46;
window.MIN_SCALE = 8;
window.MAX_SCALE = 260;
