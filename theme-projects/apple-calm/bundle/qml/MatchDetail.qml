pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Item {
    id: root
    required property MatchContext context
    readonly property var style: context.style
    readonly property var match: context.match
    readonly property string tab: context.selection.tabId
    readonly property bool fantasy: tab === "FANTACALCIO"
    readonly property bool ready: width > 0 && !!match
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:32,y:24,width:896,height:92},{role:"body",x:32,y:132,width:896,height:Math.max(1,height-180)}]
    readonly property var teams: { context.dataRevision; return context.fantasy ? Format.list(context.fantasy.teams) : [] }
    readonly property var fantasyTeam: teams.find(x => x.id === context.selection.anchorId || Format.list(x.players).some(p => p.id === context.selection.selectedId)) || teams[0] || null
    function settleMotion() { }
    Rectangle { anchors.fill:parent; color:root.style.backgroundOverlay }
    Label { x:32; y:24; width:896; height:42; themeStyle:root.style; size:30; font.weight:Font.DemiBold; text:root.fantasy ? "Fantacalcio" : "Partita"; maximumLineCount:1 }
    Tabs { x:32; y:76; width:896; context:root.context; tabs:root.context.tabs }
    Card {
        x:32; y:132; width:896; height:126; style:root.style; visible:root.tab !== "FORMAZIONI"
        Label { x:20; y:17; width:285; height:56; themeStyle:root.style; size:30; font.weight:Font.DemiBold; text:root.match ? root.match.home.name : ""; horizontalAlignment:Text.AlignHCenter; maximumLineCount:1 }
        Label { x:320; y:9; width:256; height:70; themeStyle:root.style; size:52; font.weight:Font.DemiBold; color:root.style.semantic.accentTextOnCard; text:root.match && root.match.homeScore.available && root.match.awayScore.available ? Format.number(root.match.homeScore) + " – " + Format.number(root.match.awayScore) : "VS"; horizontalAlignment:Text.AlignHCenter; maximumLineCount:1 }
        Label { x:591; y:17; width:285; height:56; themeStyle:root.style; size:30; font.weight:Font.DemiBold; text:root.match ? root.match.away.name : ""; horizontalAlignment:Text.AlignHCenter; maximumLineCount:1 }
        Label { x:20; y:83; width:856; height:32; themeStyle:root.style; size:20; secondary:true; text:root.match ? [root.match.whenText,Format.matchStatus(root.match),root.match.pendingVAR ? "VAR" : ""].filter(Boolean).join(" · ") : ""; horizontalAlignment:Text.AlignHCenter; maximumLineCount:1 }
    }
    Rows { x:32; y:276; width:896; height:Math.max(1,root.height-y-48); context:root.context; compact:true; offsetMode:!root.fantasy; visible:root.tab === "RIEPILOGO" || root.fantasy; rows:{ root.context.dataRevision; return root.fantasy ? Format.fantasyPlayers(root.fantasyTeam) : Format.matchRows(root.context) }
 emptyText:root.fantasy ? root.context.fantasy && root.context.fantasy.loading ? "Caricamento voti" : "Voti non disponibili" : root.match && root.match.status === "scheduled" ? "Dettagli disponibili dopo il calcio d’inizio" : root.match && root.match.homeScore.available && root.match.awayScore.available && root.match.homeScore.value === 0 && root.match.awayScore.value === 0 ? "Nessun gol nella partita" : "Marcatori non disponibili dalla fonte" }
    Flickable { id:statisticsScroll; objectName:"statisticsScroll"; x:32; y:276; width:896; height:Math.max(1,root.height-y-48); clip:true; contentHeight:statisticsGrid.height; contentY:Math.max(0,Math.min(Math.floor(root.context.selection.index/2)*84,contentHeight-height)); boundsBehavior:Flickable.StopAtBounds; visible:root.tab === "STATISTICHE"
      Grid { id:statisticsGrid; columns:2; spacing:12
        Repeater { model:root.match ? root.match.statistics : null
            delegate: Card { id:statisticCard; required property var item; width:442; height:72; style:root.style
                Label { x:16; y:8; width:240; height:56; themeStyle:root.style; size:20; text:statisticCard.item.label; maximumLineCount:2 }
                Label { x:260; y:8; width:166; height:56; themeStyle:root.style; size:24; text:Format.number(statisticCard.item.home) + " / " + Format.number(statisticCard.item.away); horizontalAlignment:Text.AlignRight; maximumLineCount:1 }
            }
        }
      }
    }
    Row { x:32; y:132; spacing:16; visible:root.tab === "FORMAZIONI"
        Repeater { model:root.match ? root.match.lineups : null
            delegate: Card { id:lineupCard; required property var item; width:440; height:Math.max(1,root.height-180); style:root.style
                Label { x:16; y:8; width:408; height:35; themeStyle:root.style; size:20; font.weight:Font.DemiBold; text:(lineupCard.item.teamId === root.match.home.id || lineupCard.item.teamId === "home" ? root.match.home.name : root.match.away.name) + " · " + lineupCard.item.formation; maximumLineCount:1 }
                Flickable { x:16; y:49; width:408; height:parent.height-y-16; contentHeight:roster.height; contentY:Math.max(0,Math.min(root.context.selection.index*26,contentHeight-height)); clip:true; boundsBehavior:Flickable.StopAtBounds
                    Column { id:roster; width:parent.width
                        Repeater { model:lineupCard.item.players; delegate: Label { required property var item; width:408; height:26; themeStyle:root.style; size:18; text:Format.number(item.shirtNumber) + "  " + item.name; maximumLineCount:1 } }
                    }
                }
            }
        }
    }
    Label { x:32; y:parent.height-43; width:896; height:37; themeStyle:root.style; size:18; secondary:true; text:root.fantasy && root.context.fantasy ? [(root.fantasyTeam ? root.fantasyTeam.name : ""),root.context.fantasy.provisional ? "Voti provvisori" : "",root.context.fantasy.warning,root.context.fantasy.liveNotice,root.context.fantasy.cacheError,root.context.fantasy.message,Format.source(root.context.fantasy.source)].filter(Boolean).join(" · ") : [root.match ? root.match.detailError : "",root.context.detailOperation.status === "pending" ? "Caricamento dettagli" : "",Format.source(root.context.source)].filter(Boolean).join(" · "); maximumLineCount:1 }
    Label { x:32; y:285; width:896; height:215; themeStyle:root.style; size:26; secondary:true; text:root.tab === "FORMAZIONI" ? "Formazioni non disponibili dalla fonte" : "Statistiche non disponibili dalla fonte"; horizontalAlignment:Text.AlignHCenter; visible:root.match && (root.tab === "STATISTICHE" && root.match.statistics.count === 0 || root.tab === "FORMAZIONI" && root.match.lineups.count === 0) }
}
