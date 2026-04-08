const chapters = [
  {
    kicker: "Beginning",
    title: "The world overview of conflict and fatalities",
    text: "This story begins with the worldwide monthly pattern of conflict. Each point is one month. Moving right means more fatalities, and moving up means more events. The path connects the months in time order.",
    mode: "global"
  },
  {
    kicker: "Chapter 1",
    title: "A global pattern that keeps shifting",
    text: "The global trajectory does not rise in one straight line. It moves, bends, and jumps over time, showing that conflict intensity changes unevenly from month to month.",
    mode: "global"
  },
  {
    kicker: "Chapter 2",
    title: "Some months become especially severe",
    text: "Certain months stand out because they combine higher event counts with higher fatalities. These moments pull the line upward and to the right, marking more intense periods in the timeline.",
    mode: "global_peak"
  },
  {
    kicker: "Chapter 3",
    title: "From the world view to Lebanon",
    text: "A global chart is useful for the big picture, but it can hide what happens inside one country. The story now narrows from the worldwide pattern to Lebanon’s monthly trajectory.",
    mode: "transition"
  },
  {
    kicker: "Chapter 4",
    title: "Lebanon’s monthly trajectory",
    text: "Now the chart zooms into Lebanon only. Keeping the same visual form makes the comparison easier, while the tighter scale reveals changes that were too small to see in the global view.",
    mode: "lebanon"
  },
  {
    kicker: "Chapter 5",
    title: "What the Lebanon view reveals",
    text: "In Lebanon, month-to-month movement becomes much clearer. The national path turns the wider global story into a more concrete case, showing when violence intensifies and when fatalities rise more sharply.",
    mode: "lebanon_peak"
  }
];

const COLORS = {
  global: "#8d5a97",
  globalLight: "rgba(141, 90, 151, 0.14)",
  lebanon: "#c45a3c",
  lebanonLight: "rgba(196, 90, 60, 0.16)",
  muted: "rgba(80, 74, 68, 0.18)"
};

const margin = { top: 110, right: 90, bottom: 58, left: 70 };

const svg = d3.select("#chart");
const cardKicker = document.getElementById("card-kicker");
const cardTitle = document.getElementById("card-title");
const cardText = document.getElementById("card-text");
const chapterDots = document.getElementById("chapter-dots");
const mainSubtitle = document.getElementById("story-main-subtitle");

let width = window.innerWidth;
let height = window.innerHeight;

let globalData = [];
let lebanonData = [];
let currentStep = 0;

let x = d3.scaleLinear();
let y = d3.scaleLinear();

let chartG;
let gridX;
let gridY;
let axisX;
let axisY;
let axisTitles;
let backgroundLayer;
let contextLayer;
let highlightLayer;
let pointLayer;
let annotationLayer;

chapters.forEach((_, i) => {
  const dot = document.createElement("div");
  dot.className = "chapter-dot" + (i === 0 ? " active" : "");
  chapterDots.appendChild(dot);
});

function monthKey(d) {
  return d.year * 100 + d.month_num;
}

function uniqueByText(items) {
  const seen = new Set();
  return items.filter(item => {
    if (!item || !item.text || seen.has(item.text)) return false;
    seen.add(item.text);
    return true;
  });
}

function paddedExtent(values, lowPad = 0.06, highPad = 0.1) {
  const min = d3.min(values) ?? 0;
  const max = d3.max(values) ?? 1;
  const span = Math.max(max - min, 1);
  return [Math.max(0, min - span * lowPad), max + span * highPad];
}

function getPeakEvents(series) {
  return series.reduce((best, d) => (d.events > best.events ? d : best), series[0]);
}

function getPeakFatalities(series) {
  return series.reduce((best, d) => (d.fatalities > best.fatalities ? d : best), series[0]);
}

function getRecentPoint(series) {
  return [...series].sort((a, b) => monthKey(a) - monthKey(b))[series.length - 1];
}

function getStartPoint(series) {
  return [...series].sort((a, b) => monthKey(a) - monthKey(b))[0];
}

function getSeriesLine(series) {
  return d3.line()
    .x(d => x(d.fatalities))
    .y(d => y(d.events))(series);
}

function getChapterState(stepIndex) {
  const chapter = chapters[stepIndex];

  if (chapter.mode === "global" || chapter.mode === "global_peak" || chapter.mode === "transition") {
    return {
      chapter,
      series: globalData,
      domainX: paddedExtent(globalData.map(d => d.fatalities), 0.03, 0.1),
      domainY: paddedExtent(globalData.map(d => d.events), 0.05, 0.1),
      pathColor: COLORS.global,
      pointColor: COLORS.global,
      backgroundData: globalData,
      backgroundColor: COLORS.global,
      annotate: chapter.mode === "global_peak" ? "peaks" : "global"
    };
  }

  return {
    chapter,
    series: lebanonData,
    domainX: paddedExtent(lebanonData.map(d => d.fatalities), 0.08, 0.14),
    domainY: paddedExtent(lebanonData.map(d => d.events), 0.08, 0.14),
    pathColor: COLORS.lebanon,
    pointColor: COLORS.lebanon,
    backgroundData: lebanonData,
    backgroundColor: COLORS.lebanon,
    annotate: chapter.mode === "lebanon_peak" ? "peaks" : "lebanon"
  };
}

function buildChart() {
  svg.selectAll("*").remove();
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  chartG = svg.append("g");

  gridX = chartG.append("g").attr("class", "grid");
  gridY = chartG.append("g").attr("class", "grid");

  axisX = chartG.append("g").attr("class", "axis");
  axisY = chartG.append("g").attr("class", "axis");
  axisTitles = chartG.append("g");

  backgroundLayer = chartG.append("g");
  contextLayer = chartG.append("g");
  highlightLayer = chartG.append("g");
  pointLayer = chartG.append("g");
  annotationLayer = chartG.append("g");
}

function updateScales(domainX, domainY, instant = false) {
  width = window.innerWidth;
  height = window.innerHeight;

  svg.attr("viewBox", `0 0 ${width} ${height}`);

  x.domain(domainX).range([margin.left, width - margin.right]);
  y.domain(domainY).range([height - margin.bottom, margin.top]);

  const duration = instant ? 0 : 700;
  const t = d3.transition().duration(duration).ease(d3.easeCubicOut);

  gridX
    .attr("transform", `translate(0, ${height - margin.bottom})`)
    .transition(t)
    .call(
      d3.axisBottom(x)
        .ticks(Math.max(5, Math.floor((width - margin.left - margin.right) / 170)))
        .tickSize(-(height - margin.top - margin.bottom))
        .tickFormat(d3.format(","))
    );

  gridY
    .attr("transform", `translate(${margin.left},0)`)
    .transition(t)
    .call(
      d3.axisLeft(y)
        .ticks(Math.max(5, Math.floor((height - margin.top - margin.bottom) / 110)))
        .tickSize(-(width - margin.left - margin.right))
        .tickFormat(d3.format(","))
    );

  axisX
    .attr("transform", `translate(0, ${height - margin.bottom})`)
    .transition(t)
    .call(
      d3.axisBottom(x)
        .ticks(Math.max(5, Math.floor((width - margin.left - margin.right) / 170)))
        .tickFormat(d3.format(","))
    );

  axisY
    .attr("transform", `translate(${margin.left},0)`)
    .transition(t)
    .call(
      d3.axisLeft(y)
        .ticks(Math.max(5, Math.floor((height - margin.top - margin.bottom) / 110)))
        .tickFormat(d3.format(","))
    );

  axisTitles.selectAll("*").remove();

  axisTitles.append("text")
    .attr("class", "axis-label")
    .attr("x", margin.left)
    .attr("y", margin.top - 30)
    .text("Events");

  axisTitles.append("text")
    .attr("class", "axis-sub")
    .attr("x", margin.left)
    .attr("y", margin.top - 14)
    .text("Monthly totals");

  axisTitles.append("text")
    .attr("class", "axis-label")
    .attr("x", width - margin.right)
    .attr("y", height - 24)
    .attr("text-anchor", "end")
    .text("Fatalities");

  axisTitles.append("text")
    .attr("class", "axis-sub")
    .attr("x", width - margin.right)
    .attr("y", height - 8)
    .attr("text-anchor", "end")
    .text("Monthly totals");
}

function drawBackground(data, color, instant = false) {
  const t = d3.transition().duration(instant ? 0 : 700).ease(d3.easeCubicOut);

  const pts = backgroundLayer.selectAll("circle")
    .data(data, d => d.label || `${d.year}-${d.month_num}`);

  pts.join(
    enter => enter.append("circle")
      .attr("class", "bg-point")
      .attr("cx", d => x(d.fatalities))
      .attr("cy", d => y(d.events))
      .attr("r", 0)
      .attr("fill", color)
      .call(enter => enter.transition(t).attr("r", 4.5)),
    update => update.call(update => update.transition(t)
      .attr("cx", d => x(d.fatalities))
      .attr("cy", d => y(d.events))
      .attr("fill", color)
      .attr("r", 4.5)),
    exit => exit.call(exit => exit.transition(t).attr("r", 0).remove())
  );
}

function drawSeries(series, pathColor, pointColor, instant = false) {
  const t = d3.transition().duration(instant ? 0 : 700).ease(d3.easeCubicOut);

  contextLayer.selectAll("path")
    .data([series])
    .join("path")
    .attr("class", "context-path")
    .transition(t)
    .attr("d", getSeriesLine(series));

  highlightLayer.selectAll("path")
    .data([series])
    .join("path")
    .attr("class", "highlight-path")
    .attr("stroke", pathColor)
    .transition(t)
    .attr("d", getSeriesLine(series));

  const points = pointLayer.selectAll("circle")
    .data(series, d => d.label || `${d.year}-${d.month_num}`);

  points.join(
    enter => enter.append("circle")
      .attr("class", "current-point")
      .attr("cx", d => x(d.fatalities))
      .attr("cy", d => y(d.events))
      .attr("r", 0)
      .attr("fill", pointColor)
      .call(enter => enter.transition(t).attr("r", 5.2)),
    update => update.call(update => update.transition(t)
      .attr("cx", d => x(d.fatalities))
      .attr("cy", d => y(d.events))
      .attr("r", 5.2)
      .attr("fill", pointColor)),
    exit => exit.call(exit => exit.transition(t).attr("r", 0).remove())
  );
}

function makeAnnotations(series, mode) {
  if (!series.length) return [];

  const start = getStartPoint(series);
  const recent = getRecentPoint(series);
  const peakEvents = getPeakEvents(series);
  const peakFatalities = getPeakFatalities(series);

  if (mode === "global") {
    return uniqueByText([
      { point: start, text: start.label, dx: 12, dy: -12 },
      { point: peakFatalities, text: `Deadliest: ${peakFatalities.label}`, dx: 14, dy: -18 },
      { point: recent, text: `Latest: ${recent.label}`, dx: 14, dy: 16 }
    ]);
  }

  if (mode === "lebanon") {
    return uniqueByText([
      { point: start, text: start.label, dx: 12, dy: -12 },
      { point: recent, text: `Latest: ${recent.label}`, dx: 14, dy: 16 }
    ]);
  }

  return uniqueByText([
    { point: peakEvents, text: `Highest events: ${peakEvents.label}`, dx: 14, dy: -16 },
    { point: peakFatalities, text: `Highest fatalities: ${peakFatalities.label}`, dx: 14, dy: 16 },
    { point: recent, text: `Latest: ${recent.label}`, dx: 14, dy: 36 }
  ]);
}

function drawAnnotations(series, mode, instant = false) {
  const annotations = makeAnnotations(series, mode);
  const t = d3.transition().duration(instant ? 0 : 700).ease(d3.easeCubicOut);

  const groups = annotationLayer.selectAll("g.annotation")
    .data(annotations, d => d.text);

  const enterGroups = groups.enter()
    .append("g")
    .attr("class", "annotation");

  enterGroups.append("line");
  enterGroups.append("text");

  const merged = enterGroups.merge(groups);

  merged.select("line")
    .transition(t)
    .attr("x1", d => x(d.point.fatalities))
    .attr("y1", d => y(d.point.events))
    .attr("x2", d => x(d.point.fatalities) + d.dx - 4)
    .attr("y2", d => y(d.point.events) + d.dy + 4);

  merged.select("text")
    .text(d => d.text)
    .transition(t)
    .attr("x", d => x(d.point.fatalities) + d.dx)
    .attr("y", d => y(d.point.events) + d.dy);

  groups.exit().remove();
}

function activateStep(stepIndex, instant = false) {
  currentStep = stepIndex;
  const state = getChapterState(stepIndex);

  cardKicker.textContent = state.chapter.kicker;
  cardTitle.textContent = state.chapter.title;
  cardText.textContent = state.chapter.text;

  if (stepIndex <= 2) {
    mainSubtitle.textContent = "Each point is one month in the global data. Moving right means more fatalities, and moving up means more events.";
  } else {
    mainSubtitle.textContent = "The same chart form is now used for Lebanon only, so the change in scale reveals the national monthly pattern more clearly.";
  }

  document.querySelectorAll(".chapter-dot").forEach((dot, i) => {
    dot.classList.toggle("active", i === stepIndex);
  });

  updateScales(state.domainX, state.domainY, instant);
  drawBackground(state.backgroundData, state.backgroundColor, instant);
  drawSeries(state.series, state.pathColor, state.pointColor, instant);
  drawAnnotations(state.series, state.annotate, instant);
}

function initScroll() {
  const steps = document.querySelectorAll(".step");

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const step = +entry.target.dataset.step;
        activateStep(step);
      }
    });
  }, { threshold: 0.58 });

  steps.forEach(step => observer.observe(step));
}

function normalizeMonthLabel(d) {
  if (d.label) return d.label;
  return `${d.month} ${d.year}`;
}

Promise.all([
  d3.csv(window.STORY_FILES.global, d => ({
    year: +d.year,
    month_num: +d.month_num,
    month: d.month,
    label: normalizeMonthLabel(d),
    event_type: d.event_type,
    events: +d.events,
    fatalities: +d.fatalities,
    countries_with_data: +d.countries_with_data
  })),
  d3.csv(window.STORY_FILES.country, d => ({
    iso3: d.iso3,
    country: (d.country || "").trim(),
    year: +d.year,
    month_num: +d.month_num,
    month: d.month,
    label: `${d.month} ${d.year}`,
    events: +d.events,
    fatalities: +d.fatalities
  }))
]).then(([globalRows, countryRows]) => {
  globalData = globalRows
    .filter(d => d.event_type === "All")
    .sort((a, b) => monthKey(a) - monthKey(b));

  lebanonData = countryRows
    .filter(d => d.country.toLowerCase() === "lebanon")
    .sort((a, b) => monthKey(a) - monthKey(b));

  if (!globalData.length) {
    throw new Error("Global file loaded, but no rows with event_type = 'All' were found.");
  }

  if (!lebanonData.length) {
    throw new Error("Country file loaded, but no rows for Lebanon were found.");
  }

  buildChart();
  activateStep(0, true);
  initScroll();

  window.addEventListener("resize", () => {
    buildChart();
    activateStep(currentStep, true);
  });
}).catch(err => {
  console.error(err);

  cardKicker.textContent = "Error";
  cardTitle.textContent = "The chart could not load";
  cardText.textContent = "Check that both CSV files are inside the data folder and that the file names match exactly: global_story_monthly.csv and conflict_country_monthly.csv.";
});