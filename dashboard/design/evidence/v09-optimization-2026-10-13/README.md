# Ottimizzazione rc.10 · 13 ottobre 2026

- `before/`: sorgenti immutabili usati per i confronti numerici con rc.9; `before-source.json` ne registra gli hash.
- `release-regression.txt`: 64 controlli PC, inclusi sei gate numerici/replay di ottimizzazione. Il primo tentativo `cache-regression.txt` ha incontrato quota /tmp; il seguito usa temporanei su disco.
- `first-board.json`, `reference-board.json`, `paced-board.json`: campioni CPU privati concorrenti alla Home, codice candidato. Non sono FPS della pista QML. `paced-board.json` è la variante scelta.
- `pool-board.json`: collector a due processi, non selezionato come default dopo il confronto sfavorevole.
- `board/`: backup, checkpoint reali provati su copie, sette verifiche native, griglie multigiro e ricevuta. Artefatti delle NPU nei sottopercorsi `board/npu/`.
- `npu/`: esportazione ONNX, modelli NBG compilati, metadata e ingressi; una sola policy congelata 68→16→2. I log iniziali con errori SDK non sono prove di parità; la scelta usa i tre binari finali con 512 batch ciascuno.

Gli script di prova non fanno parte dell'app distribuita. La directory `fixtures/theme-runtime/renderers` e i sorgenti di confronto sono aggiunti solo alla cartella di prova board; l'installatore copia esclusivamente gli hash del manifest. Durata dei campioni, distribuzione dei metodi e casi in cui non c'è beneficio restano espliciti nel report.
