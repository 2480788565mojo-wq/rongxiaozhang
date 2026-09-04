// 按需引入 echarts：只注册项目实际用到的图表和组件。
// 整库引入约 1MB，会把小程序主包顶破 2MB 上限；按需引入可减小一半以上。
// 项目用到的能力：折线图（TrendLine）、饼图（CategoryPie）、仪表盘（BudgetGauge）、
// 直角坐标系网格、提示框、图例、Canvas 渲染器、渐变色（graphic.LinearGradient）。
import * as echarts from "echarts/core";
import { GaugeChart, LineChart, PieChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, PieChart, GaugeChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export default echarts;
