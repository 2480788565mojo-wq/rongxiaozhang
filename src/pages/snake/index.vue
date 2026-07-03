<template>
	<view class="page-snake">
		<view class="game-header">
			<text class="score-label">得分</text>
			<text class="score-value">{{ score }}</text>
			<text class="best-label">最高分</text>
			<text class="best-value">{{ bestScore }}</text>
		</view>

		<view class="game-board" @touchstart="onTouchStart" @touchend="onTouchEnd">
			<canvas canvas-id="snakeCanvas" class="snake-canvas"></canvas>
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

function loadBest() {
	try {
		const d = uni.getStorageSync('rzz_snake_best');
		if (d) bestScore.value = parseInt(d) || 0;
	} catch {}
}
function saveBest() {
	uni.setStorageSync('rzz_snake_best', String(bestScore.value));
}

const overlayTitle = ref('');
const overlayDesc = ref('');
const overlayBtn = ref('');

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

function tick() {
	if (gameState.value !== 'playing') return;
	dir = { ...nextDir };
	const head = snake[0];
	const nh: Point = { x: head.x + dir.x, y: head.y + dir.y };

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

function draw() {
	const ctx = uni.createCanvasContext('snakeCanvas');
	const s = GRID_SIZE * CELL_SIZE;
	ctx.setFillStyle('#1a1a2e');
	ctx.fillRect(0, 0, s, s);

	ctx.setStrokeStyle('#16213e');
	ctx.setLineWidth(0.5);
	for (let i = 0; i <= GRID_SIZE; i++) {
		ctx.beginPath(); ctx.moveTo(i * CELL_SIZE, 0); ctx.lineTo(i * CELL_SIZE, s); ctx.stroke();
		ctx.beginPath(); ctx.moveTo(0, i * CELL_SIZE); ctx.lineTo(s, i * CELL_SIZE); ctx.stroke();
	}

	snake.forEach((seg, i) => {
		const a = 1 - (i / snake.length) * 0.5;
		ctx.setFillStyle(i === 0 ? '#4cd964' : `rgba(76,217,100,${a})`);
		ctx.fillRect(seg.x * CELL_SIZE + 1, seg.y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2);
	});

	if (snake.length > 0) {
		const h = snake[0];
		ctx.setFillStyle('#fff');
		const ex = h.x * CELL_SIZE + (dir.x === 1 ? 12 : dir.x === -1 ? 4 : 7);
		const ey = h.y * CELL_SIZE + (dir.y === 1 ? 12 : dir.y === -1 ? 4 : 7);
		ctx.fillRect(ex, ey, 4, 4);
	}

	ctx.setFillStyle('#ff6b6b');
	ctx.beginPath();
	ctx.arc(food.x * CELL_SIZE + 10, food.y * CELL_SIZE + 10, 8, 0, Math.PI * 2);
	ctx.fill();
	ctx.setFillStyle('rgba(255,255,255,0.3)');
	ctx.beginPath();
	ctx.arc(food.x * CELL_SIZE + 7, food.y * CELL_SIZE + 6, 3, 0, Math.PI * 2);
	ctx.fill();

	ctx.draw();
}

function setDir(d: Point) {
	if (d.x + dir.x === 0 && d.y + dir.y === 0) return;
	nextDir = d;
}

function onTouchStart(e: any) {
	const t = e.touches[0];
	tx = t.clientX; ty = t.clientY;
}

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

onShow(() => {
	loadBest();
	if (gameState.value === 'idle') {
		overlayTitle.value = '贪吃蛇';
		overlayDesc.value = '点击开始游戏';
		overlayBtn.value = '开始游戏';
		const ctx = uni.createCanvasContext('snakeCanvas');
		ctx.setFillStyle('#1a1a2e');
		ctx.fillRect(0, 0, GRID_SIZE * CELL_SIZE, GRID_SIZE * CELL_SIZE);
		ctx.draw();
	}
});

onHide(() => { stopTimer(); });
</script>

<style lang="scss" scoped>
.page-snake {
	display: flex; flex-direction: column; align-items: center;
	padding: 30rpx; min-height: 100vh; background: #0f0f23;
}
.game-header {
	display: flex; align-items: center; gap: 20rpx; margin-bottom: 30rpx;
}
.score-label, .best-label { font-size: 24rpx; color: #666; }
.score-value { font-size: 48rpx; font-weight: bold; color: #4cd964; margin-right: 30rpx; }
.best-value { font-size: 36rpx; font-weight: bold; color: #f0ad4e; }
.game-board {
	position: relative; border-radius: 16rpx; overflow: hidden;
	box-shadow: 0 0 40rpx rgba(76, 217, 100, 0.15);
}
.snake-canvas { width: 600rpx; height: 600rpx; display: block; }
.overlay {
	position: absolute; top: 0; left: 0; right: 0; bottom: 0;
	background: rgba(0,0,0,0.7);
	display: flex; flex-direction: column; align-items: center;
	justify-content: center; gap: 20rpx;
}
.overlay-title { font-size: 40rpx; font-weight: bold; color: #fff; }
.overlay-desc { font-size: 28rpx; color: #ccc; }
.control-hint { margin-top: 30rpx; }
.control-hint text { font-size: 24rpx; color: #666; }
</style>
