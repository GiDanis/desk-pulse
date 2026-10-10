"""Design specification, not a runtime contract. No provider I/O."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
PRIMARY = [24, 120, 400, 504]
SMALL = [[440, 120, 240, 244], [696, 120, 240, 244], [440, 380, 240, 244], [696, 380, 240, 244]]
GRID = [[24, 120, 448, 244], [488, 120, 448, 244], [24, 380, 448, 244], [488, 380, 448, 244]]

def block(name, rect, value_px, content, availability='Dati esistenti; nuova selezione e composizione'):
    return dict(name=name, rect=rect, valuePx=value_px, labelPx=25, notePx=23, content=content, availability=availability)

def view(key, topic, name, question, layout, blocks, detail, rules):
    return dict(id=key, topic=topic, name=name, question=question, layout=layout, blocks=blocks, open5=detail, rules=rules)

def focus(key, topic, name, question, main, secondary, detail, rules, size=86):
    return view(key, topic, name, question, 'Principale e contesto', [block('Principale',PRIMARY,size,main)] + [block(label,SMALL[i],px,content,availability) for i,(label,px,content,availability) in enumerate(secondary)],detail,rules)

EXISTING='Dati esistenti; nuova selezione e composizione'
PROJECT='Nuova proiezione qualificata dei dati esistenti; contratto da definire'
VIEWS = [
    view('oggi-ora','Oggi','Ora','Che ora è e che cosa mi serve subito?','Ora e meteo affiancati',[
        block('Ora',[24,120,536,318],152,'HH:MM; data nell’identità vista','Orologio locale esistente'),
        block('Meteo',[576,120,360,504],80,'Condizione, temperatura, percepita e freschezza'),
        block('Evento facoltativo',[24,454,536,170],34,'Titolo e orario del prossimo evento qualificato','NextEvent esistente; non è un calendario personale'),
    ],'Dettaglio Oggi: evento pertinente e condizioni del giorno, con min/max e fonte', 'Ora resta dominante; evento solo se disponibile; nessuna scheda fittizia senza evento.'),
    view('oggi-orologio','Oggi','Orologio','Leggo l’ora rapidamente a distanza?','Orologio dominante',[
        block('Ora',[24,120,912,340],224,'HH:MM grande, senza secondi','Orologio locale esistente'),
        block('Meteo compatto',[24,476,448,148],36,'Temperatura, condizione e freschezza'),
        block('Evento facoltativo',[488,476,448,148],30,'Titolo e ora del prossimo evento qualificato'),
    ],'Stesso dettaglio Oggi della vista Ora','Nessuna costellazione di KPI; se manca evento, fascia meteo estesa. I 224 px sono un candidato da verificare.'),
    view('oggi-giornata','Oggi','Giornata','Qual è il prossimo appuntamento e come sarà oggi?','Evento e giornata',[
        block('Evento / oggi',PRIMARY,68,'Prossimo evento qualificato e orario; senza evento, condizioni di oggi'),
        block('Meteo oggi',[440,120,496,244],62,'Condizione e massima/minima del giorno'),
        block('Probabilità pioggia',[440,380,240,244],52,'Massimo giornaliero disponibile; periodo dichiarato'),
        block('Vento',[696,380,240,244],38,'Velocità e direzione correnti; periodo dichiarato'),
    ],'Dettaglio Oggi, centrato sull’evento; programma pertinente e condizioni complete', 'Non ripetere tre giorni di Previsioni; niente agenda personale o raccomandazioni inventate. Senza evento: meteo principale e contesto non duplicato.'),
    focus('meteo-adesso','Meteo','Adesso','Quali sono le condizioni adesso?','Condizione, temperatura, percepita; probabilità oraria se qualificata',[
        ('Vento',38,'Velocità e direzione',EXISTING),('Umidità',58,'Umidità relativa',EXISTING),
        ('Raffiche',38,'Velocità con periodo del provider',EXISTING),('Precipitazioni',42,'Millimetri con intervallo del dato; non probabilità',EXISTING),
    ],'Condizioni complete e fonte; allerte pertinenti solo se disponibili','Conservare la famiglia Meteo attuale; la quantità di precipitazione non diventa pioggia totale del giorno.'),
    view('meteo-previsioni','Meteo','Previsioni','Come cambiano i prossimi tre giorni?','Tre giorni confrontabili',[
        block(label,[24+i*(928/3),120,880/3,504],62,'Data, condizione, massima, minima e massimo giornaliero della probabilità di pioggia')
        for i,label in enumerate(['Oggi','Domani','Terzo giorno'])
    ],'Dettaglio del giorno selezionato: stessi dati con periodo e fonte espliciti', 'Tre colonne cronologiche, stesso ordine e scala tipografica. Serie orarie, UV e alba/tramonto non sono esposti dal DTO corrente.'),
    view('account-utilizzo','Account','Utilizzo','Quanto utilizzo ho consumato e quando si ripristina?','Finestre affiancate',[
        block('Finestra breve',[24,120,448,324],80,'Nome servizio, durata reale, percentuale utilizzata, barra 0–100 e reset'),
        block('Finestra lunga',[488,120,448,324],80,'Seconda finestra pertinente dello stesso servizio'),
        block('Crediti',[24,460,448,164],38,'Saldo riportato, illimitati o non disponibile'),
        block('Reset disponibili',[488,460,448,164],38,'Numero di reset credits riportato; distinto dagli orari di reset'),
    ],'Tutte le finestre, reset assoluto locale e stato della sincronizzazione', 'Una finestra valida occupa la larghezza completa; oltre due si aprono nei dettagli. Selezione stabile per servizio e durata, non ordinata continuamente per consumo.'),
    focus('sport-calcio','Sport','Calcio','C’è una partita in corso o quando si gioca?','Competizione, squadre, risultato o orario, fase e fonte',[
        ('Prossima',34,'Appuntamento successivo distinto dalla principale',PROJECT),('Squadra',62,'Posizione e punti della squadra/competizione scelta',PROJECT),
        ('Ultimo esito',48,'Risultato concluso e identità partita',PROJECT),('Altre partite',42,'Live qualificati, senza includere la principale',PROJECT),
    ],'Partita prioritaria e calendario pertinente; poi risultati e classifica', 'Live verificato della preferita → altro live pertinente → prossima preferita → prossima competizione → ultimo esito. Nessuna diretta dedotta dall’orario.'),
    focus('sport-f1','Sport','Formula 1','Quale sessione viene prima e come sta andando il GP?','GP/circuito, sessione prioritaria, orario locale o fase',[
        ('Successiva',34,'Sessione seguente distinta dalla principale',PROJECT),('Prossimo GP',33,'GP successivo, circuito e data',PROJECT),
        ('Ultima sessione',34,'Risultato con nome pilota e sessione',PROJECT),('Mondiale',44,'Pilota di interesse o leader, punti e stagione',PROJECT),
    ],'Weekend già informativo: sessioni, risultati, timing qualificato, classifica', 'Selezionare la sessione, non solo l’inizio del GP. Al prossimo GP non assegnare il nome del GP corrente.'),
    focus('sport-motogp','Sport','MotoGP','C’è una sessione qualificata live o quale viene dopo?','GP/classe, sessione, giro o orario e stato qualificato',[
        ('In testa',34,'Leader se timing corrente; altrimenti ultimo vincitore esplicito',PROJECT),('Distacco',46,'Distacco qualificato; senza timing: prossimo appuntamento',PROJECT),
        ('Ultima sessione',42,'Sprint/gara con classe e data',PROJECT),('Mondiale',34,'Classifica della stagione e classe pertinente',PROJECT),
    ],'Weekend e sessioni, risultati, classifica; timing solo se qualificato', 'Distinguere classi, sprint/gara e gara/mondiale. La variante senza live mantiene struttura e cambia etichette esplicitamente.'),
    view('casa-preferiti','Casa','Preferiti','Qual è lo stato dei dispositivi che mi interessano?','Mosaico 2×2',[
        block('Preferito '+str(i+1),GRID[i],[58,52,58,34][i],'Nome, stato/misura principale, attributo secondario e freschezza locale') for i in range(4)
    ],'Preferiti estesi con focus e dettaglio del dispositivo', 'Ordine scelto dall’utente; nessun comando ON/OFF. Uno o due preferiti usano schede più larghe, senza riquadri vuoti.'),
    focus('casa-ambiente','Casa','Ambiente','Quali letture ambientali sono disponibili?','Sensore prioritario nominato, misura, unità e tempo',[
        ('Umidità',58,'Stesso sensore della principale se supportato',PROJECT),('Altro sensore',58,'Nome e temperatura di un altro dispositivo',PROJECT),
        ('Movimento',31,'Stato del sensore con ultima osservazione',PROJECT),('Copertura',62,'Numero di sensori con lettura corrente',PROJECT),
    ],'Misure complete dei sensori, disponibilità e timestamp', 'Vista condizionale ai codici supportati. Nessuna media tra stanze, punteggio comfort o storico ricostruito.'),
    focus('casa-dispositivi','Casa','Dispositivi','Che cosa compare nel mio catalogo Casa?','Conteggio del catalogo, disponibili secondo cloud / precedenti',[
        ('Preferiti',62,'Numero scelto dall’utente',EXISTING),('Luci',62,'Categoria solo se normalizzata in modo affidabile',PROJECT),
        ('Prese',62,'Categoria qualificata, senza dedurla dal nome',PROJECT),('Sensori',62,'Categoria qualificata, senza doppio conteggio',PROJECT),
    ],'Inventario selezionabile, dispositivo, attributi e provenienza', 'In assenza di categorie affidabili usare due riepiloghi utili di disponibilità e preferiti; conteggio cloud non equivale a presenza in rete.'),
    view('rete-traffico','Rete','Traffico','Quanto traffico WAN c’è e come varia?','Valori e andamento',[
        block('Download / upload',PRIMARY,86,'Velocità WAN aggregate, unità e timestamp per misura'),
        block('Andamento',[440,120,496,244],22,'Ultima ora qualificata, download/upload, assi e buchi dello storico','Storico esistente; finestra e disponibilità da qualificare'),
        block('Stato WAN',[440,380,240,244],42,'Stato riportato dalla box'),
        block('Capacità box',[696,380,240,244],38,'Valore riportato, con unità e provenienza; non speed test'),
    ],'Storico WAN esteso e scelta periodo, con campioni/tempi qualificati', 'Upload deve restare leggibile come numero: sulla stessa scala del download può risultare quasi piatto. Nei dettagli due grafici allineati con scale esplicite.'),
    focus('rete-iliadbox','Rete','iliadbox','La box è operativa e quali stati riporta?','Stato WAN dominante; uptime e ultimo aggiornamento di contesto',[
        ('Sensore box',56,'Temperatura del sensore nominato, non della board',EXISTING),('Wi-Fi',43,'Radio riportate; non conteggio implicito dei client',EXISTING),
        ('Ethernet',43,'Porte e stato link riportato',EXISTING),('Firmware',34,'Versione esatta, con nome lungo gestito nei dettagli',EXISTING),
    ],'Stato/sensori del router, sezioni Wi-Fi e Porte', 'Cambiare gerarchia rispetto alla tavola preliminare: Attiva/Non disponibile prima dei 2 giorni di uptime. Box e Orange Pi devono restare identificabili.',size=68),
    focus('rete-dispositivi','Rete','Dispositivi','Quanti record vedo e quali sono raggiungibili secondo box?','Record inventario, conteggio qualificato e copertura parziale',[
        ('Preferito 1',30,'Nome e stato secondo box; osservazione corrente/precedente',EXISTING),('Preferito 2',29,'Identità distinta; non raggiungibile non equivale a spento',EXISTING),
        ('Preferito 3',30,'Nome e osservazione',EXISTING),('Preferito 4',32,'Nome e freschezza locale',EXISTING),
    ],'Inventario completo con filtro esplicito; dettaglio identità/indirizzi/osservazioni', 'Quattro preferiti solo se scelti e presenti; niente velocità per host dedotta dalla WAN o presenza assoluta da record storici.'),
]

if __name__=='__main__':
    output=dict(scope='Design proposal only; not an implemented Theme API contract',canvas=[960,640],toolbarPx=56,bodyRect=[24,120,912,504],gutterPx=16,views=VIEWS)
    (HERE/'view-organization.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    assert len(VIEWS)==15 and len({v['id'] for v in VIEWS})==15
    for v in VIEWS:
        for b in v['blocks']:
            x,y,w,h=b['rect'];assert x>=24 and y>=120 and x+w<=936.001 and y+h<=624
    print(json.dumps({'views':len(VIEWS),'topics':len({v['topic'] for v in VIEWS}),'blocks':sum(len(v['blocks']) for v in VIEWS)}))
