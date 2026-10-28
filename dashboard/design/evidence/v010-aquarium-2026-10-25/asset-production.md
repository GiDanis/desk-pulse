# Produzione asset Calm

25 ottobre 2026. Strumento: imagegen integrato (skill imagegen), nessun fallback API/CLI.
Asset salvati nel progetto in dashboard/assets/aquarium/calm-v1.

Prompt fondale: illustrazione Calm 2D morbida e originale, vista frontale fissa,
acqua teal/navy, sabbia nell'ultimo 20%, rocce/piante essenziali ai lati,
centro e parte superiore aperti. Nessun pesce, testo, UI, cornice o effetto glow.
Output opaco 1536×1024, renderizzato a 960×640 con sourceSize appropriato.

Prompt gold: atlante trasparente con quattro quadranti uguali: corpo laterale
senza coda/pinna pettorale; riferimento assemblato; coda con attacco a destra;
pinna separata. Pesce originale oro/albicocca, ventre crema, occhio leggibile,
illustrazione morbida con silhouette pulita, nessuno sfondo/testo/etichetta.

Prompt teal: stessa struttura tecnica, specie originale più affusolata blu/teal,
ventre crema e accenti gialli discreti, anatomia coerente fra parti/riferimento.

Gli atlanti effettivi sono 1254×1254 RGBA con alpha reale (estremi 0/255),
non 1280 o la dimensione nominale richiesta. Catalogo e rettangoli sono
calibrati ai file reali; nessun ritaglio generativo supposto esatto.
Le giunzioni/pivot sono parametri del rig. Le sprite sheet 3072×512 a16 pose
sono esportazioni deterministiche dello stesso QML FishRig tramite
scripts/bake-aquarium-sprites.py, non una seconda identità generata.

Verifica sorgenti: alpha, dimensioni e hash; verifica visiva nella Main a960×640.
Le virate sono raccordi di traiettoria e orientamento con compressione laterale
progressiva; non sono un modello3D o una promessa di anatomia biologica.
Il confronto rig/sprite e le misure native sono conservati nei report; la
qualità resta valutabile anche dalle catture, senza una falsa approvazione umana.

Correzione export del26 ottobre: il grab della Window nel backend software
appiattiva l’alpha. Le sheet finali provengono dal grabToImage dell’Item,
con alpha reale0–255 e cornici trasparenti su tutti i16 frame. Ogni frame
misura384×256 e contiene il rig250×160 con padding, compensato nel renderer
per conservare la scala del rig. Nessun ritaglio di pinne o coda ai bordi.
Il contenimento usa un raggio conservativo0,95×larghezza: i bounding box
alpha delle parti, ruotati sull'intero intervallo di pinna/coda, hanno raggio
massimo circa0,785 per teal e0,885 per gold. La rotazione del corpo preserva
il raggio e la compressione della virata non lo aumenta. Due regressioni
sugli asset e un controllo nella Main verificano alpha, bordi e safeArea.
I primi confronti sprite opachi rimangono soltanto evidenze di sviluppo,
non confronti equivalenti validi per la scelta prestazionale finale.
