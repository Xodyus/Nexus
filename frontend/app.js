const form = document.getElementById("search-form");
const input = document.getElementById("slug-input");
const statusLine = document.getElementById("status-line");
const results = document.getElementById("results");
const explain = document.getElementById("explain");

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
  document.getElementById("explain-stable-tomato").textContent = data.stabilized.tomatometer.toFixed(1);
  document.getElementById("explain-stable-audience").textContent = data.stabilized.audience.toFixed(1);

  results.hidden = false;
  explain.hidden = false;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const slug = input.value.trim();
  if (slug) loadMovie(slug);
});
