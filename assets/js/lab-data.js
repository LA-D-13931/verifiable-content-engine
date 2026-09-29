/* ============================================================
 * 模块 3：实验数据（唯一的「内容」文件）
 * 加一个实验 = 在这里加一段数据，其余文件不用动。
 *
 * 章节与节号对齐参考课程的 12 章 56 节；尚未建设的节见 README「建设进度」。
 *
 * 辨析题的约定（tools/check-lab.py 会强制校验）：
 *   · options 与 explains 数量一致、一一对应
 *   · 正解固定放在第 3 个选项（correct: 2），避免位置规律被猜
 *   · explains 里正解那条以「✓ 对：」开头，错误的两条以「✗ 不对：」开头
 *   · 字符串一律用单引号，正文里不要出现英文撇号（会提前闭合字符串）
 *
 * task.check 支持的类型（判题器在 engine.js）：
 *   vector-at / av-at / matrix-col-at / match-matrix / det / rank
 *   on-span / in-basis / dot / cross-mag / cross-dir / solve / collinear
 *   choice / actions
 * ============================================================ */
window.CHAPTERS = [
    { id: 1, title: '向量与坐标', desc: '把「数对」看成空间里的一段位移' },
    { id: 2, title: '基向量与矩阵的列', desc: '矩阵的两列就是 î、ĵ 的落点' },
    { id: 3, title: '矩阵即变换', desc: '一个矩阵改变整个空间' },
    { id: 4, title: '复合变换与矩阵乘法', desc: '变换的复合，顺序不能交换' },
    { id: 5, title: '行列式：面积的缩放', desc: 'det 就是面积的缩放倍数' },
    { id: 6, title: '逆矩阵：撤销变换', desc: '把变换倒回去' },
    { id: 7, title: '解线性方程组', desc: '列图像与行图像，解的结构' },
    { id: 8, title: '基变换', desc: '同一根箭头，两套坐标' },
    { id: 9, title: '特征向量与特征值', desc: '不被转向的方向' },
    { id: 10, title: '走进三维空间', desc: '三列 = 三个基向量的落点' },
    { id: 11, title: '点积与对偶性', desc: '点积其实是一个 1×2 矩阵' },
    { id: 12, title: '叉积', desc: '垂直于两者的那根向量' },
    { id: 99, title: '自由沙盒', desc: '不设任务，随便拖' }
];

window.LABS = [
    /* ---------- 第 1 章 ---------- */
    {
        id: '1-1', chapter: 1, title: '放置你的第一个向量',
        brief: '向量不只是两个数，它是<strong>空间里的一段位移</strong>：从原点指向某个位置。' +
               '横向是 x 轴，纵向是 y 轴，每一格是 1 个单位。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false,
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: 'v', draggable: true }],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'place', text: '把 v 放到 (2, 1)：向右 2 格、向上 1 格',
              check: { type: 'vector-at', target: 'v', to: [2, 1], tol: 0.15 } },
            { id: 'quiz', text: '辨析：(2, 1) 这两个数分别在说什么？',
              options: ['x 方向走 2 步、y 方向走 1 步，是两个方向的位移量',
                        '向量的长度是 2，方向是 1',
                        '空间里第 2 行第 1 列的那个点'],
              explains: ['✓ 对：坐标就是沿每个基方向走多少的系数，位移量才是它的本义。',
                         '✗ 不对：长度是 √(2²+1²)≈2.24，和坐标数字没有直接关系。',
                         '✗ 不对：那是把矩阵下标的读法套到点上，(2,1) 是位置不是行列号。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '点击 (2, 1) 对应的格点，或直接拖动箭头的圆点。',
            '拖到整数格点附近会自动吸附，不用追求像素级精确。',
            '📖 配套讲义：4-1 向量组及其线性组合（向量是线性组合的基本单位）']
    },
    {
        id: '1-2', chapter: 1, title: '向量加法：首尾相接',
        brief: '向量相加就是把两段位移<strong>首尾相接</strong>：分量各自相加。' +
               'a = (1, 2)、b = (2, 0)，所以 a + b = (1+2, 2+0) = (3, 2)。' +
               '减法是加法的特例：b − a = b + (−a)。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false,
            vectors: [
                { id: 'a', data: [1, 2], color: COLORS.ai, label: 'a', draggable: false },
                { id: 'b', data: [2, 0], color: COLORS.aj, label: 'b', draggable: false },
                { id: 'v', data: [0, 0], color: COLORS.v, label: 'a+b', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'sum', text: '把金色向量拖到 a + b 的终点 (3, 2)',
              check: { type: 'vector-at', target: 'v', to: [3, 2], tol: 0.15 } },
            { id: 'sub', text: '再拖到 b − a 的终点 (1, −2)：减法就是加上反向量',
              check: { type: 'vector-at', target: 'v', to: [1, -2], tol: 0.15 } },
            { id: 'quiz', text: '辨析：a + b 和 b + a 有什么关系？',
              options: ['一般不相等，顺序不同结果也不同',
                        '完全相等：向量加法满足交换律',
                        '长度相等，但方向不同'],
              explains: ['✗ 不对：顺序重要是矩阵乘法的坑，不是向量加法，a + b 恒等于 b + a。',
                         '✓ 对：先走 a 再走 b，和先走 b 再走 a，终点是同一点，也就是平行四边形的那条对角线。',
                         '✗ 不对：分量相加 (a₁+b₁, a₂+b₂) 与顺序无关，结果完全相同。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '分量分别相加：x 是 1+2 = 3，y 是 2+0 = 2。',
            '想象先走 a，再从 a 的终点接着走 b，终点就是 a + b。',
            '📖 配套讲义：4-1 向量组及其线性组合（向量加法与线性组合）']
    },
    {
        id: '1-3', chapter: 1, title: '数乘：拉伸与反向',
        brief: '向量乘一个数（<strong>标量</strong>）就是按比例拉伸：2a 与 a 同方向、长度翻倍；' +
               '−a 则方向相反。图中 a = (1, 2)。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false,
            vectors: [
                { id: 'a', data: [1, 2], color: COLORS.ai, label: 'a', draggable: false },
                { id: 'v', data: [0, 0], color: COLORS.v, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'scale2', text: '拖动 v，使它等于 2a = (2, 4)',
              check: { type: 'vector-at', target: 'v', to: [2, 4], tol: 0.15 } },
            { id: 'neg', text: '再拖 v，使它等于 −a = (−1, −2)',
              check: { type: 'vector-at', target: 'v', to: [-1, -2], tol: 0.15 } },
            { id: 'quiz', text: '辨析：数乘 0.5a 与 −0.5a 的共同点是什么？',
              options: ['方向相同，长度也相同',
                        '都指向与 a 相反的方向',
                        '都落在 a 所在的那条过原点的直线上'],
              explains: ['✗ 不对：−0.5a 与 0.5a 方向正好相反，只是长度相同。',
                         '✗ 不对：只有带负号的 −0.5a 反向，0.5a 与 a 同向。',
                         '✓ 对：数乘只会把向量留在原来那条直线上，正数同向、负数反向。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '2a 就是每个分量乘 2：(1×2, 2×2)。',
            '负号把箭头掉转 180°，指向原点另一侧，长度不变。',
            '📖 配套讲义：4-1 向量组及其线性组合（数乘就是「组合系数」的原型）']
    },
    {
        id: '1-4', chapter: 1, title: '长度与单位向量',
        brief: '向量长度 |v| = √(x² + y²)（勾股定理）。长度为 1 的向量叫<strong>单位向量</strong>：' +
               '只保留方向、去掉长度。把 v 调成与 u = (3, 4) 同方向的单位向量。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false,
            vectors: [
                { id: 'u', data: [3, 4], color: COLORS.ai, label: 'u', draggable: false },
                { id: 'v', data: [0, 0], color: COLORS.v, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'same', text: '先把 v 拖到 (1.5, 2)：让它落在 u 所在的那条过原点直线上',
              check: { type: 'vector-at', target: 'v', to: [1.5, 2], tol: 0.15 } },
            { id: 'unit', text: '再拖到 (0.6, 0.8)：这就是 u 的<strong>单位向量</strong>，长度正好 1',
              check: { type: 'vector-at', target: 'v', to: [0.6, 0.8], tol: 0.08 } },
            { id: 'quiz', text: '辨析：把 u = (3, 4) 变成单位向量，为什么要除以 5？',
              options: ['因为 5 是 (3, 4) 的长度，除以长度就把长度变成 1',
                        '因为 3 和 4 的平均数取整是 5',
                        '因为单位向量的坐标必须是 0.6 和 0.8'],
              explains: ['✓ 对：|(3,4)| = √(9+16) = 5，除以自身长度后模长恰好为 1，方向不变。',
                         '✗ 不对：平均数与长度无关，长度要用平方和开根号。',
                         '✗ 不对：0.6 与 0.8 只是这个例子的结果，换个方向数字就变了。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '|(3, 4)| = √(9+16) = 5。',
            'u 除以它的长度 5：(3/5, 4/5) = (0.6, 0.8)。',
            '📖 配套讲义：4-1 向量组及其线性组合（长度与单位向量）']
    },
    /* ---------- 第 2 章 ---------- */
    {
        id: '2-1', chapter: 2, title: '矩阵的列 = 变换后的基向量',
        brief: 'î = (1, 0)、ĵ = (0, 1) 叫<strong>标准基向量</strong>。一个 2×2 矩阵的两列，' +
               '就是 î 与 ĵ 变换之后的落点——这是理解矩阵最重要的一幅图。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            interact: { dragColumns: true }
        },
        tasks: [
            { id: 'col1', text: '拖动粉色 Aî 的端点，把它放到 (2, 1)',
              check: { type: 'matrix-col-at', col: 0, to: [2, 1], tol: 0.15 } },
            { id: 'col2', text: '再拖动紫色 Aĵ 的端点，把它放到 (0, 2)',
              check: { type: 'matrix-col-at', col: 1, to: [0, 2], tol: 0.15 } },
            { id: 'quiz', text: '辨析：矩阵的第 1 列是谁的落点？',
              options: ['任意向量 v 的落点',
                        'î = (1, 0) 的落点',
                        'ĵ = (0, 1) 的落点'],
              explains: ['✗ 不对：v 的落点是 Av，由两列组合而成，不属于单独某一列。',
                         '✓ 对：A·î 正好取出 A 的第 1 列，所以第 1 列天然属于 î。',
                         '✗ 不对：ĵ 的落点是第 2 列，也就是紫色那一根。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '右侧矩阵面板会随拖拽实时变化，注意第 1 列的数字就是 Aî 的坐标。',
            '绿色网格是整个平面变换后的样子：两列一定，网格就定了。',
            '📖 配套讲义：2-1 矩阵及其运算（矩阵的列 = 基向量的落点）']
    },
    {
        id: '2-2', chapter: 2, title: '基向量与线性组合',
        brief: '任何向量都能写成基向量的<strong>线性组合</strong>：v = x·î + y·ĵ。' +
               '坐标 (x, y) 就是组合的<em>系数</em>。' +
               '把金色 v 拖到目标点，虚线路程就是它被拆成两步的过程。',
        scene: {
            space: '2d', matrix: null, basis: true, tgrid: false, comboPath: true,
            vectors: [
                { id: 'u', data: [1, 0], color: COLORS.ai, label: 'î', draggable: false },
                { id: 'w', data: [0, 1], color: COLORS.aj, label: 'ĵ', draggable: false },
                { id: 'v', data: [0, 0], color: COLORS.v, label: 'v', draggable: true }
            ],
            targetPoint: { point: [2, 1], label: '目标' },
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'combo', text: '把 v 拖到 (2, 1)：也就是 2·î + 1·ĵ',
              check: { type: 'vector-at', target: 'v', to: [2, 1], tol: 0.15 } },
            { id: 'quiz', text: '辨析：坐标 (2, 1) 里的两个数，本质上是什么？',
              options: ['向量的起点和终点',
                        '向量的长度和角度',
                        '两个方向的位移量，也就是组合的系数'],
              explains: ['✗ 不对：起点固定在原点，坐标描述的是终点相对原点的位移。',
                         '✗ 不对：长度是 √5、角度约 26.6°，都不是坐标里的那两个数。',
                         '✓ 对：坐标就是沿每个基方向走多少的系数；换一套基，同一根箭头的坐标就变了。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '沿粉色 î 方向走 2 步，再沿紫色 ĵ 方向走 1 步。',
            '虚线路径就是 v 被拆成两段的组合过程，右上角有实时系数读数。',
            '📖 配套讲义：4-1 向量组及其线性组合（线性组合的定义）']
    },
    {
        id: '2-3', chapter: 2, title: '张成：能到达哪里？',
        brief: '两根不共线的向量的<strong>所有线性组合</strong>能铺满整个平面——' +
               '这叫它们的<em>张成</em>（span）。青色就是两列的张成。' +
               '先把它铺满平面，再亲手拖成共线，看它怎么塌缩。',
        scene: {
            space: '2d', matrix: [[1, 1], [1, 1]], basis: true, tgrid: true, spanView: true,
            vectors: [],
            metric: 'rank',
            interact: { dragColumns: true }
        },
        tasks: [
            { id: 'full', text: '现在秩是 1（青色只剩一条线）。拖动两列让秩变成 2，让张成铺满整个平面',
              check: { type: 'rank', value: 2 } },
            { id: 'quiz', text: '辨析：秩是 2 意味着什么？',
              options: ['两列贡献了两个独立方向，能组合出平面上任何向量',
                        '矩阵有两行',
                        '矩阵的元素都大于 0'],
              explains: ['✓ 对：两个独立方向就张成整个平面，任何 b 都能被拼出来，方程组恒有解。',
                         '✗ 不对：行数是矩阵的形状，和秩不是一回事，秩可以小于行数。',
                         '✗ 不对：秩与元素的正负无关，[[−1,0],[0,−1]] 的秩也是 2。'],
              check: { type: 'choice', correct: 0 } },
            { id: 'quiz2', text: '辨析：rank(A) = 1 时，方程 Av = b 对任意 b 都有解吗？',
              options: ['一定无解',
                        '不一定：b 必须正好落在那条直线上，否则无解',
                        '有解，秩不为 0 就总有解'],
              explains: ['✗ 不对：线上的 b 是有解的，而且此时解还不唯一，有一个维度被压掉了。',
                         '✓ 对：列空间是一条线时，只有 b 在线上才有解，这就是无解的几何含义。',
                         '✗ 不对：秩 1 只能拼出一条线上的向量，线外的 b 永远拼不出来。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '把第 2 列拖到与第 1 列不共线的方向，秩立刻变成 2。',
            '看屏幕左上角的提示：青色区域 = 整个平面（秩 2），青色直线 = 一条线（秩 1）。',
            '📖 配套讲义：4-1 向量组及其线性组合（张成 = 所有线性组合的集合）']
    },
    {
        id: '2-4', chapter: 2, title: '线性相关：多余的列',
        brief: '如果一列是另一列的<strong>倍数</strong>，它就没有带来新方向——两列<em>线性相关</em>。' +
               '这时张成从平面塌缩成一条线，行列式也随之变成 0。' +
               '拖动两列感受这件事：行列式归零的那一瞬间，绿色网格会被压扁。',
        scene: {
            space: '2d', matrix: [[2, 1], [1, 2]], basis: true, tgrid: true, spanView: true,
            vectors: [],
            metric: 'rank',
            interact: { dragColumns: true }
        },
        tasks: [
            { id: 'dep', text: '让两列线性相关：把矩阵调成 [[1, 2], [2, 4]]，也就是第 2 列 = 2 × 第 1 列',
              check: { type: 'match-matrix', matrix: [[1, 2], [2, 4]], tol: 0.15 } },
            { id: 'rank1', text: '确认此时 rank(A) = 1，青色区域塌缩成一条直线',
              check: { type: 'rank', value: 1 } },
            { id: 'quiz', text: '辨析：线性相关是不是两列长得一模一样？',
              options: ['是，必须完全相同才算相关',
                        '不是，只有某一列全为 0 才算相关',
                        '不是，只要一列是另一列的倍数就算相关，正数倍、负数倍、零倍都算'],
              explains: ['✗ 不对：完全相同只是相关的特例，倍数关系就够了。',
                         '✗ 不对：零向量确实是相关的极端情形，但相关远不止这一种。',
                         '✓ 对：(1,2) 与 (−3,−6) 相关，(1,2) 与 (0,0) 也相关，关键在于有没有带来新方向。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '第 2 列 = 2 × 第 1 列是最简单的做法：(1, 2) → (2, 4)。',
            '也可以让某一列变成 (0, 0)：零向量与任何向量都线性相关。',
            '📖 配套讲义：4-2 向量组的线性相关性（线性相关 / 无关）']
    },
    {
        id: '2-5', chapter: 2, title: '列空间与秩',
        brief: '两列的所有线性组合构成一个集合，叫矩阵的<strong>列空间</strong>。' +
               '列空间有几个维度，矩阵的<em>秩</em>就是几。' +
               '两列不共线则列空间是整个平面、秩为 2；两列共线则塌成一条线、秩为 1。' +
               '屏幕上的青色区域或直线，就是列空间。',
        scene: {
            space: '2d', matrix: [[1, 2], [2, 1]], basis: true, tgrid: true, spanView: true,
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: 'b', draggable: true }],
            targetPoint: { point: [3, 3], label: '目标 b' },
            metric: 'rank',
            interact: { clickPlace: true, dragVectors: true, dragColumns: true }
        },
        tasks: [
            { id: 'span', text: '把金色 b 拖到 (3, 3)，确认它落在两列张成的平面上',
              check: { type: 'vector-at', target: 'v', to: [3, 3], tol: 0.2 } },
            { id: 'quiz', text: '辨析：列空间和矩阵的列是同一件事吗？',
              options: ['不是：列空间是两列所有线性组合的集合，通常比两根本身大得多',
                        '是，列空间就是所有列组成的集合',
                        '不是：列空间是矩阵的行组成的集合'],
              explains: ['✓ 对：取所有倍数再相加、铺出来的整个区域才是列空间；两根本身只是它的两个方向。',
                         '✗ 不对：只有两根列向量的话，集合里就两个元素，谈不上空间。',
                         '✗ 不对：行组成的集合叫行空间，是另一个概念。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '列空间 = 所有可能的 Av 组成的集合，也就是所有可能的结果向量。',
            '本关两列 (1,2) 与 (2,1) 不共线，所以列空间是整个平面，任何 b 都在里面。',
            '📖 配套讲义：4-2 向量组的线性相关性（秩与极大无关组）']
    },
    {
        id: '2-6', chapter: 2, title: '秩：列空间的维度',
        brief: '一个 2×3 的矩阵有三列，但每列只有两个分量，所以列空间不可能超过二维。' +
               '<strong>秩既不超过行数，也不超过列数。</strong>' +
               '第三列是零列，它对列空间完全没有贡献，拖动它试试看。',
        scene: {
            space: '2d', matrix: [[2, 1, 0], [1, 2, 0]], matrixSize: 2, basis: false, tgrid: true, spanView: true,
            vectors: [
                { id: 'c1', data: [2, 1], color: COLORS.ai, label: 'c₁', draggable: false },
                { id: 'c2', data: [1, 2], color: COLORS.aj, label: 'c₂', draggable: false },
                { id: 'c3', data: [0, 0], color: COLORS.v, label: 'c₃', draggable: true }
            ],
            targetPoint: { point: [4, 4], label: '目标 b' },
            metric: 'rank',
            interact: { clickPlace: false, dragVectors: true }
        },
        tasks: [
            { id: 'rank2', text: '前两列不共线，先确认 rank(A) = 2：三列也只张出整个平面',
              check: { type: 'rank', value: 2 } },
            { id: 'move', text: '把金色 c₃ 拖到 (2, 2)：注意 rank 完全没有变化',
              check: { type: 'vector-at', target: 'c3', to: [2, 2], tol: 0.25 } },
            { id: 'quiz', text: '辨析：一个 3×3 矩阵的秩可能是 4 吗？',
              options: ['不可能，3×3 的秩只能是 3',
                        '不可能：秩不超过 min(行数, 列数)，3×3 的秩最多是 3',
                        '可能，只要元素足够复杂'],
              explains: ['✗ 不对：秩也可以是 0、1 或 2，列相关时就会掉下来。',
                         '✓ 对：秩既不超过行数也不超过列数；3×3 矩阵的秩只能是 0、1、2、3。',
                         '✗ 不对：秩的上限由矩阵的形状决定，不由元素的复杂程度决定。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '注意面板里 rank(A) 的数字：多加一列不会自动让秩变大。',
            '列的根数不等于张成的维度，这是这一关最想让你记住的一句。',
            '📖 配套讲义：2-3 矩阵的公式（伴随矩阵与秩的不等式）（秩的定义与不等式）']
    },
    /* ---------- 第 3 章 ---------- */
    {
        id: '3-1', chapter: 3, title: '矩阵 = 对整个空间的变换',
        brief: '矩阵不只作用于一个向量，它作用于<strong>空间中的每一个点</strong>：' +
               '整张网格一起变形。点击「播放变换」，看网格如何从单位方格连续地变成变换后的样子。',
        scene: {
            space: '2d', matrix: [[1, 1], [0, 1]], basis: true, tgrid: true, shape: 'square',
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            interact: { dragVectors: true, dragColumns: true },
            toolbar: [
                { id: 'play', label: '▶ 播放变换', action: 'play-transform' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' },
                { id: 'shear', label: '剪切 ĵ→(1,1)', action: 'preset', matrix: [[1, 1], [0, 1]] },
                { id: 'rot', label: '旋转 90°', action: 'preset', matrix: [[0, -1], [1, 0]] }
            ]
        },
        tasks: [
            { id: 'play', text: '点击「播放变换」看一次完整的变形动画',
              check: { type: 'actions', all: ['play-transform'] } },
            { id: 'av', text: '把矩阵调成旋转 90°（点预设，或直接拖两列），让 Av 落到 (−1, 1)',
              check: { type: 'av-at', to: [-1, 1], tol: 0.2 } },
            { id: 'quiz', text: '辨析：变换之后的网格里，直线还是直线吗？原点还在原位吗？',
              options: ['直线会变弯，原点会移动',
                        '直线仍是直线，但原点会移动',
                        '直线仍是直线，原点固定不动'],
              explains: ['✗ 不对：弯曲就不是线性变换了；原点移动同理，那属于仿射变换。',
                         '✗ 不对：原点必须固定（A·0 = 0），否则不是线性变换。',
                         '✓ 对：这两条正是线性的定义性特征：保持直线、保持原点。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '旋转 90° 时 î 落到 (0,1)、ĵ 落到 (−1,0)，所以矩阵是 [[0,−1],[1,0]]。',
            'v = (1,1) 被旋转 90° 后是 (−1,1)，长度不变、方向转了 90°。',
            '📖 配套讲义：2-1 矩阵及其运算（矩阵作为变换的几何含义）']
    },
    {
        id: '3-2', chapter: 3, title: '向量去哪了：v → Av',
        brief: '矩阵 A 把向量 v 映到 <strong>Av</strong>（绿色虚线）。' +
               '因为变换是线性的，Av = x·Aî + y·Aĵ——系数不变，<em>只是基被换掉了</em>。' +
               '拖动 v 和两列，观察这条关系始终成立。',
        scene: {
            space: '2d', matrix: [[1, 1], [0, 1]], basis: true, tgrid: true,
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            interact: { dragVectors: true, dragColumns: true }
        },
        tasks: [
            { id: 'av', text: '拖动 v 或两列，让绿色的 Av 落到 (2, 2)',
              check: { type: 'av-at', to: [2, 2], tol: 0.2 } },
            { id: 'quiz', text: '辨析：v 变成 Av 的整个过程中，什么东西没有变？',
              options: ['v 用两列表示的组合系数没有变',
                        'v 的长度没有变',
                        'v 的方向没有变'],
              explains: ['✓ 对：Av = x·Aî + y·Aĵ，系数 (x, y) 原封不动，变的只是基向量本身。',
                         '✗ 不对：剪切会把长度改掉，长度并不守恒。',
                         '✗ 不对：剪切会改变方向，只有特征方向例外。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '最简单的做法：让矩阵变回单位阵，再把 v 拖到 (2, 2)。',
            '或者保持剪切矩阵，给 v 一个合适的值让 Av 命中 (2, 2)。',
            '📖 配套讲义：2-1 矩阵及其运算（矩阵与向量的乘法）']
    },
    {
        id: '3-3', chapter: 3, title: '变换的形状：旋转 90°',
        brief: '旋转 90° 后，î 落到 (0, 1)，ĵ 落到 (−1, 0)。' +
               '所以旋转矩阵就是 <strong>[[0, −1], [1, 0]]</strong>。' +
               '试着用「旋转 90°」预设，或者亲手把两列拖到位。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            metric: 'det',
            interact: { dragVectors: true, dragColumns: true },
            toolbar: [
                { id: 'rot90', label: '旋转 90°', action: 'preset', matrix: [[0, -1], [1, 0]] },
                { id: 'rot-90', label: '反向旋转 90°', action: 'preset', matrix: [[0, 1], [-1, 0]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'c1', text: '把粉色 Aî 拖到 (0, 1)',
              check: { type: 'matrix-col-at', col: 0, to: [0, 1], tol: 0.15 } },
            { id: 'c2', text: '把紫色 Aĵ 拖到 (−1, 0)',
              check: { type: 'matrix-col-at', col: 1, to: [-1, 0], tol: 0.15 } },
            { id: 'quiz', text: '辨析：旋转 90° 之后，v = (1, 1) 跑到哪里去了？',
              options: ['(1, −1)：上下翻转',
                        '(−1, 1)：长度不变，方向转了 90°',
                        '(1, 1)：旋转不改变向量'],
              explains: ['✗ 不对：(1,−1) 是关于 x 轴的反射，不是旋转 90°。',
                         '✓ 对：A·(1,1) = (0·1 + (−1)·1, 1·1 + 0·1) = (−1, 1)，模长仍是 √2。',
                         '✗ 不对：只有原点是不动点，其它向量都会转，除非它恰好是零向量。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '旋转 90° 时 î 从 (1,0) 转到 (0,1)，ĵ 从 (0,1) 转到 (−1,0)。',
            '旋转矩阵的两列都是单位向量，而且互相垂直，这是旋转的特征。',
            '📖 配套讲义：2-1 矩阵及其运算（具体的矩阵运算）']
    },
    {
        id: '3-4', chapter: 3, title: '投影：把平面压到一条线上',
        brief: '投影把每个向量垂直投到一条直线上。投到 x 轴时，î 原地不动（落在 (1,0)），' +
               'ĵ 直接落到原点——所以矩阵是 <strong>[[1, 0], [0, 0]]</strong>。' +
               '整个平面被压扁了：投影丢失信息，所以它不可逆。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, spanView: true,
            vectors: [{ id: 'v', data: [1.5, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            metric: 'rank',
            interact: { dragVectors: true, dragColumns: true },
            toolbar: [
                { id: 'proj-x', label: '投影到 x 轴', action: 'preset', matrix: [[1, 0], [0, 0]] },
                { id: 'proj-y', label: '投影到 y 轴', action: 'preset', matrix: [[0, 0], [0, 1]] },
                { id: 'proj-diag', label: '投影到 y = x', action: 'preset', matrix: [[0.5, 0.5], [0.5, 0.5]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'px', text: '点击「投影到 x 轴」，把矩阵调成 [[1, 0], [0, 0]]',
              check: { type: 'match-matrix', matrix: [[1, 0], [0, 0]], tol: 0.06 } },
            { id: 'flat', text: '确认秩掉到 1（青色只剩一条线），行列式也变成 0',
              check: { type: 'rank', value: 1 } },
            { id: 'quiz', text: '辨析：投影矩阵为什么不可逆？',
              options: ['因为它不是方阵',
                        '因为它的元素里有 0',
                        '因为方向上不同的向量被压到同一个点，无法反推原来是谁'],
              explains: ['✗ 不对：[[1,0],[0,0]] 是标准的 2×2 方阵。',
                         '✗ 不对：[[2,0],[0,1]] 里也有 0，但它可逆。关键在秩，不在元素。',
                         '✓ 对：丢掉的那个维度再也补不回来，所有 ĵ 方向的差别都被抹平了。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            'x 轴上的向量不会被投影改变；y 方向的成分会被整个丢掉。',
            '投影到 y = x 的矩阵是 [[0.5, 0.5], [0.5, 0.5]]，两列都是 (0.5, 0.5)，所以秩是 1。',
            '📖 配套讲义：2-3 矩阵的公式（伴随矩阵与秩的不等式）（投影是秩亏的（det = 0））']
    },
    {
        id: '3-5', chapter: 3, title: '旋转任意角度',
        brief: '旋转 θ 角：î 落到 (cosθ, sinθ)，ĵ 落到 (−sinθ, cosθ)，' +
               '所以旋转矩阵是 <strong>[[cosθ, −sinθ], [sinθ, cosθ]]</strong>。' +
               'θ = 45° 时 cosθ = sinθ ≈ 0.707。旋转不改变任何向量的长度，也不改变面积。',
        scene: {
            space: '2d', matrix: [[0.7071, -0.7071], [0.7071, 0.7071]], basis: true, tgrid: true, shape: 'square',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true },
            toolbar: [
                { id: 'rot45', label: '旋转 45°', action: 'preset', matrix: [[0.7071, -0.7071], [0.7071, 0.7071]] },
                { id: 'rot90', label: '旋转 90°', action: 'preset', matrix: [[0, -1], [1, 0]] },
                { id: 'rot30', label: '旋转 30°', action: 'preset', matrix: [[0.866, -0.5], [0.5, 0.866]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'twice', text: '现在已经是 45°。点击「旋转 45°」两次：两次 45° 应该正好等于 90°',
              check: { type: 'match-matrix', matrix: [[0, -1], [1, 0]], tol: 0.06 } },
            { id: 'det1', text: '确认旋转的 det(A) = 1（面积一点没变）',
              check: { type: 'det', op: 'eq', value: 1, tol: 0.06 } },
            { id: 'quiz', text: '辨析：旋转矩阵的 det 为什么恒等于 1？',
              options: ['因为旋转不改变面积，正方形转完还是同样大的正方形',
                        '因为对角线元素相乘恰好是 1',
                        '因为旋转矩阵的列都是单位向量'],
              explains: ['✓ 对：det 就是面积缩放倍数，旋转是刚体运动，面积不变，所以 det = 1。',
                         '✗ 不对：cos²θ + sin²θ = 1 是结果，不是原因；原因在几何上。',
                         '✗ 不对：两列确实是单位向量，但列是单位向量不足以保证 det = 1，反射的 det 是 −1。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '两次 45° 的复合就是 90°，所以点两次「旋转 45°」即可。',
            '旋转矩阵的 det = cos²θ − (−sinθ)·sinθ = cos²θ + sin²θ = 1。',
            '📖 配套讲义：6-2 正交变换及配方法化标准形（正交变换就是旋转 / 反射）']
    },
    {
        id: '3-6', chapter: 3, title: '剪切：把正方形推成平行四边形',
        brief: '<strong>剪切</strong>（shear）固定一个基向量、把另一个推斜：' +
               'î 不动、ĵ 被推到 (1, 1)，矩阵是 [[1, 1], [0, 1]]。' +
               '网格像一叠纸牌被推开——注意每一层只是平移，<em>面积没有变</em>。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true },
            toolbar: [
                { id: 'shear', label: '剪切 ĵ→(1,1)', action: 'preset', matrix: [[1, 1], [0, 1]] },
                { id: 'shear-h', label: '横向剪切 î→(1,1)', action: 'preset', matrix: [[1, 0], [1, 1]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'shear', text: '点击「剪切 ĵ→(1,1)」，把矩阵调成 [[1, 1], [0, 1]]',
              check: { type: 'match-matrix', matrix: [[1, 1], [0, 1]], tol: 0.06 } },
            { id: 'det1', text: '确认 det(A) 仍然是 1：绿色方块被推斜了，但面积没变',
              check: { type: 'det', op: 'eq', value: 1, tol: 0.06 } },
            { id: 'quiz', text: '辨析：剪切把正方形推成了平行四边形，面积为什么没变？',
              options: ['因为剪切只改变了方向，没有改变长度',
                        '因为剪切的 det = 1，而行列式就是面积缩放倍数',
                        '因为平行四边形和正方形面积总是相等'],
              explains: ['✗ 不对：ĵ 的长度从 1 变成了 √2，长度确实变了，但面积没变。',
                         '✓ 对：形状变了，但面积比例恰好是 1，这就是 det 的几何含义。',
                         '✗ 不对：只有同底等高的平行四边形面积才相等；这里是因为行列式恰好为 1。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '剪切的 det = 1×1 − 1×0 = 1。',
            '把第 2 列从 (0,1) 拖到 (1,1)，单格手柄拖拽即可精确到位。',
            '📖 配套讲义：2-1 矩阵及其运算（剪切矩阵的乘法验证）']
    },
    /* ---------- 第 4 章 ---------- */
    {
        id: '4-1', chapter: 4, title: '复合变换 = 矩阵相乘',
        brief: '先做旋转 B，再做剪切 A，等价于<strong>一个矩阵 A·B</strong>。' +
               '注意顺序：写在右边的先作用。矩阵乘法就是<em>变换的复合</em>。' +
               '用工具条依次施加 A、B，再与直接给出的 A·B 对比。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            interact: {},
            toolbar: [
                { id: 'apply-b', label: '① 施加 B（旋转 90°）', action: 'mul-left', matrix: [[0, -1], [1, 0]], log: 'apply-b' },
                { id: 'apply-a', label: '② 施加 A（剪切）', action: 'mul-left', matrix: [[1, 1], [0, 1]], log: 'apply-a' },
                { id: 'show-ab', label: '直接看复合结果 A·B', action: 'preset', matrix: [[1, -1], [1, 0]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'seq', text: '依次点击「① 施加 B」「② 施加 A」，亲手做出 A·B',
              check: { type: 'actions', all: ['apply-b', 'apply-a'], ordered: true } },
            { id: 'same', text: '确认结果与直接点击「直接看复合结果 A·B」得到的矩阵一致',
              check: { type: 'match-matrix', matrix: [[1, -1], [1, 0]], tol: 0.06 } },
            { id: 'quiz', text: '辨析：A·B 里，哪一个变换先作用在向量上？',
              options: ['A 先作用，因为 A 写在左边',
                        '两个变换同时作用，没有先后',
                        'B 先作用，因为 B 写在右边'],
              explains: ['✗ 不对：写在前面的反而后作用。可以验证：A·B 的第 1 列 = A 作用于 B 的第 1 列。',
                         '✗ 不对：复合变换是有顺序的，这也正是 AB 不等于 BA 的原因。',
                         '✓ 对：矩阵乘法从右往左读，最右边的变换最先作用在向量上。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            'A·B 的第 1 列 = A 作用于 B 的第 1 列。',
            '每次点「施加 X」都在做 M ← X·M，也就是先做原来的 M，再做 X。',
            '📖 配套讲义：2-1 矩阵及其运算（矩阵乘法的定义）']
    },
    {
        id: '4-2', chapter: 4, title: '顺序很重要：AB 不等于 BA',
        brief: '先旋转再剪切，和先剪切再旋转，<strong>结果完全不同</strong>。' +
               '分别点两个按钮看两种顺序的最终网格，体会矩阵乘法为什么不能交换。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            interact: {},
            toolbar: [
                { id: 'rot-first', label: '先旋转 → 后剪切', action: 'preset', matrix: [[1, -1], [1, 0]], log: 'view-ab' },
                { id: 'shear-first', label: '先剪切 → 后旋转', action: 'preset', matrix: [[0, -1], [1, 1]], log: 'view-ba' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'both', text: '分别点击两个按钮，对比两种顺序的最终网格差异',
              check: { type: 'actions', all: ['view-ab', 'view-ba'] } },
            { id: 'neq', text: '确认「先旋转后剪切」的结果矩阵是 [[1, −1], [1, 0]]',
              check: { type: 'match-matrix', matrix: [[1, -1], [1, 0]], tol: 0.06 } },
            { id: 'quiz', text: '辨析：既然 AB 不等于 BA，那 det(AB) 和 det(BA) 相等吗？',
              options: ['相等：det(AB) = det(A)·det(B) = det(BA)',
                        '不相等，矩阵都不同了，行列式当然也不同',
                        '只有 A、B 都可逆时才相等'],
              explains: ['✓ 对：det(AB) = det(A)·det(B)，右边是两个数的乘积，交换顺序不影响结果。',
                         '✗ 不对：这是陷阱。矩阵作为数组确实不同，但行列式是一个数，数的乘法可以交换。',
                         '✗ 不对：不需要可逆条件，det 的乘法公式对任意方阵都成立。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '注意单位正方形被推成的平行四边形，两种顺序下形状完全不同。',
            '按钮上写的是作用顺序；矩阵面板显示的是最终的那个复合矩阵。',
            '📖 配套讲义：2-1 矩阵及其运算（AB 一般不等于 BA）']
    },
    {
        id: '4-3', chapter: 4, title: '逐列看懂矩阵乘法',
        brief: '先做变换 B、再做变换 A，等价于<strong>一个矩阵 A·B</strong>。' +
               '注意顺序：写在右边的先作用。AB 的第 1 列 = A 乘以 B 的第 1 列，' +
               '也就是「矩阵乘法就是对每一列分别做变换」。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            interact: {},
            toolbar: [
                { id: 'apply-b', label: '① 施加 B（旋转 90°）', action: 'mul-left', matrix: [[0, -1], [1, 0]], log: 'apply-b' },
                { id: 'apply-a', label: '② 施加 A（剪切）', action: 'mul-left', matrix: [[1, 1], [0, 1]], log: 'apply-a' },
                { id: 'show-ab', label: '直接看 A·B 结果', action: 'preset', matrix: [[1, -1], [1, 0]] },
                { id: 'show-ba', label: '看另一种顺序 B·A', action: 'preset', matrix: [[0, -1], [1, 1]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'seq', text: '依次点击「① 施加 B」再点「② 施加 A」，亲手做出 A·B',
              check: { type: 'actions', all: ['apply-b', 'apply-a'], ordered: true } },
            { id: 'result', text: '确认结果矩阵是 [[1, −1], [1, 0]]',
              check: { type: 'match-matrix', matrix: [[1, -1], [1, 0]], tol: 0.05 } },
            { id: 'quiz', text: '辨析：既然 AB 不等于 BA，那么 det(AB) 和 det(BA) 相等吗？',
              options: ['只有 A、B 都可逆时才相等',
                        '相等：det(AB) = det(A)·det(B) = det(BA)',
                        '不相等，矩阵都不同了，行列式当然也不同'],
              explains: ['✗ 不对：不需要可逆条件，det 的乘法公式对任意方阵都成立。',
                         '✓ 对：det(AB) = det(A)·det(B)，右边是两个数的乘积，交换顺序不影响结果。',
                         '✗ 不对：这是陷阱。矩阵作为数组确实不同，但行列式是一个数，数的乘法可以交换。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'A·B 的第 1 列 = A 作用于 B 的第 1 列。',
            '每次点「施加 X」都在做 M ← X·M，也就是先做原来的 M，再做 X。',
            '📖 配套讲义：2-1 矩阵及其运算（矩阵乘法为什么这样定义）']
    },
    {
        id: '4-4', chapter: 4, title: '三个变换的复合：结合律',
        brief: '三个变换复合时，<strong>(AB)C 和 A(BC) 结果相同</strong>——矩阵乘法满足结合律。' +
               '按钮按 C → B → A 的顺序施加（最右边的先作用），看最终矩阵。' +
               '结合律允许我们随意加括号，但不允许交换顺序。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            interact: {},
            toolbar: [
                { id: 'apply-c', label: '① 施加 C（x 方向放大 2 倍）', action: 'mul-left', matrix: [[2, 0], [0, 1]], log: 'apply-c' },
                { id: 'apply-b', label: '② 施加 B（旋转 90°）', action: 'mul-left', matrix: [[0, -1], [1, 0]], log: 'apply-b' },
                { id: 'apply-a', label: '③ 施加 A（剪切）', action: 'mul-left', matrix: [[1, 1], [0, 1]], log: 'apply-a' },
                { id: 'preset-abc', label: '直接看 (AB)C', action: 'preset', matrix: [[2, -1], [2, 0]], log: 'view-abc' },
                { id: 'preset-abc2', label: '直接看 A(BC)', action: 'preset', matrix: [[2, -1], [2, 0]], log: 'view-abc2' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'seq', text: '依次点击 ①②③，把三个变换按 C → B → A 的顺序复合起来',
              check: { type: 'actions', all: ['apply-c', 'apply-b', 'apply-a'], ordered: true } },
            { id: 'assoc', text: '确认最终矩阵是 [[2, −1], [2, 0]]，也就是 A·B·C',
              check: { type: 'match-matrix', matrix: [[2, -1], [2, 0]], tol: 0.06 } },
            { id: 'quiz', text: '辨析：结合律 (AB)C = A(BC) 说明了什么？',
              options: ['三个矩阵相乘的结果一定是单位阵',
                        '矩阵乘法可以交换顺序',
                        '加括号的顺序不影响结果，但乘的顺序不能交换'],
              explains: ['✗ 不对：这里的复合结果是 [[2, −1], [2, 0]]，不是单位阵。',
                         '✗ 不对：结合律讲的是加括号，交换律讲的是换位置，这是两件事。',
                         '✓ 对：结合律只保证括号可以随便加，AB 与 BA 仍然一般不相等。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '矩阵乘法从右往左读：C 最先作用，A 最后作用。',
            'A·B·C 可以逐次算：先算 A·B 再乘 C，或者先算 B·C 再左乘 A，结果一样。',
            '📖 配套讲义：2-1 矩阵及其运算（矩阵乘法的结合律）']
    },
    /* ---------- 第 5 章 ---------- */
    {
        id: '5-1', chapter: 5, title: '行列式 = 面积的缩放倍数',
        brief: '蓝色小方块（边长 0.5）被矩阵变成绿色平行四边形。' +
               '两者面积之比<strong>就是 det(A)</strong>——用半格方块是为了让原形与变形同时看得见。' +
               '拖动两列看它怎么变。',
        scene: {
            space: '2d', matrix: [[2, 0], [0, 1]], basis: true, tgrid: true, shape: 'area',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true }
        },
        tasks: [
            { id: 'two', text: '拖动两列，让 det(A) = 2',
              check: { type: 'det', op: 'eq', value: 2, tol: 0.15 } },
            { id: 'neg', text: '继续拖，让 det(A) 变成负数（观察空间被「翻面」）',
              check: { type: 'det', op: 'lt', value: -0.2 } },
            { id: 'zero', text: '再让 det(A) = 0：把平面压成一条线',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.08 } },
            { id: 'quiz', text: '辨析：det(A) = 0 意味着什么？',
              options: ['矩阵不可逆，信息被压没了，无法还原',
                        '矩阵是零矩阵',
                        '矩阵把面积放大了 0 倍但依然可逆'],
              explains: ['✓ 对：整个平面塌缩到一条线或一个点，不同输入落到同一输出，逆变换不存在。',
                         '✗ 不对：零矩阵只是 det = 0 的一种极端情形，[[1,1],[1,1]] 的 det 也是 0。',
                         '✗ 不对：面积变成 0 恰恰说明维度丢了，丢了就补不回来。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '2×2 的 det = a·d − b·c，也就是主对角线乘积减去副对角线乘积。',
            '让两列共线（一列是另一列的倍数），det 立刻变成 0。',
            '📖 配套讲义：1-1 二三阶行列式（二三阶行列式）']
    },
    {
        id: '5-2', chapter: 5, title: '负行列式 = 空间翻转',
        brief: '当 det(A) 小于 0 时，空间被<strong>翻转</strong>了，像照镜子一样：' +
               'î 与 ĵ 的左右手关系颠倒。观察绿色方块从蓝色方块的哪一侧翻了过去。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'area',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true },
            toolbar: [
                { id: 'flip-x', label: '翻 x 轴（上下镜像）', action: 'preset', matrix: [[1, 0], [0, -1]] },
                { id: 'flip-y', label: '翻 y 轴（左右镜像）', action: 'preset', matrix: [[-1, 0], [0, 1]] },
                { id: 'rot180', label: '旋转 180°', action: 'preset', matrix: [[-1, 0], [0, -1]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'flip', text: '点击「翻 x 轴」，让 det(A) = −1',
              check: { type: 'det', op: 'eq', value: -1, tol: 0.06 } },
            { id: 'quiz', text: '辨析：旋转 180° 的矩阵是 [[−1,0],[0,−1]]，它的 det 是多少？',
              options: ['det = 0，因为空间被压扁了',
                        'det = +1：两个方向都反了，等于绕了一圈，左右手关系没有变',
                        'det = −1，因为对角线上的元素都是负数'],
              explains: ['✗ 不对：这个矩阵是可逆的，面积没有被压成 0。',
                         '✓ 对：det = (−1)×(−1) − 0×0 = 1。旋转 180° 不改变朝向，面积比例仍是 1。',
                         '✗ 不对：不能只看单个元素的符号，两个负号相乘会变正。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'det = a·d − b·c，注意两个负号相乘会变正。',
            '翻一个轴 det 是 −1；同时翻两个轴等于旋转 180°，det 又回到 +1。',
            '📖 配套讲义：1-4 行列式的性质（性质 2：换行变号 = 空间翻转）']
    },
    {
        id: '5-3', chapter: 5, title: 'det = 0：空间被压扁',
        brief: '当两列<strong>共线</strong>时，整个平面被压成一条线，面积变成 0——' +
               '矩阵丢失了一个维度，这就是<em>奇异矩阵</em>。' +
               '拖动两列亲手制造一次塌缩。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'area', spanView: true,
            vectors: [],
            metric: 'rank',
            interact: { dragColumns: true }
        },
        tasks: [
            { id: 'zero', text: '拖动两列，让 det(A) = 0（青色列空间塌成一条线）',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.08 } },
            { id: 'rk', text: '确认此时 rank(A) = 1',
              check: { type: 'rank', value: 1 } },
            { id: 'quiz', text: '辨析：det = 0、rank 小于 2、奇异、不可逆，这几个说法是什么关系？',
              options: ['完全无关的四件事',
                        '只对方阵成立，矩形矩阵没有这些概念',
                        '说的是同一件事的不同侧面：面积为零、维度塌缩、没有逆矩阵'],
              explains: ['✗ 不对：它们由同一个几何事实串起来——有一个维度被压掉了。',
                         '✗ 不对：矩形矩阵确实没有行列式，但奇异与秩的概念仍然适用，只是说法要调整。',
                         '✓ 对：对 n×n 方阵来说，这四句话是等价的，可以互相推导。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '把第 2 列拖到第 1 列的倍数方向上，det 立刻归零。',
            '注意面板里 det 与 rank 是同时变化的：det = 0 与 rank 小于 2 总是同时出现。',
            '📖 配套讲义：1-6 行列式的计算（det = 0 与可逆性）']
    },
    {
        id: '5-4', chapter: 5, title: 'det(AB) = det(A) · det(B)',
        brief: 'A 把面积放大 2 倍，B 再放大 3 倍，复合变换自然放大 <strong>2 × 3 = 6 倍</strong>。' +
               '这就是 det 最重要的性质，也是面积缩放这个解释最直接的证据。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'area',
            vectors: [],
            metric: 'det',
            interact: {},
            toolbar: [
                { id: 'apply-a', label: '① 施加 A（x 方向 ×2）', action: 'mul-left', matrix: [[2, 0], [0, 1]], log: 'apply-a' },
                { id: 'apply-b', label: '② 施加 B（y 方向 ×3）', action: 'mul-left', matrix: [[1, 0], [0, 3]], log: 'apply-b' },
                { id: 'preset-ab', label: '直接看 A·B', action: 'preset', matrix: [[2, 0], [0, 3]], log: 'view-ab' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'seq', text: '依次点击 ①②，先放大 2 倍再放大 3 倍',
              check: { type: 'actions', all: ['apply-a', 'apply-b'], ordered: true } },
            { id: 'six', text: '确认复合矩阵的 det = 6，也就是 2 × 3',
              check: { type: 'det', op: 'eq', value: 6, tol: 0.1 } },
            { id: 'quiz', text: '辨析：det(AB) = det(A)·det(B) 为什么成立？',
              options: ['因为 A 先把面积缩放 det(A) 倍，B 再缩 det(B) 倍，两次缩放相乘',
                        '因为 det 一定是整数，整数乘法总成立',
                        '因为它只是代数公式，没有几何含义'],
              explains: ['✓ 对：面积缩放是逐次累乘的，先乘 det(A) 再乘 det(B)，总效果就是两者之积。',
                         '✗ 不对：det 完全可以是分数，比如 [[0.5,0],[0,1]] 的 det 是 0.5。',
                         '✗ 不对：这条性质恰恰有最直观的几何解释。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            'A·B 的对角线是 2 和 3，所以 det = 2×3 = 6。',
            '盯着绿色平行四边形的面积：它先变成 2 倍，再变成 6 倍。',
            '📖 配套讲义：1-4 行列式的性质（det(AB) = det(A)·det(B)）']
    },
    {
        id: '5-5', chapter: 5, title: 'det 与逆：det(A⁻¹) = 1 / det(A)',
        brief: 'A 把面积放大 4 倍，那么撤销它的 A⁻¹ 必然把面积缩回 <strong>1/4</strong>。' +
               '因为 A⁻¹·A = I，两边取 det 就有 det(A⁻¹)·det(A) = 1。',
        scene: {
            space: '2d', matrix: [[2, 0], [0, 2]], basis: true, tgrid: true, shape: 'area',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true },
            toolbar: [
                { id: 'apply-inv', label: '求出 A⁻¹ 并应用', action: 'mul-left-inv', matrix: [[2, 0], [0, 2]], log: 'apply-inv' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'four', text: '先确认现在 det(A) = 4（两个方向都放大 2 倍）',
              check: { type: 'det', op: 'eq', value: 4, tol: 0.1 } },
            { id: 'quarter', text: '点击「求出 A⁻¹ 并应用」，让 det 变成 1/4',
              check: { type: 'det', op: 'eq', value: 0.25, tol: 0.03 } },
            { id: 'quiz', text: '辨析：为什么 det(A⁻¹) 一定等于 1 / det(A)？',
              options: ['因为 det 只能取 1 或 −1',
                        '因为 A⁻¹·A = I，取 det 得 det(A⁻¹)·det(A) = det(I) = 1',
                        '因为逆矩阵的元素都是原矩阵元素的倒数'],
              explains: ['✗ 不对：det 可以是任何实数，比如 [[2,0],[0,2]] 的 det 是 4。',
                         '✓ 对：这是纯粹的代数推理：单位阵的 det 是 1，所以两个数相乘等于 1，它们互为倒数。',
                         '✗ 不对：以 [[2,0],[0,2]] 为例，它的逆是 [[0.5,0],[0,0.5]]，但一般矩阵的逆并不是逐元素取倒数。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '[[2,0],[0,2]] 的逆是 [[0.5,0],[0,0.5]]，det = 0.25。',
            '面板里的 det 会从 4 跳到 0.25，正好是倒数关系。',
            '📖 配套讲义：2-2 逆矩阵（det 与逆矩阵的存在性）']
    },
    /* ---------- 第 6 章 ---------- */
    {
        id: '6-1', chapter: 6, title: '逆矩阵 = 撤销变换',
        brief: '如果 A 把空间变过去，<strong>A⁻¹ 就把它变回来</strong>：A⁻¹·A = I。' +
               '点击「求逆」看一段可逆矩阵的证据，再亲手制造一个不可逆的。',
        scene: {
            space: '2d', matrix: [[2, 0], [0, 1]], basis: true, tgrid: true, shape: 'area',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true },
            toolbar: [
                { id: 'inv', label: '求 A⁻¹ 并应用', action: 'try-inverse' },
                { id: 'play-inv', label: '▶ 播放 A → A⁻¹', action: 'play-inverse' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'inv', text: '在 A = [[2,0],[0,1]] 上点击「求 A⁻¹ 并应用」，让矩阵变回单位阵',
              check: { type: 'match-matrix', matrix: [[1, 0], [0, 1]], tol: 0.08 } },
            { id: 'sing', text: '现在制造一个不可逆矩阵：把两列拖成共线，让 det = 0',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.08 } },
            { id: 'quiz', text: '辨析：为什么 det = 0 的矩阵没有逆？',
              options: ['因为公式里出现除以 0，所以只是算不出来',
                        '因为 det = 0 时矩阵不再是方阵',
                        '因为多个不同的向量被压到同一个位置，无法确定该还原成谁'],
              explains: ['✗ 不对：不只如此。除以 0 只是表象，根本原因是信息已经丢失。',
                         '✗ 不对：奇异矩阵仍然是方阵，只是它的列线性相关。',
                         '✓ 对：压扁之后信息不可恢复，映射不是一一对应，逆自然不存在。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '[[2,0],[0,1]] 的逆是 [[0.5,0],[0,1]]：x 方向放大 2 倍，撤销就是缩小一半。',
            '把两列拖到同一条直线上（比如 (1,1) 与 (2,2)）就能得到 det = 0。',
            '📖 配套讲义：2-2 逆矩阵（逆矩阵的定义与求法）']
    },
    {
        id: '6-2', chapter: 6, title: '奇异矩阵没有逆',
        brief: 'det = 0 的矩阵把平面压成了一条线——<strong>信息被压没了，无法还原</strong>，' +
               '所以 A⁻¹ 不存在。亲手制造一个奇异矩阵，然后按「试着求 A⁻¹」看会发生什么。',
        scene: {
            space: '2d', matrix: [[1, 1], [1, 1]], basis: true, tgrid: true, shape: 'area', spanView: true,
            vectors: [],
            metric: 'rank',
            interact: { dragColumns: true },
            toolbar: [
                { id: 'try-inv', label: '试着求 A⁻¹', action: 'try-inverse' },
                { id: 'make-sing', label: '造一个奇异矩阵', action: 'preset', matrix: [[1, 2], [2, 4]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'sing', text: '让 det(A) = 0：把两列拖成共线，或用「造一个奇异矩阵」',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.08 } },
            { id: 'tryit', text: '现在点击「试着求 A⁻¹」，注意它算不出来',
              check: { type: 'actions', all: ['try-inverse'] } },
            { id: 'quiz', text: '辨析：奇异矩阵没有逆，最本质的原因是什么？',
              options: ['因为它把不同的向量映到同一个点，所以不存在反过来的映射',
                        '因为它的元素里有很多 0',
                        '因为它的行列式公式里要除以 0'],
              explains: ['✓ 对：映射不是一一对应，就谈不上有逆映射，这是最根本的一条。',
                         '✗ 不对：[[0,1],[1,0]] 里也有 0，但它是可逆的，交换两个轴就能还原。',
                         '✗ 不对：除以 0 只是这个事实在公式上的表现，不是原因。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '[[1,2],[2,4]] 的两列 (1,2) 与 (2,4) 共线，所以 det = 0。',
            '点「试着求 A⁻¹」会弹出提示，说明它不可逆。',
            '📖 配套讲义：2-2 逆矩阵（可逆的充要条件 det ≠ 0）']
    },
    {
        id: '6-3', chapter: 6, title: '用逆矩阵解方程',
        brief: '方程 Av = b 的两边同乘 A⁻¹，就得到 <strong>v = A⁻¹b</strong>。' +
               '先用列图像把 v 拖出来，再回来体会为什么这个式子能一步给出答案。',
        scene: {
            space: '2d', matrix: [[2, 1], [1, 1]], basis: true, tgrid: false,
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: 'v 未知', draggable: true, showTransform: true, transformLabel: 'Av' }],
            targetPoint: { point: [3, 2], label: 'b' },
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'solve', text: '拖动 v，使 Av 命中目标 b = (3, 2)',
              check: { type: 'solve', to: [3, 2], tol: 0.2 } },
            { id: 'vcheck', text: '确认 v 正好落在 (1, 1)：这就是方程的解',
              check: { type: 'vector-at', target: 'v', to: [1, 1], tol: 0.2 } },
            { id: 'quiz', text: '辨析：为什么只有当 A 可逆时，才能用 v = A⁻¹b 求解？',
              options: ['因为不可逆时 b 一定是零向量',
                        '因为 A⁻¹ 不存在时这个式子写不出来；而且此时解要么没有、要么不唯一',
                        '因为不可逆时方程组一定没有解'],
              explains: ['✗ 不对：b 是不是零向量与 A 是否可逆无关。',
                         '✓ 对：A⁻¹ 不存在就没有 A⁻¹b 这个式子；且列空间不满时 b 可能落在外面导致无解。',
                         '✗ 不对：不可逆时方程组也可能有解，只是解不唯一，也就是无穷多解。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '解 [[2,1],[1,1]]·v = (3,2)：由第二行得 v₁ + v₂ = 2，结合第一行可得 v = (1, 1)。',
            '把 v 拖到 (1, 1)，绿色 Av 就会正好落在金色目标点上。',
            '📖 配套讲义：3-1 克拉默法则（克拉默法则：解 = 行列式之比）']
    },
    {
        id: '6-4', chapter: 6, title: '复合的逆：(BA)⁻¹ = A⁻¹B⁻¹',
        brief: '撤销复合变换必须<strong>逆序</strong>：就像先穿袜子再穿鞋，脱的时候必须先脱鞋再脱袜子。' +
               '先依次施加 A（放大）、B（旋转），再按正确顺序把它们撤销掉。',
        scene: {
            space: '2d', matrix: Mat.identity(2), basis: true, tgrid: true, shape: 'square',
            vectors: [],
            interact: {},
            toolbar: [
                { id: 'apply-a', label: '① 施加 A（x 方向 ×2）', action: 'mul-left', matrix: [[2, 0], [0, 1]], log: 'apply-a' },
                { id: 'apply-b', label: '② 施加 B（旋转 90°）', action: 'mul-left', matrix: [[0, -1], [1, 0]], log: 'apply-b' },
                { id: 'undo-b', label: '③ 撤销 B', action: 'mul-left-inv', matrix: [[0, -1], [1, 0]], log: 'undo-b' },
                { id: 'undo-a', label: '④ 撤销 A', action: 'mul-left-inv', matrix: [[2, 0], [0, 1]], log: 'undo-a' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'build', text: '先依次点击 ①②，做出复合变换 B·A',
              check: { type: 'actions', all: ['apply-a', 'apply-b'], ordered: true } },
            { id: 'unwind', text: '再按正确顺序撤销：先点「③ 撤销 B」，再点「④ 撤销 A」',
              check: { type: 'actions', all: ['apply-a', 'apply-b', 'undo-b', 'undo-a'], ordered: true } },
            { id: 'back', text: '确认矩阵已经回到单位阵 I',
              check: { type: 'match-matrix', matrix: [[1, 0], [0, 1]], tol: 0.08 } },
            { id: 'quiz', text: '辨析：撤销复合变换 (BA)⁻¹ 为什么要逆序？',
              options: ['因为逆矩阵的元素需要按相反顺序排列',
                        '其实顺序无所谓，正序撤销也能回到单位阵',
                        '因为矩阵乘法不满足交换律，只有逆序才能正好抵消'],
              explains: ['✗ 不对：逆矩阵的元素没有按顺序排列这回事。',
                         '✗ 不对：正序撤销一般回不到单位阵，因为矩阵乘法不可交换。',
                         '✓ 对：(BA)⁻¹(BA) = A⁻¹B⁻¹BA = A⁻¹A = I，中间靠 B⁻¹B = I 消掉，顺序不能乱。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '先做的变换要后撤销，这就是逆序的含义。',
            '撤销完成后矩阵应当显示为 [[1, 0], [0, 1]]，也就是单位阵。',
            '📖 配套讲义：2-2 逆矩阵（(BA)⁻¹ = A⁻¹B⁻¹）']
    },
    /* ---------- 第 7 章 ---------- */
    {
        id: '7-1', chapter: 7, title: '列图像：把 b 拼出来',
        brief: '方程 Av = b 有两种读法。这里用<strong>列图像</strong>：' +
               '找系数，让 A 的两列组合出 b。金色 v 是未知向量，绿色 Av 是当前结果。',
        scene: {
            space: '2d', matrix: [[1, 2], [1, -1]], basis: true, tgrid: false,
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: 'v 未知', draggable: true, showTransform: true, transformLabel: 'Av' }],
            targetPoint: { point: [4, 1], label: 'b' },
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'solve', text: '拖动 v，使 Av 命中目标 b = (4, 1)',
              check: { type: 'solve', to: [4, 1], tol: 0.2 } },
            { id: 'quiz', text: '辨析：什么样的方程组一定没有解？',
              options: ['b 不在两列的列空间里时（比如两列共线而 b 在直线外）',
                        '系数里出现负数时',
                        '未知数比方程多时'],
              explains: ['✓ 对：有解等价于 b 落在列空间里；b 在列空间外，就是无解。',
                         '✗ 不对：负数只是符号，[[−1,0],[0,−1]] 的方程组照样有解。',
                         '✗ 不对：未知数多只是可能无穷多解，不等于无解。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '解方程 [[1,2],[1,−1]]·v = (4,1) 得 v ≈ (2, 1)，直接拖到 (2, 1) 试试。',
            '盯着绿色 Av 去撞金色目标圆环，Av 会跟着 v 一起动。',
            '📖 配套讲义：3-2 线性方程组（方程组的列图像）']
    },
    {
        id: '7-2', chapter: 7, title: '行图像：两条直线的交点',
        brief: '同一个方程组的另一种读法叫<strong>行图像</strong>：每一行是一条直线，' +
               '<em>解就是两条直线的交点</em>。方程组 x + 2y = 4 与 x − y = 1 的交点是 (2, 1)。',
        scene: {
            space: '2d', matrix: [[1, 2], [1, -1]], basis: false, tgrid: false,
            lines: [
                { a: 1, b: 2, c: 4, color: 'rgba(251,113,133,0.8)' },
                { a: 1, b: -1, c: 1, color: 'rgba(196,181,253,0.8)' }
            ],
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: '解', draggable: true }],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'hit', text: '拖动金色点，让它落在两条直线的交点上',
              check: { type: 'intercept', tol: 0.2 } },
            { id: 'same', text: '确认这个点就是 (2, 1)：它同时满足两个方程',
              check: { type: 'vector-at', target: 'v', to: [2, 1], tol: 0.2 } },
            { id: 'quiz', text: '辨析：行图像与列图像描述的是同一个方程组吗？',
              options: ['不是，行图像看直线，列图像看向量组合，是两个方程组',
                        '是同一个方程组：行图像看「两条线交于一点」，列图像看「两列拼出 b」',
                        '只有方阵两者才相同'],
              explains: ['✗ 不对：两者是同一个 Ax = b，只是看的角度不同。',
                         '✓ 对：交点坐标 (2,1) 就是组合系数 (2,1)，两种读法给出同一个答案。',
                         '✗ 不对：对任意矩阵都成立，与是否方阵无关。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '两条直线分别是 x + 2y = 4 与 x − y = 1，交点在 (2, 1)。',
            '拖到格点附近会自动吸附，把金色点放到两条线的交叉处即可。',
            '📖 配套讲义：3-2 线性方程组（方程组的行图像）']
    },
    {
        id: '7-3', chapter: 7, title: '无解：两条平行线',
        brief: '方程组 x + y = 2 与 x + y = 4 的图像是两条<strong>平行线</strong>，' +
               '没有交点，所以方程组<em>无解</em>。从列图像看：b 不在两列的张成上。',
        scene: {
            space: '2d', matrix: [[1, 1], [1, 1]], basis: false, tgrid: false, spanView: true, nullView: true,
            lines: [
                { a: 1, b: 1, c: 2, color: 'rgba(251,113,133,0.85)' },
                { a: 1, b: 1, c: 4, color: 'rgba(196,181,253,0.85)' }
            ],
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            targetPoint: { point: [4, 4], label: 'b = (4,4)' },
            metric: 'rank',
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'rank', text: '先确认 rank(A) = 1：两列共线，列空间只是那条青色直线',
              check: { type: 'rank', value: 1 } },
            { id: 'try', text: '拖动 v 试着让 Av 命中金色目标 b = (4, 4)',
              check: { type: 'null-space', tol: 1e9 } },
            { id: 'quiz', text: '辨析：为什么这个方程组无解？',
              options: ['因为未知数只有两个',
                        '因为两个方程的系数完全相同',
                        '因为两条直线平行，没有交点；等价地，b 落在列空间之外'],
              explains: ['✗ 不对：两个未知数本身不会导致无解。',
                         '✗ 不对：系数相同只是表现为平行，根因在于 b 不在列空间里。',
                         '✓ 对：两列共线时列空间只是一条直线，b 不在线上就拼不出来，于是无解。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '两条线斜率相同、截距不同，所以平行。',
            '观察绿色 Av：无论怎么拖 v，Av 都只能落在那条青色直线上，够不到目标点。',
            '📖 配套讲义：3-2 线性方程组（无解的判定）']
    },
    {
        id: '7-4', chapter: 7, title: '无穷多解：重合的线',
        brief: '方程组 x = 2 与 2x = 4 其实是<strong>同一个方程</strong>，' +
               '两条线完全重合，线上<em>每个点都是解</em>：无穷多解。' +
               '拖动 v 时请留意 Av——它始终停在同一处，因为多出来的那个方向被 A 压掉了。',
        scene: {
            space: '2d', matrix: [[1, 0], [2, 0]], basis: false, tgrid: false, nullView: true,
            lines: [
                { a: 1, b: 0, c: 2, color: 'rgba(251,113,133,0.85)' },
                { a: 2, b: 0, c: 4, color: 'rgba(196,181,253,0.5)', dash: [6, 5] }
            ],
            vectors: [{ id: 'v', data: [0, 0], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            targetPoint: { point: [2, 4], label: 'b = (2,4)' },
            metric: 'rank',
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'one', text: '把 v 拖到 (2, 0)：Av 应该命中 b = (2, 4)',
              check: { type: 'solve', to: [2, 4], tol: 0.25 } },
            { id: 'two', text: '再换成 (2, 3)：Av 仍然命中同一个 b，说明解不止一个',
              check: { type: 'solve', to: [2, 4], tol: 0.25 } },
            { id: 'quiz', text: '辨析：为什么这个方程组有无穷多解？',
              options: ['因为两个方程是同一个方程，两条线重合',
                        '因为矩阵不是方阵',
                        '因为有解就一定是无穷多解'],
              explains: ['✓ 对：(1,1) 与 (2,2) 共线，第二个方程只是第一个的两倍，约束没有增加。',
                         '✗ 不对：这里是标准的 2×2 方阵。',
                         '✗ 不对：可逆矩阵构成的方程组恰好只有一个解。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '把 v 的第二个分量改成任意数，Av 都不会变——因为 A 的第二列是零列。',
            '紫色直线就是零空间：沿它滑动 v，Av 始终停在同一个点上。',
            '📖 配套讲义：3-2 线性方程组（无穷多解的判定）']
    },
    {
        id: '7-5', chapter: 7, title: '零空间：被压到原点的方向',
        brief: '7-3 的矩阵 A = [[1, 1], [1, 1]] 把整个平面压到了直线 y = x 上。' +
               '那些<strong>恰好被压到原点</strong>的向量（满足 Av = 0）组成 A 的<em>零空间</em>。' +
               '拖动 v 观察绿色 Av，找出被压扁的那个方向。',
        scene: {
            space: '2d', matrix: [[1, 1], [1, 1]], basis: false, tgrid: true, nullView: true,
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            metric: 'rank',
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'find', text: '拖动 v，让绿色的 Av 落到原点上（Av = 0）',
              check: { type: 'null-space', tol: 0.1, dir: [-1, 1] } },
            { id: 'quiz', text: '辨析：零空间里的向量，与矩阵的列是什么关系？',
              options: ['零空间的向量就是矩阵的列',
                        '零空间的方向与矩阵的每一行都垂直，所以被 A 映到 0',
                        '零空间一定是二维的'],
              explains: ['✗ 不对：列向量一般不在零空间里，把列代进去得到的是 A 乘列，通常不是 0。',
                         '✓ 对：A·v 的第 i 个分量就是第 i 行与 v 的点积；行与 v 垂直时点积为 0。',
                         '✗ 不对：这里零空间是一维的一条直线。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '零空间方向是 (1, −1) 或 (−1, 1)：A·(1,−1) = (1·1 + 1·(−1), 1·1 + 1·(−1)) = (0, 0)。',
            '紫色直线就是零空间：v 落在它上面时 Av 会被压到原点。',
            '📖 配套讲义：4-3 方程组解的结构（基础解系与通解结构）']
    },
    /* ---------- 第 8 章 ---------- */
    {
        id: '8-1', chapter: 8, title: '同一根向量，两套坐标',
        brief: '粉色、紫色箭头是一组<strong>新基</strong>（也就是矩阵 B 的两列），' +
               '虚线是它们的坐标格。v 还是那根箭头，但用新基来读，它的坐标不一样了：' +
               'v = c₁·b₁ + c₂·b₂，屏幕上的 (c₁, c₂) 就是 v 的<em>新基坐标</em>。',
        scene: {
            space: '2d', matrix: [[2, 1], [1, 1]], basis: true, tgrid: false, basisCoords: true,
            vectors: [{ id: 'v', data: [3, 2], color: COLORS.v, label: 'v', draggable: true }],
            interact: { clickPlace: true, dragVectors: true, dragColumns: true }
        },
        tasks: [
            { id: 'read', text: '把 v 拖到 (3, 2)，读一读屏幕上的新基坐标 (c₁, c₂)',
              check: { type: 'in-basis', to: [1, 1], tol: 0.2 } },
            { id: 'quiz', text: '辨析：v 的标准坐标是 (3, 2)，新基坐标是 (1, 1)，v 本身变了吗？',
              options: ['只有基是标准基时坐标才等于向量',
                        '变了，坐标不同就说明向量不同',
                        '没变，v 还是同一根箭头，只是换了把尺子去量'],
              explains: ['✗ 不对：标准基只是最方便的一把尺子，换成别的基坐标就换个数。',
                         '✗ 不对：坐标只是描述方式，箭头本身没有动。',
                         '✓ 对：这是基变换最核心的一句话——向量是几何对象，坐标依赖于基。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '本关新基是 b₁ = (2,1)、b₂ = (1,1)。',
            '(3,2) = 1·(2,1) + 1·(1,1)，所以新基坐标是 (1,1)——解方程组就能得到。',
            '📖 配套讲义：4-1 向量组及其线性组合（同一向量的两套坐标）']
    },
    {
        id: '8-2', chapter: 8, title: '坐标翻译器：B 与 B⁻¹',
        brief: '新基坐标 c 翻译成标准坐标：左乘 B（也就是 <strong>B·c</strong>）。' +
               '反过来，标准坐标翻译成新基坐标：左乘 <strong>B⁻¹</strong>。' +
               '矩阵 B 就是两种语言之间的翻译器。',
        scene: {
            space: '2d', matrix: [[2, 0], [0, 1]], basis: true, tgrid: false, basisCoords: true,
            vectors: [{ id: 'v', data: [2, 1], color: COLORS.v, label: 'v', draggable: true }],
            interact: { clickPlace: true, dragVectors: true, dragColumns: true }
        },
        tasks: [
            { id: 'read', text: '把 v 拖到 (2, 1)：它在新基下的坐标应该是 (1, 1)',
              check: { type: 'in-basis', to: [1, 1], tol: 0.2 } },
            { id: 'quiz', text: '辨析：已知新基坐标 c，怎样算出标准坐标？',
              options: ['左乘 B：标准坐标 = B·c',
                        '直接读出 c 的两个数',
                        '左乘 B⁻¹'],
              explains: ['✓ 对：B 的列就是基向量本身，c₁b₁ + c₂b₂ 正是 B·c。',
                         '✗ 不对：只有标准基下两者才恰好相等。',
                         '✗ 不对：B⁻¹ 是反方向的翻译，把标准坐标变回新基坐标。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '本关 B = [[2,0],[0,1]] 是标准基的 x 方向放大 2 倍。',
            '那么 (2,1) 用新基读就是 (1,1)：因为 1·(2,0) + 1·(0,1) = (2,1)。',
            '📖 配套讲义：2-1 矩阵及其运算（过渡矩阵与坐标变换）']
    },
    {
        id: '8-3', chapter: 8, title: '新基下的矩阵：B⁻¹AB',
        brief: '同一个变换 A，用新基的语言怎么写？答案是 <strong>B⁻¹AB</strong>：' +
               '先把新基坐标翻译成标准坐标（乘 B），再施加 A，最后翻译回去（乘 B⁻¹）。' +
               '这个式子叫 A 与 B 的<em>相似</em>。',
        scene: {
            space: '2d', matrix: [[0, -1], [1, 0]], basis: false, tgrid: true,
            vectors: [{ id: 'v', data: [1, 0], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            interact: { dragVectors: true },
            toolbar: [
                { id: 'basis-diag', label: '新基 B = [[2,0],[0,1]]', action: 'preset', matrix: [[0, -1], [1, 0]] },
                { id: 'basis-shear', label: '新基 B = [[1,1],[0,1]]', action: 'preset', matrix: [[0, -1], [1, 0]] }
            ]
        },
        tasks: [
            { id: 'b1', text: '先看 A = 旋转 90°，新基取 B = [[2,0],[0,1]] 时 B⁻¹AB 是什么',
              check: { type: 'in-basis-matrix', basis: [[2, 0], [0, 1]], matrix: [[0, -1], [1, 0]], tol: 0.1 } },
            { id: 'b2', text: '再把新基换成 B = [[1,1],[0,1]]，看 B⁻¹AB 变成了什么',
              check: { type: 'in-basis-matrix', basis: [[1, 1], [0, 1]], matrix: [[1, -2], [1, -1]], tol: 0.12 } },
            { id: 'quiz', text: '辨析：换基之后 A 所代表的变换变了吗？',
              options: ['变了，因为矩阵不一样了',
                        '没变，只是换了描述它的坐标系；相似矩阵描述的是同一个线性变换',
                        '只有当 B 是单位阵时才没变'],
              explains: ['✗ 不对：矩阵的元素变了，但几何上做的还是同一件事。',
                         '✓ 对：相似矩阵是同一个线性变换在不同基下的两套坐标写法。',
                         '✗ 不对：任何可逆的 B 都给出同一个变换的另一种描述。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'B⁻¹AB 的计算顺序：先乘 B，再左乘 A，最后左乘 B⁻¹。',
            '两个 B 得到两个不同的相似矩阵，但它们的迹与行列式完全相同。',
            '📖 配套讲义：5-2 对称矩阵的对角化（相似矩阵 B⁻¹AB）']
    },
    {
        id: '8-4', chapter: 8, title: '好基让问题变简单',
        brief: 'A = [[2, 1], [0, 1]] 在标准基下有点拧巴（带剪切）。' +
               '但换到它两个<strong>特征方向</strong>组成的基 B 下，B⁻¹AB 变成了<em>对角矩阵</em>：' +
               '沿每个基方向独立缩放，互不纠缠。',
        scene: {
            space: '2d', matrix: [[2, 1], [0, 1]], basis: false, tgrid: true,
            vectors: [{ id: 'v', data: [1, 0], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            interact: { dragVectors: true },
            toolbar: [
                { id: 'show-eigen', label: '🔍 显示特征方向', action: 'reveal-eigen' },
                { id: 'to-diag', label: '切到对角形式', action: 'preset', matrix: [[2, 0], [0, 1]] }
            ]
        },
        tasks: [
            { id: 'diag', text: '用特征方向组成的基 B = [[1, 1], [0, -1]]，确认 B⁻¹AB 是对角矩阵',
              check: { type: 'in-basis-matrix', basis: [[1, 1], [0, -1]], matrix: [[2, 0], [0, 1]], tol: 0.12 } },
            { id: 'det', text: '再确认对角化前后行列式不变：det(A) 仍然是 2',
              check: { type: 'det', op: 'eq', value: 2, tol: 0.08 } },
            { id: 'quiz', text: '辨析：对角矩阵为什么「好」？',
              options: ['因为它的行列式一定是 1',
                        '因为它的元素少',
                        '因为两个方向各自独立缩放，互不干扰，计算幂次和求解都变得简单'],
              explains: ['✗ 不对：对角矩阵的 det 是对角线元素之积，可以是任何数。',
                         '✗ 不对：元素个数和普通 2×2 一样是 4 个，好用在结构上。',
                         '✓ 对：方向之间解耦之后，Aⁿ 只需把对角线元素各自取 n 次幂。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '特征方向是 (1, 0) 与 (1, −1)，把它们作为 B 的两列。',
            '对角化 A = PDP⁻¹ 里，D 的对角线就是两个特征值 2 和 1。',
            '📖 配套讲义：5-2 对称矩阵的对角化（相似对角化）']
    },
    /* ---------- 第 9 章 ---------- */
    {
        id: '9-1', chapter: 9, title: '特征向量：不被转向的方向',
        brief: '大多数向量经过 A 都会改变方向，但<strong>特征向量只被拉伸、不被转向</strong>：' +
               'Av = λv。拖动金色 v，找到让 Av 与 v 共线的方向。',
        scene: {
            space: '2d', matrix: [[2, 1], [0, 1]], basis: false, tgrid: true,
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av', lineUp: true }],
            interact: { clickPlace: true, dragVectors: true },
            toolbar: [
                { id: 'reveal', label: '🔍 显示特征方向', action: 'reveal-eigen' }
            ]
        },
        tasks: [
            { id: 'eig', text: '找出一个特征方向（λ = 2 的那个）',
              check: { type: 'collinear', tolDeg: 4 } },
            { id: 'quiz', text: '辨析：如果 Av 与 v 共线且方向相反，λ 是什么？',
              options: ['λ 是负数',
                        'λ = 0',
                        'λ 是正数，只是画反了'],
              explains: ['✓ 对：Av = λv 中 λ < 0 表示向量掉头 180°，长度按 |λ| 缩放。',
                         '✗ 不对：λ = 0 意味着 Av = 0，v 被压到原点，方向都谈不上了。',
                         '✗ 不对：相同方向的共线才是 λ > 0；反向共用一条线但指向相反。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '试试 (1, 0)：A·(1,0) = (2,0)，还在 x 轴上，只是被拉长 2 倍。',
            '另一个特征方向是 (1, −1)：A·(1,−1) = (1,−1)，λ = 1，完全不动。',
            '📖 配套讲义：5-1 特征值与特征向量（特征向量的定义 Av = λv）']
    },
    {
        id: '9-2', chapter: 9, title: '特征值：缩放的倍数',
        brief: '共线时 Av = λv，<strong>λ 就是特征值</strong>：|λ| 是拉伸倍数，' +
               '符号表示是否反向。下面这个矩阵是反射矩阵，找一找它的两个特征方向。',
        scene: {
            space: '2d', matrix: [[0, 1], [1, 0]], basis: false, tgrid: true,
            vectors: [{ id: 'v', data: [1, 0.4], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av', lineUp: true }],
            interact: { clickPlace: true, dragVectors: true },
            toolbar: [
                { id: 'reveal', label: '🔍 显示特征方向', action: 'reveal-eigen' }
            ]
        },
        tasks: [
            { id: 'lam1', text: '找出 λ = 1 的特征方向：v 被 A 完全留在原地',
              check: { type: 'eigen', value: 1, tol: 0.12, tolDeg: 4 } },
            { id: 'lam_minus1', text: '再找出 λ = −1 的方向：Av 与 v 长度相同、方向相反',
              check: { type: 'eigen', value: -1, tol: 0.12, tolDeg: 4 } },
            { id: 'quiz', text: '辨析：λ = −1 与 λ = 1 的几何差别是什么？',
              options: ['没有差别，都是长度不变',
                        'λ = 1 原地不动；λ = −1 长度不变但掉头 180°',
                        'λ = −1 表示向量被压到原点'],
              explains: ['✗ 不对：一个保持方向，一个把方向翻了过来，这正是负号的几何含义。',
                         '✓ 对：|λ| 决定长度倍数，λ 的符号决定是否反向。',
                         '✗ 不对：λ = −1 时长度不变，仍然是一个可逆的变换。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '矩阵 [[0,1],[1,0]] 交换两个坐标，也就是关于直线 y = x 的反射。',
            '(1,1) 在镜面上，完全不动（λ = 1）；(1,−1) 垂直于镜面，被翻成 (−1,1)（λ = −1）。',
            '📖 配套讲义：5-1 特征值与特征向量（特征值的意义）']
    },
    {
        id: '9-3', chapter: 9, title: '对角矩阵的特征值',
        brief: '对角矩阵 [[2, 0], [0, 3]] 的特征向量就是两条坐标轴，' +
               '特征值直接写在对角线上：<strong>λ₁ = 2、λ₂ = 3</strong>。' +
               '它们的乘积正好等于 det = 6。',
        scene: {
            space: '2d', matrix: [[2, 0], [0, 3]], basis: true, tgrid: true, shape: 'square',
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av', lineUp: true }],
            metric: 'det',
            interact: { dragVectors: true, dragColumns: true },
            toolbar: [
                { id: 'reveal', label: '🔍 显示特征方向', action: 'reveal-eigen' }
            ]
        },
        tasks: [
            { id: 'e1', text: '找出 λ = 2 的特征方向（提示：就是 x 轴）',
              check: { type: 'eigen', value: 2, tol: 0.12, tolDeg: 4 } },
            { id: 'e2', text: '再找出 λ = 3 的特征方向（y 轴）',
              check: { type: 'eigen', value: 3, tol: 0.12, tolDeg: 4 } },
            { id: 'prod', text: '确认 det(A) = 6，也就是两个特征值的乘积',
              check: { type: 'det', op: 'eq', value: 6, tol: 0.1 } },
            { id: 'quiz', text: '辨析：det 与特征值之间的一般关系是什么？',
              options: ['det 与特征值没有任何关系',
                        'det 等于特征值之和',
                        'det 等于所有特征值的乘积'],
              explains: ['✗ 不对：两者关系很紧密，det = λ₁λ₂…λₙ，迹 = λ₁+λ₂+…+λₙ。',
                         '✗ 不对：特征值之和等于矩阵的迹（对角线元素之和），不是 det。',
                         '✓ 对：这里 2 × 3 = 6，正好是 det。面积缩放倍数就是各方向缩放倍数之积。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            'x 轴上的向量只被拉长 2 倍，y 轴上的只被拉长 3 倍。',
            '把 v 拖到 (1, 0) 或 (0, 1) 试试，再看 Av 落在哪里。',
            '📖 配套讲义：5-1 特征值与特征向量（对角矩阵的特征值就在对角线上）']
    },
    {
        id: '9-4', chapter: 9, title: '特征方向上的反复变换',
        brief: '回到 A = [[2, 1], [0, 1]]。先把 v 放到特征方向 (1, 0) 上，' +
               '再反复施加 A——<strong>v 始终停留在特征方向上，只是每次被拉长 λ 倍</strong>。',
        scene: {
            space: '2d', matrix: [[2, 1], [0, 1]], basis: false, tgrid: true,
            vectors: [{ id: 'v', data: [1, 0], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av', lineUp: true }],
            interact: { clickPlace: true, dragVectors: true },
            toolbar: [
                { id: 'apply-a', label: '施加一次 A', action: 'mul-left', matrix: [[2, 1], [0, 1]], log: 'apply-a' },
                { id: 'apply-three', label: '连施加三次', action: 'mul-left-3', matrix: [[2, 1], [0, 1]], log: 'apply-three' },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'onaxis', text: '把 v 拖到 x 轴上的 (1, 0)——这里就是 λ = 2 的特征方向',
              check: { type: 'vector-at', target: 'v', to: [1, 0], tol: 0.15 } },
            { id: 'apply', text: '点击「施加一次 A」，观察 Av 仍然躺在 x 轴上',
              check: { type: 'actions', all: ['apply-a'] } },
            { id: 'quiz', text: '辨析：连施加三次 A 之后，矩阵变成了什么？',
              options: ['A³，在特征方向上等价于把 λ 乘三次，即 λ³ = 8',
                        '还是 A 本身',
                        '3·A，也就是每个元素乘 3'],
              explains: ['✓ 对：在特征方向上，反复作用就是反复乘 λ；A³ 在该方向上放大 8 倍。',
                         '✗ 不对：每施加一次都会改变矩阵，A³ 一般不等于 A。',
                         '✗ 不对：矩阵乘法不是数乘，A³ 不等于 3A。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            'x 轴上的向量 (t, 0) 被 A 映到 (2t, 0)，还是 x 轴上的向量。',
            '这正是「特征方向」的实用价值：反复作用不会跑偏，只按 λ 倍增长。',
            '📖 配套讲义：5-1 特征值与特征向量（Aⁿ 与特征值）']
    },
    {
        id: '9-5', chapter: 9, title: '特征基：把 A 变成对角矩阵',
        brief: '把两个特征方向 (1, 0)、(1, −1) 拼成矩阵 P 的两列，计算 <strong>P⁻¹AP</strong>：' +
               '换到特征基下，A = [[2, 1], [0, 1]] 变成了<em>对角矩阵</em>，' +
               '对角线上正好是特征值 2 和 1。这就是对角化 A = PDP⁻¹。',
        scene: {
            space: '2d', matrix: [[2, 1], [0, 1]], basis: false, tgrid: true,
            vectors: [],
            interact: {},
            toolbar: [
                { id: 'to-diag', label: '切到对角形式 D', action: 'preset', matrix: [[2, 0], [0, 1]] },
                { id: 'back', label: '回到原矩阵 A', action: 'preset', matrix: [[2, 1], [0, 1]] },
                { id: 'reveal', label: '🔍 显示特征方向', action: 'reveal-eigen' }
            ]
        },
        tasks: [
            { id: 'diag', text: '用特征基 P = [[1, 1], [0, -1]]，确认 P⁻¹AP 是对角矩阵 diag(2, 1)',
              check: { type: 'in-basis-matrix', basis: [[1, 1], [0, -1]], matrix: [[2, 0], [0, 1]], tol: 0.12 } },
            { id: 'trace', text: '再确认迹不变：对角形式与原矩阵的对角线之和都是 3',
              check: { type: 'match-matrix', matrix: [[2, 1], [0, 1]], tol: 0.06 } },
            { id: 'quiz', text: '辨析：为什么对角化要求特征向量足够多？',
              options: ['因为对角矩阵的元素必须都是正数',
                        '因为要凑够 n 个线性无关的特征向量才能拼成可逆的 P',
                        '因为特征值必须是整数'],
              explains: ['✗ 不对：对角矩阵的元素可以是负数或 0。',
                         '✓ 对：P 的两列必须线性无关（P 可逆），否则 P⁻¹ 不存在，对角化就无从谈起。',
                         '✗ 不对：特征值可以是任意实数，甚至复数。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'P 的两列就是两个特征方向：(1,0) 与 (1,−1)。',
            '对角化之后 D 的对角线是特征值，而 A = PDP⁻¹；两者的迹与行列式都相同。',
            '📖 配套讲义：5-2 对称矩阵的对角化（A = PDP⁻¹ 对角化）']
    },
    /* ---------- 第 10 章 ---------- */
    {
        id: '10-1', chapter: 10, title: '三维空间与 3×3 矩阵',
        brief: '三维中 3×3 矩阵的三列分别是 î、ĵ、k̂ 的落点。' +
               '<strong>单位立方体被变换成平行六面体，体积缩放倍数 = det(A)</strong>。' +
               '在空白处拖动可以旋转视角。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 2]], basis: true, tgrid: false, shape: 'cube',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true, orbit: true }
        },
        tasks: [
            { id: 'vol2', text: '把 det(A) 调成 2（提示：只动对角线上的第三个元素）',
              check: { type: 'det', op: 'eq', value: 2, tol: 0.2 } },
            { id: 'flat', text: '再让三列共面，把 det 压成 0：立方体被拍成一个平面',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.12 } },
            { id: 'quiz', text: '辨析：三维矩阵 det = 0 时，空间被压成了什么？',
              options: ['一定被压成一个点',
                        '空间没有变化，只是体积记为零',
                        '被压成一个平面或一条线'],
              explains: ['✗ 不对：压成一个点需要三列全为零向量，那是最极端的情况。',
                         '✗ 不对：体积为零意味着维度真的丢了，平行六面体是扁的。',
                         '✓ 对：秩可能是 2（压成平面）或 1（压成直线），两种情况体积都是 0。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '拖动空白处旋转视角，滚轮缩放。三维里的列向量手柄是三个小球。',
            'det = 0 的最快做法：把某一列拖成另外两列的倍数。',
            '📖 配套讲义：1-3 行列式的定义（三阶行列式与 3×3 矩阵）']
    },
    {
        id: '10-2', chapter: 10, title: '三维行列式 = 体积缩放',
        brief: '单位立方体（蓝色）被 3×3 矩阵变成平行六面体（绿色），' +
               '<strong>体积缩放倍数就是 det(A)</strong>。拖动三个列的端点，' +
               '让体积变成 2 倍——注意此时三个列向量必须线性无关。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], basis: true, tgrid: false, shape: 'cube',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true, orbit: true }
        },
        tasks: [
            { id: 'two', text: '拖动三个端点，让 det(A) = 2（比如把第三列拖到 2 倍长）',
              check: { type: 'det', op: 'eq', value: 2, tol: 0.2 } },
            { id: 'neg', text: '再把某一列拖到反方向，让 det(A) 变成负数',
              check: { type: 'det', op: 'lt', value: -0.2 } },
            { id: 'quiz', text: '辨析：三维里 det 为负，几何上发生了什么？',
              options: ['空间被翻转了：三个列向量的左右手关系从右手系变成左手系',
                        '立方体被压扁了',
                        '体积变成了负的，这没有几何意义'],
              explains: ['✓ 对：det 的符号表示定向是否被翻转，这与二维里负 det 表示翻面是同一件事。',
                         '✗ 不对：被压扁对应的是 det = 0，而不是负值。',
                         '✗ 不对：体积本身总是正的，负号携带的是「朝向」信息。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '默认矩阵是单位阵，det = 1。把第三列 (0,0,1) 拖到 (0,0,2) 就得到 det = 2。',
            '拖动空白处可以旋转视角，从不同角度确认绿色平行六面体的大小。',
            '📖 配套讲义：1-1 二三阶行列式（三阶行列式的几何意义 = 体积）']
    },
    {
        id: '10-3', chapter: 10, title: '三维旋转：绕 z 轴转 90°',
        brief: '绕 z 轴旋转时，k̂ 不动，î 与 ĵ 在 xy 平面内转 90°。' +
               '所以矩阵第 3 列是 (0, 0, 1)，前两列和二维旋转一样：' +
               '<strong>[[0, −1, 0], [1, 0, 0], [0, 0, 1]]</strong>。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], basis: true, tgrid: false, shape: 'cube',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true, orbit: true },
            toolbar: [
                { id: 'rot-z90', label: '绕 z 轴转 90°', action: 'preset', matrix: [[0, -1, 0], [1, 0, 0], [0, 0, 1]] },
                { id: 'rot-x90', label: '绕 x 轴转 90°', action: 'preset', matrix: [[1, 0, 0], [0, 0, -1], [0, 1, 0]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'col1', text: '把粉色 Aî 拖到 (0, 1, 0)',
              check: { type: 'matrix-col-at', col: 0, to: [0, 1, 0], tol: 0.2 } },
            { id: 'col2', text: '把紫色 Aĵ 拖到 (−1, 0, 0)',
              check: { type: 'matrix-col-at', col: 1, to: [-1, 0, 0], tol: 0.2 } },
            { id: 'kfix', text: '确认蓝色 Ak̂ 仍在 (0, 0, 1)：旋转轴上的向量不动',
              check: { type: 'matrix-col-at', col: 2, to: [0, 0, 1], tol: 0.1 } },
            { id: 'quiz', text: '辨析：为什么绕 z 轴旋转时 k̂ 不动？',
              options: ['因为旋转矩阵的第三列总是 (0,0,1)',
                        '因为 k̂ 恰好是这次旋转的转轴方向，转轴上的向量都不动',
                        '因为 k̂ 的长度是 1，所以不会变'],
              explains: ['✗ 不对：只有绕 z 轴的旋转第三列才是 (0,0,1)；绕 x 轴时不动的是第一列。',
                         '✓ 对：绕某轴旋转时，该轴上的向量是特征向量，特征值为 1。',
                         '✗ 不对：长度为 1 的向量照样会被别的旋转改变方向。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            '绕 z 轴就是把 xy 平面当作二维来旋转，z 坐标原样保留。',
            '也可以直接点「绕 z 轴转 90°」预设，再自己拖动验证一遍。',
            '📖 配套讲义：6-2 正交变换及配方法化标准形（三维正交变换）']
    },
    {
        id: '10-4', chapter: 10, title: '三维 det = 0：压成一个平面',
        brief: '当三个列向量<strong>共面</strong>时，平行六面体被压扁，体积变成 0——' +
               '三维空间塌缩成一个平面（甚至一条线），矩阵奇异。亲手把这个立方体压扁。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], basis: true, tgrid: false, shape: 'cube',
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true, orbit: true }
        },
        tasks: [
            { id: 'flat', text: '让三列共面，把 det(A) 压成 0（最快：把第三列拖成前两列的倍数）',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.12 } },
            { id: 'rank', text: '确认此时 rank(A) = 2：空间被压成一个平面',
              check: { type: 'rank', value: 2 } },
            { id: 'line', text: '继续压：把三列拖成全部共线，让 rank(A) 掉到 1',
              check: { type: 'rank', value: 1 } },
            { id: 'quiz', text: '辨析：三维矩阵 rank = 2 意味着什么？',
              options: ['矩阵把空间压成了一个点',
                        '矩阵有两行非零',
                        '三个列向量落在同一个平面上，整个三维空间被压成那张平面'],
              explains: ['✗ 不对：压成一个点需要秩为 0，也就是零矩阵。',
                         '✗ 不对：行数与秩不是一回事，这里的矩阵仍然是 3×3。',
                         '✓ 对：三个列向量只贡献了两个独立方向，张成的是过原点的一个平面。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '最省事的做法：把第三列 (0,0,1) 拖到 (1,1,0)，它就成了前两列之和，三列共面。',
            '再让前两列也共线（比如第二列拖到 (2,0,0)），秩就掉到 1。',
            '📖 配套讲义：1-6 行列式的计算（三阶 det = 0 与秩）']
    },
    /* ---------- 第 11 章 ---------- */
    {
        id: '11-1', chapter: 11, title: '点积：分量相乘再相加',
        brief: '两个向量的<strong>点积是一个数</strong>：u·v = uₓvₓ + u_yv_y。' +
               '它不是向量、也不是矩阵，就是一个实数。' +
               '拖动紫色 v，观察屏幕上 u·v 的读数怎么变。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false, dotPair: { a: 'u', b: 'v', proj: false },
            vectors: [
                { id: 'u', data: [2, 1], color: COLORS.ai, label: 'u', draggable: false },
                { id: 'v', data: [1, 2], color: COLORS.aj, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'calc', text: '把 v 拖到 (1, 2)：此时 u·v 应该等于 2×1 + 1×2 = 4',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 4, tol: 0.3 } },
            { id: 'zero', text: '再把 v 拖到让 u·v = 0 的位置（提示：与 u 垂直）',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 0, tol: 0.2 } },
            { id: 'quiz', text: '辨析：u·v 的结果是什么类型？',
              options: ['一个数（标量），没有方向',
                        '一个 2×2 矩阵',
                        '一个向量，方向由 u 和 v 共同决定'],
              explains: ['✓ 对：两个向量的点积是标量，这也是它和叉积（结果是向量）最大的区别。',
                         '✗ 不对：矩阵是变换，点积只是把两个向量压缩成一个数。',
                         '✗ 不对：点积的结果是一个实数，不带方向。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            'u = (2, 1) 固定，v = (v₁, v₂) 时 u·v = 2v₁ + v₂。',
            '要让 2v₁ + v₂ = 0，比如 v = (1, −2)。',
            '📖 配套讲义：4-1 向量组及其线性组合（向量的内积运算）']
    },
    {
        id: '11-2', chapter: 11, title: '几何意义：投影的长度',
        brief: 'u·v 的几何含义：<strong>v 在 u 方向上的投影长度 × |u|</strong>。' +
               '图中绿色箭头就是 v 在 u 上的投影，虚线是垂线。' +
               '把 v 沿着垂直于 u 的方向移动，投影不变、点积也不变。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false, dotPair: { a: 'u', b: 'v', proj: true },
            vectors: [
                { id: 'u', data: [3, 0], color: COLORS.ai, label: 'u', draggable: false },
                { id: 'v', data: [1, 2], color: COLORS.aj, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'same', text: '把 v 拖到 (1, 3)：投影长度不变，点积仍然是 3',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 3, tol: 0.3 } },
            { id: 'dbl', text: '再把投影拉长到 2 倍：让点积变成 6',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 6, tol: 0.3 } },
            { id: 'quiz', text: '辨析：把 v 沿着垂直于 u 的方向平移，为什么点积不变？',
              options: ['因为 v 的长度没变',
                        '因为投影长度没变，而 u·v = 投影长度 × |u|',
                        '因为点积只和夹角有关'],
              explains: ['✗ 不对：(1,2) 与 (1,3) 长度并不相等，但点积相同。',
                         '✓ 对：垂直于 u 的位移对投影没有贡献，乘出来的那个数自然不变。',
                         '✗ 不对：夹角确实变了，但投影长度与 |u| 都没变，所以点积不变。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'u = (3, 0) 时，u·v = 3v₁，只看 v 的第一个分量。',
            '所以 (1, 2)、(1, 3)、(1, 100) 的点积都是 3——投影长度都是 1。',
            '📖 配套讲义：4-1 向量组及其线性组合（内积的几何意义：投影）']
    },
    {
        id: '11-3', chapter: 11, title: '点积的符号：锐角、直角、钝角',
        brief: '点积的<strong>符号</strong>透露夹角：u·v 大于 0 是锐角，等于 0 是垂直，小于 0 是钝角。' +
               '因为 u·v = |u||v|cosθ，符号完全由 cosθ 决定。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false, dotPair: { a: 'u', b: 'v', proj: true },
            vectors: [
                { id: 'u', data: [2, 0], color: COLORS.ai, label: 'u', draggable: false },
                { id: 'v', data: [1, 1], color: COLORS.aj, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'acute', text: '先把 v 拖到与 u 成锐角的位置，让点积大于 0',
              check: { type: 'dot', a: 'u', b: 'v', op: 'gt', value: 1.0 } },
            { id: 'right', text: '再拖到与 u 垂直的位置，让点积等于 0',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 0, tol: 0.2 } },
            { id: 'obtuse', text: '最后拖到钝角位置，让点积小于 0',
              check: { type: 'dot', a: 'u', b: 'v', op: 'lt', value: -1.0 } },
            { id: 'quiz', text: '辨析：两个非零向量的点积为 0，说明了什么？',
              options: ['两者的长度相等',
                        '至少有一个向量是零向量',
                        '两者垂直：cos 90° = 0，所以点积为 0'],
              explains: ['✗ 不对：长度相等与点积是否为 0 没有直接关系。',
                         '✗ 不对：题目已经说明是非零向量，零向量才会让点积恒为 0。',
                         '✓ 对：垂直是点积为 0 的充要条件（在非零前提下），这也是「正交」的定义。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            'u = (2, 0) 时，u·v = 2v₁，所以符号只取决于 v 的第一个分量。',
            'v₁ = 0（也就是 v 落在 y 轴上）时点积为 0。',
            '📖 配套讲义：4-1 向量组及其线性组合（内积的符号与夹角）']
    },
    {
        id: '11-4', chapter: 11, title: '对偶性：点积是一个 1×2 矩阵',
        brief: '固定 u = (2, 1)，映射 <strong>v ↦ u·v</strong> 把平面上的向量变成一个数——' +
               '它是一个从 2D 到 1D 的<em>线性变换</em>，矩阵是 1×2 的 [2 1]，' +
               '正好是 u 躺下来（也就是转置 uᵀ）。下图把这件事画了出来。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false,
            numLine: { range: [-8, 8], title: '数轴（1 维输出）' },
            oneDim: { basis: [1, 0], proj: true },
            dotPair: { a: 'u', b: 'v', proj: false },
            vectors: [
                { id: 'u', data: [2, 1], color: COLORS.ai, label: 'u', draggable: false },
                { id: 'v', data: [1, 2], color: COLORS.aj, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'hit4', text: '把 v 拖到让 u·v = 4 的位置',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: 4, tol: 0.3 } },
            { id: 'hitneg', text: '再拖到让 u·v = −4 的位置',
              check: { type: 'dot', a: 'u', b: 'v', op: 'eq', value: -4, tol: 0.3 } },
            { id: 'quiz', text: '辨析：为什么说「点积是一个 1×2 矩阵」？',
              options: ['因为固定 u 之后，v ↦ u·v 是线性映射，写成矩阵就是 1×2 的 uᵀ',
                        '因为点积的结果可能是负数',
                        '因为点积要用到两个向量'],
              explains: ['✓ 对：这个映射满足线性性，矩阵形式就是把它写成一行——这正是对偶性的内容。',
                         '✗ 不对：结果的正负与它是不是线性映射无关。',
                         '✗ 不对：用到两个向量只是输入，关键在于「固定一个之后剩下的那个映射是不是线性的」。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            'u = (2, 1)，所以 u·v = 2v₁ + v₂。',
            '下方数轴上的圆点就是 u·v 的当前取值，拖 v 时它会跟着滑动。',
            '📖 配套讲义：2-1 矩阵及其运算（1×2 矩阵与线性函数）']
    },
    {
        id: '11-5', chapter: 11, title: '转置：把行躺成列',
        brief: '<strong>转置</strong> Aᵀ 把 A 的第 1 行写成第 1 列、第 2 行写成第 2 列：' +
               'A = [[2, 1], [0, 3]] 的转置是 Aᵀ = [[2, 0], [1, 3]]。' +
               '11-4 里「向量躺下来变成 1×2 矩阵」，就是向量版本的转置。',
        scene: {
            space: '2d', matrix: [[2, 1], [0, 3]], basis: true, tgrid: true,
            vectors: [],
            interact: { dragColumns: true },
            toolbar: [
                { id: 'transpose', label: '把它转置', action: 'preset', matrix: [[2, 0], [1, 3]], log: 'transpose' },
                { id: 'back', label: '↺ 转回原矩阵', action: 'preset', matrix: [[2, 1], [0, 3]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'do', text: '点击「把它转置」，把 A 变成 Aᵀ = [[2, 0], [1, 3]]',
              check: { type: 'match-matrix', matrix: [[2, 0], [1, 3]], tol: 0.06 } },
            { id: 'det', text: '确认转置不改变行列式：det(Aᵀ) 仍然是 6',
              check: { type: 'det', op: 'eq', value: 6, tol: 0.1 } },
            { id: 'quiz', text: '辨析：转置和「求逆」是什么关系？',
              options: ['转置就是求逆，两者一样',
                        '是两种不同的操作：转置只换行列位置，不需要矩阵可逆；逆矩阵则要求 det 不为 0',
                        '转置等价于把每个元素取倒数'],
              explains: ['✗ 不对：[[0,1],[1,0]] 是自转置的，但它的逆也是它自己——这只是巧合，不是一般规律。',
                         '✓ 对：转置对任意矩阵都有定义，求逆只对方阵且 det 不为 0 才有。',
                         '✗ 不对：转置是换位置，与取倒数无关。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'A = [[2,1],[0,3]]，把第 1 行 (2,1) 写成第 1 列，第 2 行 (0,3) 写成第 2 列。',
            '转置后 det 不变：主对角线元素仍是 2 与 3，副对角线仍是 0 与 1。',
            '📖 配套讲义：1-4 行列式的性质（转置与行列式性质 1）']
    },
    {
        id: '11-6', chapter: 11, title: '点积与角度：余弦相似度',
        brief: 'u·v = |u||v|cosθ。当两个向量都是<strong>单位向量</strong>时，' +
               '点积就是 cosθ 本身——夹角越小，点积越大。' +
               '下面 u = (1, 0) 固定，请把 v 调成与它夹角 60° 的单位向量。',
        scene: {
            space: '2d', matrix: null, basis: false, tgrid: false,
            dotPair: { a: 'u', b: 'v', proj: true, showCos: true },
            vectors: [
                { id: 'u', data: [1, 0], color: COLORS.ai, label: 'u', draggable: false },
                { id: 'v', data: [1, 1], color: COLORS.aj, label: 'v', draggable: true }
            ],
            interact: { clickPlace: true, dragVectors: true }
        },
        tasks: [
            { id: 'unit', text: '先把 v 调成单位向量（长度 1）',
              check: { type: 'vector-angle', a: 'u', b: 'v', value: 45, tol: 5, unit: true, unitTol: 0.06 } },
            { id: 'sixty', text: '再让 v 与 u 的夹角正好是 60°（此时 cosθ = 0.5）',
              check: { type: 'vector-angle', a: 'u', b: 'v', value: 60, tol: 4, unit: true, unitTol: 0.08 } },
            { id: 'quiz', text: '辨析：什么情况下点积就等于 cosθ？',
              options: ['只有当两个向量相等时',
                        '任何时候都等于 cosθ',
                        '当两个向量都是单位向量时，因为 |u||v| = 1'],
              explains: ['✗ 不对：两个相同的单位向量点积是 1，对应 cosθ = 1，只是其中一种情形。',
                         '✗ 不对：一般情形下 u·v = |u||v|cosθ，还差一个长度因子。',
                         '✓ 对：把长度归一化之后，点积就只剩下夹角信息，这就是余弦相似度的来源。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '60° 的单位向量是 (0.5, √3/2) ≈ (0.5, 0.866)。',
            'u = (1,0) 时 u·v 正好等于 v 的第一个分量，所以点积 0.5 就对应 60°。',
            '📖 配套讲义：6-2 正交变换及配方法化标准形（正交与余弦）']
    },
    /* ---------- 第 12 章 ---------- */
    {
        id: '12-1', chapter: 12, title: '二维叉积 = 有向面积',
        brief: '二维里两个向量的<strong>叉积是一个数</strong>：u×w = uₓw_y − u_ywₓ，' +
               '正好等于 det([u w])——平行四边形的<em>有向</em>面积。' +
               '拖动两列，重温第 5 章的面积，这次注意它的符号。',
        scene: {
            space: '2d', matrix: [[2, 0], [0, 1]], basis: true, tgrid: true,
            cross: { colA: 0, colB: 1, label: 'a×b' },
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true }
        },
        tasks: [
            { id: 'pos', text: '先让有向面积为正（比如保持 [[2,0],[0,1]]，a×b = 2）',
              check: { type: 'det', op: 'gt', value: 1 } },
            { id: 'neg', text: '再把有向面积变成负数：交换两根列的前后顺序感',
              check: { type: 'det', op: 'lt', value: -0.2 } },
            { id: 'quiz', text: '辨析：二维叉积与行列式是什么关系？',
              options: ['u×w 就是矩阵 [u w] 的行列式，所以面积相同、符号规则也相同',
                        '叉积是行列式的绝对值',
                        '两者没有关系，只是数值巧合'],
              explains: ['✓ 对：把 u、w 分别当作两列组成矩阵，它的行列式就是 u×w。',
                         '✗ 不对：叉积保留符号（有向面积），绝对值才是无向面积。',
                         '✗ 不对：两者是同一个量的两种说法，uₓw_y − u_ywₓ 与 2×2 行列式公式完全一致。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '把第 1 列拖到第二列的下方一侧，行列式就会变成负数。',
            '屏幕上蓝色平行四边形就是 a、b 张成的图形，左上角显示有向面积。',
            '📖 配套讲义：1-1 二三阶行列式（二阶 det 就是有向面积）']
    },
    {
        id: '12-2', chapter: 12, title: '三维叉积：垂直于两者的向量',
        brief: '三维中 a×b 是一个<strong>向量</strong>：它同时垂直于 a 和 b，' +
               '方向由<em>右手定则</em>给出（四指从 a 卷向 b，拇指就是方向）。' +
               '让 a = (1, 0, 0)、b = (0, 1, 0)，绿色箭头就是实时算出的 a×b。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], basis: true, tgrid: false,
            cross: { colA: 0, colB: 1, label: 'a×b' },
            vectors: [],
            interact: { dragColumns: true, orbit: true },
            toolbar: [
                { id: 'preset-xy', label: 'a = î, b = ĵ', action: 'preset', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] },
                { id: 'preset-yz', label: 'a = ĵ, b = k̂', action: 'preset', matrix: [[0, 0, 0], [1, 0, 0], [0, 1, 1]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'perp', text: '让 a = î、b = ĵ：确认 a×b 的长度是 1',
              check: { type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 1, tol: 0.1 } },
            { id: 'dir', text: '确认 a×b 的方向就是 k̂ = (0, 0, 1)',
              check: { type: 'cross-dir', colA: 0, colB: 1, dir: [0, 0, 1] } },
            { id: 'quiz', text: '辨析：为什么三维叉积的结果是向量，而不是数？',
              options: ['因为三维空间比二维多一个方向',
                        '因为要同时垂直于 a 和 b 的方向在三维里恰好唯一确定，所以能给出一个向量',
                        '因为三维的叉积公式更长'],
              explains: ['✗ 不对：多一个维度只是前提，关键在于「垂直于两者的方向唯一」。',
                         '✓ 对：在三维里与 a、b 都垂直的方向只有一个（差一个符号），所以结果可以是一个向量。',
                         '✗ 不对：公式长短是结果不是原因。'],
              check: { type: 'choice', correct: 1 } }
        ],
        hints: [
            'î × ĵ = k̂，这是右手定则最基础的一条。',
            '拖动空白处旋转视角，确认绿色箭头确实垂直于粉色与紫色两根。',
            '📖 配套讲义：1-3 行列式的定义（三维叉积与三阶行列式）']
    },
    {
        id: '12-3', chapter: 12, title: '叉积的长度 = 平行四边形面积',
        brief: '<strong>|a×b| = |a||b|sinθ</strong>，正好是 a、b 张成的平行四边形面积。' +
               '拖动矩阵的前两列（粉色、紫色箭头），绿色叉积向量的长度会实时变化。' +
               '注意它和点积的对照：点积用 cos，叉积用 sin。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], basis: true, tgrid: false,
            cross: { colA: 0, colB: 1, label: 'a×b' },
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true, orbit: true },
            toolbar: [
                { id: 'preset-xy', label: 'a = î, b = ĵ（面积 1）', action: 'preset', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] },
                { id: 'preset-2x', label: '把 a 拉长到 2 倍（面积 2）', action: 'preset', matrix: [[2, 0, 0], [0, 1, 0], [0, 0, 1]] },
                { id: 'reset', label: '↺ 回到 I', action: 'identity' }
            ]
        },
        tasks: [
            { id: 'one', text: '先确认 a = î、b = ĵ 时 |a×b| = 1',
              check: { type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 1, tol: 0.1 } },
            { id: 'two', text: '再把 a 拉长到 2 倍，让 |a×b| 变成 2',
              check: { type: 'cross-mag', colA: 0, colB: 1, op: 'eq', value: 2, tol: 0.15 } },
            { id: 'quiz', text: '辨析：固定 |a| 与 |b|，|a×b| 什么时候最大？',
              options: ['夹角为 180° 时最大',
                        '夹角为 0° 时最大',
                        '夹角为 90° 时最大，此时 sinθ = 1，面积为 |a||b|'],
              explains: ['✗ 不对：夹角 180° 时也共线，面积同样是 0。',
                         '✗ 不对：夹角 0° 时 sinθ = 0，两个向量共线，面积为零。',
                         '✓ 对：sin 在 90° 取最大值 1，此时平行四边形是矩形，面积最大。'],
              check: { type: 'choice', correct: 2 } }
        ],
        hints: [
            '把第二列拖到与第一列成 90°，面积最大；拖成共线时面积归零。',
            '屏幕上的绿色箭头长度就是 |a×b|，右上角有实时数值。',
            '📖 配套讲义：1-3 行列式的定义（叉积长度 = 平行四边形面积）']
    },
    {
        id: '12-4', chapter: 12, title: '叉积与行列式：对偶的回归',
        brief: '把 a×b 与第三个向量 c 点积：<strong>(a×b)·c = det([a b c])</strong>——' +
               '平行六面体的有向体积。「与 c 点积」这个线性函数，其对偶向量正是 a×b，' +
               '第 11 章的对偶性在三维里又回来了。',
        scene: {
            space: '3d', matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]], basis: true, tgrid: false, shape: 'cube',
            cross: { colA: 0, colB: 1, label: 'a×b' },
            vectors: [],
            metric: 'det',
            interact: { dragColumns: true, orbit: true }
        },
        tasks: [
            { id: 'unit', text: '先在单位阵上看：det = 1，也就是 (a×b)·c = 1',
              check: { type: 'det', op: 'eq', value: 1, tol: 0.06 } },
            { id: 'vol', text: '把第三列拉长到 2 倍，让体积变成 2',
              check: { type: 'det', op: 'eq', value: 2, tol: 0.15 } },
            { id: 'flat', text: '再让三列共面，让体积变成 0',
              check: { type: 'det', op: 'eq', value: 0, tol: 0.12 } },
            { id: 'quiz', text: '辨析：为什么 (a×b)·c 等于平行六面体的体积？',
              options: ['因为 |a×b| 是底面积，再乘 c 在 a×b 方向上的投影高度就是体积',
                        '因为三个向量的长度相乘就是体积',
                        '因为这是定义，没有几何解释'],
              explains: ['✓ 对：底面积 × 高 = 体积，而点积正是把 c 投影到 a×b 方向上再乘模长。',
                         '✗ 不对：直接把三个长度相乘忽略了它们之间的夹角，只在两两垂直时才成立。',
                         '✗ 不对：它有非常清楚的几何解释，也正是叉积被称为「面积向量」的原因。'],
              check: { type: 'choice', correct: 0 } }
        ],
        hints: [
            '默认单位阵的 det = 1，绿色平行六面体正好是单位立方体。',
            '让某一列拖成另外两列的组合，三列就共面了，体积归零。',
            '📖 配套讲义：1-1 二三阶行列式（混合积 = 三阶行列式 = 体积）']
    },
    /* ---------- 第 99 章 · 自由沙盒 ---------- */
    {
        id: '99-1', chapter: 99, title: '自由沙盒',
        brief: '没有任务。拖动列向量、拖动视角、放几个向量试试。' +
               '右侧面板实时给出 det、秩与特征值。',
        scene: {
            space: '2d', matrix: [[1, 0.5], [0.5, 1]], basis: true, tgrid: true, shape: 'square',
            vectors: [{ id: 'v', data: [1, 1], color: COLORS.v, label: 'v', draggable: true, showTransform: true, transformLabel: 'Av' }],
            metric: 'det',
            interact: { clickPlace: true, dragVectors: true, dragColumns: true },
            toolbar: [
                { id: 'reset', label: '↺ 回到 I', action: 'identity' },
                { id: 'play', label: '▶ 播放变换', action: 'play-transform' },
                { id: 'to3d', label: '切到三维', action: 'toggle-space' },
                { id: 'eigen', label: '🔍 显示特征方向', action: 'reveal-eigen' }
            ]
        },
        tasks: [],
        hints: [
            '随便玩。想看三维就把矩阵升成 3×3，点「切到三维」。',
            '📖 配套讲义：4-1 向量组及其线性组合（自由探索：向量与矩阵）']
    },
];




