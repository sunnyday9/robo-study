const angleInput = document.querySelector("#frame-angle");
const sensorAxes = document.querySelector("#sensor-axes");
const frameResult = document.querySelector("#frame-result");

function updateFrame() {
  const degrees = Number(angleInput.value);
  const radians = degrees * Math.PI / 180;
  const baseX = (2 + Math.cos(radians)).toFixed(2);
  const baseY = (1 + Math.sin(radians)).toFixed(2);
  sensorAxes.setAttribute("transform", `rotate(${-degrees})`);
  frameResult.textContent = `${degrees}° → point in base: (${baseX}, ${baseY}) m`;
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
  const verdict = stamp < 1000 ? "the requested time is newer than this buffer."
    : stamp === 1000 ? "an exact transform sample is available."
      : "the stamp falls between samples; TF can interpolate.";
  tfResult.textContent = `${stamp} ms → ${verdict}`;
}

const offsetInput = document.querySelector("#action-offset");
const alignmentResult = document.querySelector("#alignment-result");
const actionLabels = [...document.querySelectorAll("[data-action]")];
const actions = ["Approach", "Approach", "Grip", "Lift", "Lift"];

function updateAlignment() {
  const offset = Number(offsetInput.value);
  actionLabels.forEach((label, index) => {
    label.textContent = actions[index + offset] ?? "Missing";
    label.classList.toggle("shifted", label.textContent !== actions[index]);
  });
  alignmentResult.textContent = `The grip label is paired with frame ${3 - offset}.`;
}

angleInput.addEventListener("input", updateFrame);
timeInput.addEventListener("input", updateTime);
offsetInput.addEventListener("change", updateAlignment);
updateFrame();
updateTime();
updateAlignment();
