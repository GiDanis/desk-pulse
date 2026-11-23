pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.2
import "Format.js" as Format

Panel {
    required property CasaContext context
    ctx:context
    title:"Casa · Smart Life"
    subtitle:context.description
    rows:Format.settings(context.rows)
    footer:[context.feedback || context.casa.modeText,context.casa.quotaConfigured ? "Richieste " + context.casa.requests + " · margine " + context.casa.remaining : "Quota continuativa da configurare"].filter(Boolean).join(" · ")
    rowAction:"settings.activate"
}
