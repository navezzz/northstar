const money = value => value == null ? "—" : `$${Number(value).toFixed(2)}`;
const percent = value => value == null ? "—" : `${Number(value).toFixed(2)}%`;
let strategies = [];

function metric(value, label, tone = "") {
  return `<div class="metric ${tone}"><strong>${value}</strong><span>${label}</span></div>`;
}

function emptyRow(columns, message) {
  return `<tr><td colspan="${columns}" class="empty">${message}</td></tr>`;
}

function renderStrategy(strategy) {
  document.querySelectorAll(".strategy-tab").forEach(button => button.classList.toggle("active", button.dataset.id === strategy.id));
  document.querySelector("#strategy-name").textContent = `${strategy.name} v${strategy.version}`;
  document.querySelector("#strategy-description").textContent = strategy.description;
  const decisions = strategy.recommendations || [];
  const counts = Object.fromEntries(["BUY", "WATCH", "AVOID", "NO_DATA"].map(s => [s, decisions.filter(d => d.signal === s).length]));
  const paper = strategy.paper;
  const backtest = strategy.backtest;
  document.querySelector("#summary").innerHTML = [
    [counts.BUY,"Buy signals"], [counts.WATCH,"Watching"], [money(paper.equity),"Paper equity"], [percent(backtest.total_return_pct),"Backtest return"]
  ].map(([value,label]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join("");
  document.querySelector("#decisions").innerHTML = decisions.map(d => `<tr>
    <td><strong>${d.ticker}</strong><br><small>${d.as_of}</small></td>
    <td><span class="badge ${d.signal}">${d.signal}</span><br><small>${d.valid_for}</small></td>
    <td>${money(d.reference_price)}</td><td>${d.signal === "BUY" ? "Next open" : "—"}</td>
    <td>${money(d.stop)}</td><td>${money(d.target)}</td><td>${d.reason}</td>
  </tr>`).join("");
  document.querySelector("#paper-period").textContent = `${paper.start} → ${paper.as_of || "waiting"}`;
  document.querySelector("#paper-metrics").innerHTML = [
    metric(money(paper.equity),"Equity"), metric(percent(paper.total_return_pct),"Return"), metric(paper.open_positions.length,"Open"), metric(paper.num_trades,"Closed trades")
  ].join("");
  document.querySelector("#positions").innerHTML = paper.open_positions.length ? paper.open_positions.map(p => `<tr><td><strong>${p.ticker}</strong></td><td>${p.entry_date}</td><td>${money(p.entry_price)}</td><td>${p.shares}</td><td>${money(p.stop)}</td><td>${money(p.current_price)}</td></tr>`).join("") : emptyRow(6,"No open paper positions");
  document.querySelector("#backtest-period").textContent = `${backtest.start} → ${backtest.as_of}`;
  document.querySelector("#backtest-metrics").innerHTML = [
    metric(percent(backtest.total_return_pct),"Strategy"), metric(percent(backtest.spy_return_pct),"SPY"), metric(percent(backtest.max_drawdown_pct),"Max drawdown"), metric(backtest.num_trades,"Trades"), metric(percent(backtest.win_rate_pct),"Win rate")
  ].join("");
  document.querySelector("#history").innerHTML = paper.trades.length ? [...paper.trades].reverse().map(t => `<tr><td><strong>${t.ticker}</strong></td><td>${t.entry_date}<br>${money(t.entry_price)}</td><td>${t.exit_date}<br>${money(t.exit_price)}</td><td>${t.shares}</td><td>${percent(t.return_pct)}</td><td>${money(t.pnl)}</td><td>${t.reason}</td></tr>`).join("") : emptyRow(7,"No completed paper trades yet");
}

async function load() {
  const body = document.querySelector("#decisions");
  try {
    let response = await fetch("api/decisions/latest");
    if (!response.ok) response = await fetch("data/latest.json");
    if (!response.ok) throw new Error("Run `northstar demo` or `northstar daily-run` first.");
    const data = await response.json();
    if (data.schema_version !== 3 || !data.strategies) throw new Error("Dashboard data uses an older schema; run the new export-site command.");
    document.querySelector("#freshness").textContent = `Updated ${new Date(data.completed_at).toLocaleString()}`;
    strategies = data.strategies;
    document.querySelector("#strategy-tabs").innerHTML = strategies.map((strategy, index) => `<button class="strategy-tab ${index === 0 ? "active" : ""}" data-id="${strategy.id}">${strategy.name}<small>${strategy.status}</small></button>`).join("");
    document.querySelectorAll(".strategy-tab").forEach(button => button.addEventListener("click", () => renderStrategy(strategies.find(strategy => strategy.id === button.dataset.id))));
    renderStrategy(strategies[0]);
  } catch (error) {
    body.innerHTML = `<tr><td colspan="7" class="error">${error.message}</td></tr>`;
    document.querySelector("#freshness").textContent = "No completed run";
  }
}
load();
