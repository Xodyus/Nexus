const form = document.getElementById("search-form");
const input = document.getElementById("slug-input");
const statusLine = document.getElementById("status-line");
const results = document.getElementById("results");
const explain = document.getElementById("explain");
const candidatesList = document.getElementById("candidates");

const historyList = document.getElementById("history-list");

const compareSection = document.getElementById("compare");
const compareForm = document.getElementById("compare-form");
const compareInput = document.getElementById("compare-input");
const compareCandidates = document.getElementById("compare-candidates");
const compareStatus = document.getElementById("compare-status");
const compareTable = document.getElementById("compare-table");

let currentMovie = null; // { slug, data } for the movie currently on screen

function bandFor(score) {
  if (score >= 75) return { band: "good", text: "Good" };
  if (score >= 60) return { band: "warning", text: "Mixed" };
  if (score >= 40) return { band: "serious", text: "Weak" };
  return { band: "critical", text: "Poor" };
}

function fillTile(tileId, score, footnote) {
  const tile = document.getElementById(tileId);
  const { band, text } = bandFor(score);

  tile.classList.remove("band-good", "band-warning", "band-serious", "band-critical");
  tile.classList.add(`band-${band}`);

  tile.querySelector(".hero-figure").textContent = Math.round(score);
  tile.querySelector(".meter-fill").style.width = `${Math.max(0, Math.min(100, score))}%`;
  tile.querySelector(".status-text").textContent = text;
  tile.querySelector(".tile-footnote").textContent = footnote || "";
}

function showStatus(message, isError) {
  statusLine.hidden = false;
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", Boolean(isError));
}

function showCandidates(candidates) {
  candidatesList.innerHTML = "";
  if (!candidates.length) {
    candidatesList.hidden = true;
    return;
  }
  for (const candidate of candidates) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = candidate.year
      ? `${candidate.title} (${candidate.year})`
      : candidate.title;
    button.addEventListener("click", () => {
      candidatesList.hidden = true;
      loadMovie(candidate.slug);
    });
    item.appendChild(button);
    candidatesList.appendChild(item);
  }
  candidatesList.hidden = false;
}

async function searchTitle(title) {
  results.hidden = true;
  explain.hidden = true;
  candidatesList.hidden = true;
  showStatus(`Searching for "${title}"...`);

  let response;
  try {
    response = await fetch(`/api/search?title=${encodeURIComponent(title)}`);
  } catch (err) {
    showStatus(`Network error: ${err.message}`, true);
    return;
  }

  const data = await response.json();
  if (!response.ok) {
    showStatus(data.error || "Something went wrong.", true);
    return;
  }

  const candidates = data.candidates || [];
  if (candidates.length === 1) {
    loadMovie(candidates[0].slug);
    return;
  }

  statusLine.hidden = true;
  showCandidates(candidates);
}

async function loadMovie(slug) {
  results.hidden = true;
  explain.hidden = true;
  showStatus(`Fetching "${slug}" from Rotten Tomatoes (first run scrapes + caches, later runs are instant)...`);

  let response;
  try {
    response = await fetch(`/api/movie/${encodeURIComponent(slug)}`);
  } catch (err) {
    showStatus(`Network error: ${err.message}`, true);
    return;
  }

  const data = await response.json();
  if (!response.ok) {
    showStatus(data.error || "Something went wrong.", true);
    return;
  }

  statusLine.hidden = true;

  fillTile(
    "tile-tomatometer",
    data.inputs.tomatometer_score,
    `${data.inputs.critic_review_count} critic reviews`
  );
  fillTile(
    "tile-audience",
    data.inputs.audience_score,
    `${data.inputs.audience_review_count} audience ratings`
  );
  fillTile(
    "tile-realistic",
    data.realistic_score,
    "Shrunk toward baseline + controversy-adjusted"
  );

  document.getElementById("explain-penalty").textContent = data.controversy_penalty.toFixed(1);
  document.getElementById("explain-stable-tomato").textContent = data.stabilized.critic.toFixed(1);
  document.getElementById("explain-stable-audience").textContent = data.stabilized.audience.toFixed(1);

  results.hidden = false;
  explain.hidden = false;

  currentMovie = { slug, data };
  compareSection.hidden = false;
  compareTable.hidden = true;
  compareCandidates.hidden = true;
  compareStatus.hidden = true;
  compareInput.value = "";

  loadHistory();
}

async function loadHistory() {
  let response;
  try {
    response = await fetch("/api/history");
  } catch (err) {
    return; // history sidebar is a nice-to-have, fail silently
  }
  if (!response.ok) return;

  const data = await response.json();
  const entries = data.history || [];

  historyList.innerHTML = "";
  if (!entries.length) {
    const empty = document.createElement("li");
    empty.className = "history-empty";
    empty.textContent = "Nothing scored yet.";
    historyList.appendChild(empty);
    return;
  }

  for (const entry of entries) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    const label = document.createElement("span");
    label.textContent = entry.slug;
    const score = document.createElement("span");
    score.className = "history-score";
    score.textContent = entry.realistic_score != null ? Math.round(entry.realistic_score) : "–";
    button.appendChild(label);
    button.appendChild(score);
    button.addEventListener("click", () => loadMovie(entry.slug));
    item.appendChild(button);
    historyList.appendChild(item);
  }
}

function showCompareCandidates(candidates) {
  compareCandidates.innerHTML = "";
  if (!candidates.length) {
    compareCandidates.hidden = true;
    return;
  }
  for (const candidate of candidates) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = candidate.year
      ? `${candidate.title} (${candidate.year})`
      : candidate.title;
    button.addEventListener("click", () => {
      compareCandidates.hidden = true;
      loadCompare(candidate.slug);
    });
    item.appendChild(button);
    compareCandidates.appendChild(item);
  }
  compareCandidates.hidden = false;
}

function showCompareStatus(message, isError) {
  compareStatus.hidden = false;
  compareStatus.textContent = message;
  compareStatus.classList.toggle("is-error", Boolean(isError));
}

async function searchCompareTitle(title) {
  compareCandidates.hidden = true;
  compareTable.hidden = true;
  showCompareStatus(`Searching for "${title}"...`);

  let response;
  try {
    response = await fetch(`/api/search?title=${encodeURIComponent(title)}`);
  } catch (err) {
    showCompareStatus(`Network error: ${err.message}`, true);
    return;
  }

  const data = await response.json();
  if (!response.ok) {
    showCompareStatus(data.error || "Something went wrong.", true);
    return;
  }

  const candidates = data.candidates || [];
  if (candidates.length === 1) {
    loadCompare(candidates[0].slug);
    return;
  }

  compareStatus.hidden = true;
  showCompareCandidates(candidates);
}

async function loadCompare(slug) {
  if (!currentMovie) return;
  showCompareStatus(`Fetching "${slug}"...`);
  compareTable.hidden = true;

  let response;
  try {
    response = await fetch(`/api/movie/${encodeURIComponent(slug)}`);
  } catch (err) {
    showCompareStatus(`Network error: ${err.message}`, true);
    return;
  }

  const data = await response.json();
  if (!response.ok) {
    showCompareStatus(data.error || "Something went wrong.", true);
    return;
  }

  compareStatus.hidden = true;

  document.getElementById("compare-col-current").textContent = currentMovie.slug;
  document.getElementById("compare-col-other").textContent = slug;

  document.getElementById("compare-tomato-current").textContent =
    `${Math.round(currentMovie.data.inputs.tomatometer_score)}%`;
  document.getElementById("compare-tomato-other").textContent =
    `${Math.round(data.inputs.tomatometer_score)}%`;

  document.getElementById("compare-audience-current").textContent =
    `${Math.round(currentMovie.data.inputs.audience_score)}%`;
  document.getElementById("compare-audience-other").textContent =
    `${Math.round(data.inputs.audience_score)}%`;

  document.getElementById("compare-realistic-current").textContent =
    Math.round(currentMovie.data.realistic_score);
  document.getElementById("compare-realistic-other").textContent =
    Math.round(data.realistic_score);

  compareTable.hidden = false;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (value) searchTitle(value);
});

compareForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = compareInput.value.trim();
  if (value) searchCompareTitle(value);
});

loadHistory();
