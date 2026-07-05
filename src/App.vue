<script setup lang="ts">
// 应用启动时执行初始化
import { onLaunch } from "@dcloudio/uni-app";

onLaunch(() => {
  console.log("荣小账 App Launch");
});
</script>
<style lang="scss">
// 导入 uview-plus 全局样式
@import "uview-plus/index.scss";

// 页面全局背景色：浅灰色
page {
	background-color: #f5f6fa;
}
</style>
