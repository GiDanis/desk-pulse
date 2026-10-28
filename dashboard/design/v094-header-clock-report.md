# Dashboard Orange Pi v0.9.4 — orario nella barra e luminosità uniforme

## Ambito

Due correzioni richieste il 22 ottobre 2026: HH:mm sempre visibile nella barra di ogni argomento; oscuramento della barra insieme al resto dell’interfaccia. Core 0.9.4-rc.1, Apple Calm 1.6.4, Theme API 2.12. Nessuna modifica ai provider, al Gioco o alla ricetta di apprendimento.

## Implementazione

- `Main.qml`: orario della barra Base/Functional e fallback collegato a `timeText()`; spazio del titolo ridotto per riservare il lato destro. Il contatore della vecchia barra lascia posto all’ora.
- `ShellContext.clock`: campo opzionale `ClockState`, pubblicato dal payload della shell attraverso l’adattatore esistente. Tipi e riferimento generati, fingerprint del corpus aggiornato; import precedenti compatibili.
- `Shell.qml` Apple Calm: HH:mm nella barra di 56 px, a destra con 24 px di margine. Quiete/Ripristino restano nello stesso settore sotto l’ora quando presenti; badge e disciplina conservano le proprie aree.
- `dimmingLayer`: livello esplicito 30, sopra shell (2), avvisi (3/4) e caricamento/scelta tema (20/21). Un solo filtro oscura uniformemente tutta la GUI, senza alterare input e priorità degli avvisi.
- Palette notte, luminosità automatica/manuale e fascia silenziosa restano impostazioni distinte. Conservati font, palette, icone e geometria del contenuto.

## Verifiche e consegna

Evidenze in [v094-header-clock-2026-10-22](evidence/v094-header-clock-2026-10-22/). **Installata il 22 ottobre 2026:** core 0.9.4-rc.1, 648 file verificati; Apple Calm 1.6.4 attivo, digest `d67dccb9bf336273afa9f9cd1b2c23bc9fbe2947f04274f9dfa97a2ac56e0e28`. [Ricevuta finale](evidence/v094-header-clock-2026-10-22/board/final-receipt.json).

- PC: 30 test contratto superati e una esclusione dichiarata; 40 test API runtime, 68 superfici dell’adattatore, matrice Apple da 1.098 casi senza warning. Tre temi, 30 combinazioni di navigazione ciascuno.
- ARM: 39 test API runtime superati; un controllo qmllint escluso perché il binario non è presente sulla board. Il primo tentativo fallito per tale requisito è conservato; il controllo completo del lint è passato sul PC. Nessun pacchetto di sistema installato.
- EGLFS/KMS nativo 960×640: Base, Functional e Apple, 90 combinazioni complessive; cambio 23:59→00:00, palette giorno/notte, luminosità manuale 50%/20% e automatica giorno/notte. Rapporti e catture in `board/`; confronto pixel con tolleranza di due livelli RGB per intestazione e contenuto. Nessun warning QML.
- Apple: approfondimenti Menu/Impostazioni/Informazioni/Avvisi, ritorno Home e permanenza effettiva del tema salvato; Quiete e badge senza sovrapposizione. I primi tentativi del nuovo test hanno rilevato errori del fixture (anteprima annullata da Home, attesa del primo frame e nome scenario), corretti prima del collaudo nativo.
- Kit AI rigenerato sul contratto 2.12, [archivio](evidence/v094-header-clock-2026-10-22/smartpc-theme-ai-kit-2.12.zip).

Il runtime è stato confrontato con la 0.9.3-rc.2 installata: modifiche limitate alla barra, al contratto, ai test e alla documentazione. Libreria numerica ARM identica, nessuna modifica al Gioco. Attivazione Apple attraverso Main/ThemeService reali con primo frame e salvataggio, conservando tutte le opzioni dell’aspetto tranne l’identità della revisione.

GUI pronta con PID corrente e heartbeat fresco; servizio active/running e NRestarts=0; pending nullo. Intero database Gioco e 214 artefatti personali invariati, preferenze non grafiche e opzioni grafiche conservate. Backup `/var/lib/smartpc-dashboard/v094-backups/20261022-183733`; runtime precedente `/opt/smartpc/dashboard-before-v094-20261022-183733`. Nessun reboot OS; candidato non promosso a stabile dal solo controllo mirato. Le catture software verificano il rendering, non la leggibilità fisica a distanza.
