<template>
	<view class="page-snake">
		<!-- 得分和最高分显示 -->
		<view class="game-header">
			<text class="score-label">得分</text>
			<text class="score-value">{{ score }}</text>
			<text class="best-label">最高分</text>
			<text class="best-value">{{ bestScore }}</text>
		</view>

		<!-- 游戏画布，支持触摸滑屏操作 -->
		<view class="game-board" @touchstart="onTouchStart" @touchend="onTouchEnd">
			<canvas canvas-id="snakeCanvas" class="snake-canvas"></canvas>
			<!-- 未开始/游戏结束时的遮罩层 -->
			<view class="overlay" v-if="gameState !== 'playing'">
				<text class="overlay-title">{{ overlayTitle }}</text>
				<text class="overlay-desc">{{ overlayDesc }}</text>
				<u-button type="primary" shape="circle" @click="startGame">{{ overlayBtn }}</u-button>
			</view>
		</view>

		<view class="control-hint">
			<text>滑动屏幕或按方向键控制方向</text>
		</view>
	</view>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { onShow, onHide } from '@dcloudio/uni-app';

const GRID_SIZE = 15;
const CELL_SIZE = 20;
const MOVE_INTERVAL = 200;

type Point = { x: number; y: number };

const score = ref(0);
const bestScore = ref(0);
const gameState = ref<'idle' | 'playing' | 'over'>('idle');

let snake: Point[] = [];
let food: Point = { x: 0, y: 0 };
let dir = { x: 1, y: 0 };
let nextDir = { x: 1, y: 0 };
let timer: ReturnType<typeof setInterval> | null = null;
let tx = 0, ty = 0;

// 从本地存储读取最高分
function loadBest() {
	try {
		const d = uni.getStorageSync('rzz_snake_best');
		if (d) bestScore.value = parseInt(d) || 0;
	} catch {}
}
// 保存最高分到本地存储
function saveBest() {
	uni.setStorageSync('rzz_snake_best', String(bestScore.value));
}

const overlayTitle = ref('');
const overlayDesc = ref('');
const overlayBtn = ref('');

// 开始新游戏：初始化蛇的位置、方向，生成食物，启动定时器
function startGame() {
	gameState.value = 'playing';
	score.value = 0;
	snake = [{ x: 7, y: 7 }, { x: 6, y: 7 }, { x: 5, y: 7 }];
	dir = { x: 1, y: 0 };
	nextDir = { x: 1, y: 0 };
	spawnFood();
	draw();
	stopTimer();
	timer = setInterval(tick, MOVE_INTERVAL);
}

// 随机生成食物（避开蛇身）
function spawnFood() {
	for (let i = 0; i < 200; i++) {
		const fx = Math.floor(Math.random() * GRID_SIZE);
		const fy = Math.floor(Math.random() * GRID_SIZE);
		if (!snake.some(s => s.x === fx && s.y === fy)) {
			food = { x: fx, y: fy }; return;
		}
	}
}

function stopTimer() {
	if (timer) { clearInterval(timer); timer = null; }
}

// 游戏主循环：蛇移动、碰撞检测、吃食物
function tick() {
	if (gameState.value !== 'playing') return;
	dir = { ...nextDir };
	const head = snake[0];
	const nh: Point = { x: head.x + dir.x, y: head.y + dir.y };

	// 撞墙或撞自己则游戏结束
	if (nh.x < 0 || nh.x >= GRID_SIZE || nh.y < 0 || nh.y >= GRID_SIZE) { endGame(); return; }
	if (snake.some(s => s.x === nh.x && s.y === nh.y)) { endGame(); return; }

	snake.unshift(nh);
	if (nh.x === food.x && nh.y === food.y) {
		score.value += 10;
		spawnFood();
	} else {
		snake.pop();
	}
	draw();
}

// 游戏结束：停止定时器，更新最高分，显示结算界面
function endGame() {
	gameState.value = 'over';
	stopTimer();
	if (score.value > bestScore.value) {
		bestScore.value = score.value;
		saveBest();
	}
	draw();
	overlayTitle.value = '游戏结束';
	overlayDesc.value = '得分：' + score.value;
	overlayBtn.value = '重新开始';
}

// 绘制游戏画面：网格背景、蛇身、食物
function draw() {
	const ctx = uni.createCanvasContext('snakeCanvas');
	const s = GRID_SIZE * CELL_SIZE;
	// 游戏区域使用浅色底，和应用主题保持一致。
	ctx.setFillStyle('#f2f3f5');
	ctx.fillRect(0, 0, s, s);

	// 网格线
	ctx.setStrokeStyle('#e5e5ea');
	ctx.setLineWidth(0.5);
	for (let i = 0; i <= GRID_SIZE; i++) {
		ctx.beginPath(); ctx.moveTo(i * CELL_SIZE, 0); ctx.lineTo(i * CELL_SIZE, s); ctx.stroke();
		ctx.beginPath(); ctx.moveTo(0, i * CELL_SIZE); ctx.lineTo(s, i * CELL_SIZE); ctx.stroke();
	}

	// 蛇身：蛇头亮绿色，蛇尾渐淡
	snake.forEach((seg, i) => {
		const a = 1 - (i / snake.length) * 0.5;
		ctx.setFillStyle(i === 0 ? '#34c759' : `rgba(52,199,89,${a})`);
		ctx.fillRect(seg.x * CELL_SIZE + 1, seg.y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2);
	});

	// 蛇眼睛
	if (snake.length > 0) {
		const h = snake[0];
		ctx.setFillStyle('#1d1d1f');
		const ex = h.x * CELL_SIZE + (dir.x === 1 ? 12 : dir.x === -1 ? 4 : 7);
		const ey = h.y * CELL_SIZE + (dir.y === 1 ? 12 : dir.y === -1 ? 4 : 7);
		ctx.fillRect(ex, ey, 4, 4);
	}

	// 食物：红色圆形带高光
	ctx.setFillStyle('#ff3b30');
	ctx.beginPath();
	ctx.arc(food.x * CELL_SIZE + 10, food.y * CELL_SIZE + 10, 8, 0, Math.PI * 2);
	ctx.fill();
	ctx.setFillStyle('rgba(255,255,255,0.3)');
	ctx.beginPath();
	ctx.arc(food.x * CELL_SIZE + 7, food.y * CELL_SIZE + 6, 3, 0, Math.PI * 2);
	ctx.fill();

	ctx.draw();
}

// 设置移动方向（不允许直接反向）
function setDir(d: Point) {
	if (d.x + dir.x === 0 && d.y + dir.y === 0) return;
	nextDir = d;
}

// 触摸开始，记录起始位置
function onTouchStart(e: any) {
	const t = e.touches[0];
	tx = t.clientX; ty = t.clientY;
}

// 触摸结束，根据滑动方向判断移动方向
function onTouchEnd(e: any) {
	if (gameState.value !== 'playing') return;
	const t = e.changedTouches[0];
	if (!t) return;
	const dx = t.clientX - tx, dy = t.clientY - ty;
	if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
	if (Math.abs(dx) > Math.abs(dy)) {
		setDir(dx > 0 ? { x: 1, y: 0 } : { x: -1, y: 0 });
	} else {
		setDir(dy > 0 ? { x: 0, y: 1 } : { x: 0, y: -1 });
	}
}

// 键盘控制（H5 环境）：方向键和 WASD
function onKeyDown(e: any) {
	if (gameState.value !== 'playing') return;
	switch (e.keyCode) {
		case 37: case 65: setDir({ x: -1, y: 0 }); break;
		case 38: case 87: setDir({ x: 0, y: -1 }); break;
		case 39: case 68: setDir({ x: 1, y: 0 }); break;
		case 40: case 83: setDir({ x: 0, y: 1 }); break;
	}
}

function setupKeyboard() {
	if (typeof document !== 'undefined') {
		document.addEventListener('keydown', onKeyDown);
	}
}
function teardownKeyboard() {
	if (typeof document !== 'undefined') {
		document.removeEventListener('keydown', onKeyDown);
	}
}

onMounted(() => { setupKeyboard(); });
onUnmounted(() => { stopTimer(); teardownKeyboard(); });

// 页面显示时加载最高分，未开始时显示开始界面
onShow(() => {
	loadBest();
	if (gameState.value === 'idle') {
		overlayTitle.value = '贪吃蛇';
		overlayDesc.value = '点击开始游戏';
		overlayBtn.value = '开始游戏';
		const ctx = uni.createCanvasContext('snakeCanvas');
		ctx.setFillStyle('#f2f3f5');
		ctx.fillRect(0, 0, GRID_SIZE * CELL_SIZE, GRID_SIZE * CELL_SIZE);
		ctx.draw();
	}
});

onHide(() => { stopTimer(); });
</script>

<style lang="scss" scoped>
.page-snake {
	display: flex; flex-direction: column; align-items: center;
	padding: 30rpx; min-height: 100vh; box-sizing: border-box; background: var(--color-bg);
}
.game-header {
	display: flex; align-items: center; gap: 20rpx; margin-bottom: 24rpx; padding: 20rpx 28rpx; border-radius: var(--radius-lg); background: var(--color-surface); box-shadow: var(--shadow-sm);
}
.score-label, .best-label { font-size: 24rpx; color: var(--color-text-secondary); }
.score-value { margin-right: 30rpx; color: var(--color-success); font-family: var(--font-mono); font-size: 48rpx; font-weight: 700; }
.best-value { color: var(--color-warning); font-family: var(--font-mono); font-size: 36rpx; font-weight: 700; }
.game-board {
	position: relative; overflow: hidden; border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
}
.snake-canvas { width: 600rpx; height: 600rpx; display: block; }
.overlay {
	position: absolute; top: 0; left: 0; right: 0; bottom: 0;
	background: rgba(247,248,250,.92);
	display: flex; flex-direction: column; align-items: center;
	justify-content: center; gap: 20rpx;
}
.overlay-title { font-size: 40rpx; font-weight: 600; color: var(--color-text); }
.overlay-desc { font-size: 28rpx; color: var(--color-text-secondary); }
.control-hint { margin-top: 30rpx; }
.control-hint text { font-size: 24rpx; color: var(--color-text-secondary); }
</style>
