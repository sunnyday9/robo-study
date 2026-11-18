const angleInput = document.querySelector("#frame-angle");
const sensorAxes = document.querySelector("#sensor-axes");
const frameResult = document.querySelector("#frame-result");

function updateFrame() {
  const degrees = Number(angleInput.value);
  const radians = degrees * Math.PI / 180;
  const baseX = (2 + Math.cos(radians)).toFixed(2);
  const baseY = (1 + Math.sin(radians)).toFixed(2);
  sensorAxes.setAttribute("transform", `rotate(${-degrees})`);
  frameResult.textContent = `${degrees}° → 基座坐标： (${baseX}, ${baseY}) m`;
}

const timeInput = document.querySelector("#tf-time");
const tfMarker = document.querySelector("#tf-marker");
const tfLabel = document.querySelector("#tf-marker-label");
const tfResult = document.querySelector("#tf-result");

function updateTime() {
  const stamp = Number(timeInput.value);
  const markerX = 60 + (stamp - 900) * 1.8;
  tfMarker.setAttribute("cx", markerX);
  tfLabel.setAttribute("x", markerX);
  const verdict = stamp < 1000 ? "请求的时间晚于缓冲区里最新的样本。"
    : stamp === 1000 ? "找到了时间戳完全一致的变换样本。"
      : "时间戳位于两个样本之间，TF 可以插值。";
  tfResult.textContent = `${stamp} ms → ${verdict}`;
}

const offsetInput = document.querySelector("#action-offset");
const alignmentResult = document.querySelector("#alignment-result");
const actionLabels = [...document.querySelectorAll("[data-action]")];
const actions = ["接近", "接近", "抓取", "抬起", "抬起"];

function updateAlignment() {
  const offset = Number(offsetInput.value);
  actionLabels.forEach((label, index) => {
    label.textContent = actions[index + offset] ?? "缺失";
    label.classList.toggle("shifted", label.textContent !== actions[index]);
  });
  alignmentResult.textContent = `抓取动作与第 ${3 - offset} 帧配对。`;
}

angleInput.addEventListener("input", updateFrame);
timeInput.addEventListener("input", updateTime);
offsetInput.addEventListener("change", updateAlignment);
updateFrame();
updateTime();
updateAlignment();
