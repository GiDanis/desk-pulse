.pragma library

function list(model) {
    if (!model) return [];
    if (Array.isArray(model)) return model;
    var out = [];
    for (var i = 0; i < model.count; i++) { var row = model.get(i); if (row) out.push(row); }
    return out;
}
function number(value) { return !value ? "—" : value.displayText || (value.available ? String(value.value) + (value.unit ? " " + value.unit : "") : "—"); }
function scalar(value) { return value && value.available ? value.displayText || (typeof value.value === "boolean" ? value.value ? "Attivo" : "Disattivo" : String(value.value)) : "—"; }
function stamp(value) { return value === null || value === undefined ? "" : Qt.formatDateTime(new Date(value * 1000), "dd/MM · HH:mm"); }
function source(value) {
    if (!value) return "Dati non disponibili";
    var labels = {active: "Aggiornato", updating: "Aggiornamento", pending: "In attesa", stale: "Dati precedenti", offline: "Offline", error: "Errore fonte", unavailable: "Non disponibile"};
    var text = (value.sourceLabel ? value.sourceLabel + " · " : "") + (labels[value.status] || value.status);
    if (value.isStale && value.status !== "stale") text += " · ultimi dati";
    if (value.updatedAt !== null && value.updatedAt !== undefined) text += " · " + stamp(value.updatedAt);
    if (value.error) text += " · " + value.error;
    return text;
}
function commands(model) {
    var rows=list(model).filter(function(x) { return x.enabled; }), used=[], out=[];
    rows.forEach(function(x) {
        if (used.indexOf(x.key)>=0) return;
        var mate=(x.key===2?8:x.key===4?6:0), pair=mate ? rows.find(function(y) { return y.key===mate && y.label===x.label; }) : null;
        used.push(x.key); if (pair) used.push(pair.key);
        out.push(x.key+(pair ? "/"+pair.key : "")+" "+x.label);
    }); return out.join(" · ");
}
function weather(code) {
    if (code === 0) return "sun";
    if (code === 1 || code === 2) return "partly-cloudy";
    if (code === 3) return "cloud";
    if (code === 45 || code === 48) return "fog";
    if ([51,53,55,56,57,61,63,65,66,67,80,81,82].indexOf(code) >= 0) return "rain";
    if ([71,73,75,77,85,86].indexOf(code) >= 0) return "snow";
    if ([95,96,99].indexOf(code) >= 0) return "storm";
    return "unknown";
}
function row(id, title, detail, value, icon) { return {id: id, title: title || "", detail: detail || "", value: value === undefined ? "" : value, icon: icon || ""}; }
function info(model) { return list(model).map(function(x) { return row(x.id, x.title, x.detail, scalar(x.value)); }); }
function standings(model) { return list(model).map(function(x) { return row(x.id, number(x.position) + "  " + x.name, x.played.available ? "Giocate " + number(x.played) + " · V " + number(x.wins) + "  N " + number(x.draws) + "  P " + number(x.losses) : "", number(x.points) + " pt"); }); }
function matches(model, filter) {
    var all = list(model);
    if (filter === "PROSSIME") all = all.filter(function(m) { return m.status === "scheduled" || m.status === "postponed"; });
    if (filter === "IN CORSO") all = all.filter(function(m) { return m.status === "live"; });
    if (filter === "RISULTATI") all = all.filter(function(m) { return m.status === "finished"; });
    return all.map(function(m) { return row(m.id, m.home.name + "  –  " + m.away.name, [m.whenText, m.status === "live" ? "In corso " + number(m.minute) : m.rawStatus || m.status, m.pendingVAR ? "VAR" : ""].filter(Boolean).join(" · "), m.homeScore.available && m.awayScore.available ? number(m.homeScore) + " – " + number(m.awayScore) : "", "football"); });
}
function timing(model) { return list(model).map(function(x) { return row(x.id, number(x.position) + "  " + x.driverName, [x.team, x.compound || x.tyre, x.status].filter(Boolean).join(" · "), [number(x.time), number(x.gap)].join(" · ")); }); }
function events(model) { return list(model).map(function(x) { return row(x.id, x.name, [x.circuit, stamp(x.startsAt)].filter(Boolean).join(" · "), "", "flag"); }); }
function sessions(model) { return list(model).map(function(x) { return row(x.id, x.name, stamp(x.startsAt), x.status); }); }
function squad(model) { return list(model).map(function(x) { return row(x.id, number(x.shirtNumber) + "  " + x.name, [x.role, x.group, x.inMinute.available ? "Entra " + number(x.inMinute) : "", x.outMinute.available ? "Esce " + number(x.outMinute) : ""].filter(Boolean).join(" · ")); }); }
function settings(model) { return list(model).map(function(x) { var r = row(x.id, x.title, x.enabled ? x.detail : x.reason || x.detail, x.value.available || x.control !== "action" && x.control !== "transfer" ? scalar(x.value) : "", settingIcon(x.id)); r.enabled = x.enabled; r.actionId = x.actionId || "settings.activate"; r.targetId = x.targetId || x.id; return r; }); }
function settingIcon(id) { var exact={sports:"trophy","module.sports":"trophy","modules.sports":"trophy",services:"source","appearance.apply":"save","appearance.import":"import","appearance.export":"export","appearance.reload":"refresh","network.router":"router","network.wifi":"wifi","network.ports":"ethernet"}; if (exact[id]) return exact[id]; if (id.indexOf("network") >= 0) return "network"; if (id.indexOf("casa") >= 0) return "connected-home"; if (id.indexOf("integration") >= 0) return "plug"; if (id.indexOf("info") >= 0) return "info"; if (id.indexOf("command") >= 0) return "keyboard"; if (id.indexOf("sport") >= 0) return "football"; if (id.indexOf("racing") >= 0 || id.indexOf("f1") >= 0) return "race-car"; if (id.indexOf("motogp") >= 0) return "motorcycle"; if (id.indexOf("appearance") >= 0) return "palette"; if (id.indexOf("display") >= 0) return "display"; if (id.indexOf("notification") >= 0) return "bell"; if (id.indexOf("source") >= 0) return "source"; if (id.indexOf("account") >= 0) return "account"; if (id.indexOf("module") >= 0) return "modules"; return "settings"; }
function settingTitle(id) { var names = {index:"Impostazioni",appearance:"Aspetto","appearance.notifications":"Aspetto notifiche",display:"Schermo",modules:"Moduli e Home",notifications:"Avvisi",services:"Servizi collegati",sports:"Discipline Sport","appearance.management":"Gestione temi","notifications.categories":"Avvisi sullo schermo","notifications.quiet":"Fascia silenzio",account:"Account ChatGPT",integrations:"Sport",sources:"Dati e aggiornamenti",sport:"Calcio",racing:"Motorsport",casa:"Casa / Smart Life",network:"Rete locale"}; return names[id.replace(/^settings\./, "")] || "Impostazioni"; }
function matchRows(context) {
    var m = context.match; if (!m) return [];
    var tab = context.selection.tabId.toUpperCase();
    if (tab.indexOf("STAT") >= 0) return list(m.statistics).map(function(x) { return row(x.id, x.label, "", number(x.home) + " / " + number(x.away)); });
    if (tab.indexOf("FORMA") >= 0 || tab.indexOf("LINEUP") >= 0) {
        var out = []; list(m.lineups).forEach(function(x) { out.push(row(x.id, x.teamId === m.home.id ? m.home.name : m.away.name, [x.formation, x.coach].filter(Boolean).join(" · "))); out = out.concat(squad(x.players)); }); return out;
    }
    if (tab.indexOf("FANTA") >= 0) {
        var teams = context.fantasy ? list(context.fantasy.teams) : [];
        return teams.reduce(function(out, team) { out.push(row(team.id, team.name, "", number(team.total))); return out.concat(list(team.players).map(function(x) { return row(x.id, x.name, [x.role, x.group, list(x.bonuses).map(function(b) { return b.label + " " + number(b.count) + " (" + number(b.points) + ")"; }).join(" · ")].filter(Boolean).join(" · "), (x.withoutVote ? "S.V." : x.voteText || number(x.vote)) + " / " + (x.fantavoteText || number(x.fantavote))); })); }, []);
    }
    return list(m.events).map(function(x) { return row(x.id, x.playerName || x.text || x.kind, x.text, number(x.minute)); });
}
function teamRows(context) {
    var team = context.team; if (!team) return [];
    var tab = context.selection.tabId.toUpperCase();
    if (tab.indexOf("INFO") >= 0) return info(team.info);
    if (tab.indexOf("ROSA") >= 0 || tab.indexOf("SQUAD") >= 0) return squad(team.squad);
    var fixtures = list(team.fixtures).filter(function(m) { return !context.serieAOnly || m.competitionId === "serie_a" || m.competitionId === "football:55"; });
    return matches(fixtures.filter(function(m) { return tab.indexOf("RISULT") >= 0 ? m.status === "finished" : m.status !== "finished" && m.status !== "cancelled"; }));
}
function racingRows(context) {
    var id = context.contentId, data = context.racing, tab = context.selection.tabId.toUpperCase(); if (!data) return [];
    if (id === "racing.calendar") return events(data.events);
    if (id === "racing.standings") return standings(tab.indexOf("COSTR") >= 0 ? data.constructors : data.standings);
    if (id === "racing.event.detail") return context.event ? tab.indexOf("CIRCU") >= 0 ? info(context.event.info) : tab.indexOf("RIEP") >= 0 || tab.indexOf("SUMM") >= 0 ? info(context.event.summary) : sessions(context.event.sessions) : [];
    if (id === "racing.session.detail") return context.session ? tab.indexOf("SESSION") >= 0 || tab.indexOf("INFO") >= 0 ? info(context.session.info) : timing(context.session.results) : [];
    if (id === "racing.live") return !data.live ? [] : tab.indexOf("RACE") >= 0 || tab.indexOf("MESS") >= 0 || tab.indexOf("DIREZ") >= 0 ? list(data.live.messages).map(function(x) { return row(x.id, x.text, stamp(x.issuedAt), x.severity); }) : tab.indexOf("PISTA") >= 0 || tab.indexOf("TRACK") >= 0 ? info(data.live.info) : timing(data.live.rows);
    return [];
}
function driverRows(context) {
    var d = context.driver; if (!d) return [];
    var tab = context.selection.tabId.toUpperCase();
    if (tab.indexOf("PIT") >= 0 || tab.indexOf("SOST") >= 0) return list(d.pitStops).map(function(x) { return row(x.id, "Sosta " + number(x.stopNumber), "Giro " + number(x.lap) + " · " + x.timeText, number(x.duration)); });
    if (tab.indexOf("GIR") >= 0 || tab.indexOf("LAP") >= 0) return list(d.laps).map(function(x) { return row(x.id, "Giro " + number(x.lap), "Posizione " + number(x.position), number(x.time)); });
    if (tab.indexOf("GOM") >= 0 || tab.indexOf("TYRE") >= 0) return list(d.stints).map(function(x) { return row(x.id, x.compound, "Giri " + number(x.startLap) + "–" + number(x.endLap), "Età " + number(x.tyreAge)); });
    var out = info(d.detailRows); if (d.timing) out = timing([d.timing]).concat(out); return out;
}
function matchStatus(m) { var labels={scheduled:"Programmata",live:"In corso",finished:"Terminata",postponed:"Rinviata",cancelled:"Annullata",suspended:"Sospesa",unavailable:"Stato non disponibile"}; return (labels[m.status] || m.status) + (m.status === "live" && m.minute.available ? " · " + number(m.minute) + "′" : ""); }
function fantasyPlayers(team) { return !team ? [] : list(team.players).map(function(x) { return row(x.id,x.name,[x.role,x.group,list(x.bonuses).map(function(b) { return b.label + " " + number(b.count) + " (" + number(b.points) + ")"; }).join(" · ")].filter(Boolean).join(" · "), (x.withoutVote ? "S.V." : x.voteText || number(x.vote)) + " / " + (x.fantavoteText || number(x.fantavote))); }); }

function familyIcon(id) { return ({oggi:"clock",meteo:"partly-cloudy",account:"account",sports:"trophy",sport:"football",f1:"race-car",motogp:"motorcycle",casa:"connected-home",network:"network"})[id] || "unknown"; }
function metricIcon(code) { var id=String(code).toLowerCase(); return id.indexOf("temp")>=0 ? "thermometer" : id.indexOf("humidity")>=0 ? "droplet" : id.indexOf("fan")>=0 ? "fan" : id.indexOf("switch")>=0 ? "plug" : "info"; }
function casaDevices(model) { return list(model).map(x => row(x.id,x.name,[x.availability+(x.availabilityPrevious ? " · salvata" : ""),x.previous ? "Dato precedente" : "",x.secondaryText].filter(Boolean).join(" · "),x.primaryText,({"casa.temperature":"thermometer","casa.light":"lightbulb","casa.plug":"plug","casa.motion":"motion"})[x.iconId] || "connected-home")); }
