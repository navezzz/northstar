const money = value => value == null ? "—" : `$${Number(value).toFixed(2)}`;

async function load() {
  const body = document.querySelector("#decisions");
  try {
    let response = await fetch("api/decisions/latest");
    if (!response.ok) response = await fetch("data/latest.json");
    if (!response.ok) throw new Error("Run `northstar demo` or `northstar daily-run` first.");
    const data = await response.json();
    document.querySelector("#freshness").textContent = `Updated ${new Date(data.completed_at).toLocaleString()}`;
    const counts = Object.fromEntries(["BUY", "WATCH", "AVOID", "NO_DATA"].map(s => [s, data.decisions.filter(d => d.signal === s).length]));
    document.querySelector("#summary").innerHTML = [
      [data.decisions.length,"Symbols"], [counts.BUY,"Buy setups"], [counts.WATCH,"Watching"], [counts.AVOID + counts.NO_DATA,"Not actionable"]
    ].map(([value,label]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join("");
    body.innerHTML = data.decisions.map(d => `<tr>
      <td><strong>${d.ticker}</strong><br><small>${d.as_of}</small></td>
      <td><span class="badge ${d.signal}">${d.signal}</span></td><td>${money(d.close)}</td>
      <td>${d.entry_low == null ? "—" : `${money(d.entry_low)}–${money(d.entry_high)}`}</td>
      <td>${money(d.stop)}</td><td>${money(d.risk_per_share)}</td><td>${d.suggested_shares || "—"}</td><td>${d.reason}</td>
    </tr>`).join("");
  } catch (error) {
    body.innerHTML = `<tr><td colspan="8" class="error">${error.message}</td></tr>`;
    document.querySelector("#freshness").textContent = "No completed run";
  }
}
load();
