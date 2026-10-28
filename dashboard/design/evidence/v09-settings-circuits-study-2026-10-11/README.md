# Evidenze di studio — impostazioni e circuiti

11 ottobre 2026. **Concept offline 960×640, non schermate runtime né qualifica board.**

- [Studio completo](../../game-settings-circuits-ux-study.md)
- [Sessione](sessione-concept.png), [Allenamento](allenamento-concept.png), [Avanzate](avanzate-concept.png)
- [Circuito tecnico](circuito-tecnico-concept.png)
- [Misure e limiti geometrici](geometry-study.json), [campioni della linea centrale](candidate-centerline.json)
- [Controlli degli artefatti](study-checks.json): link locali validi, quattro immagini 960×640, due direzioni di curva e intersezioni campionate riportate. Non sono test del runtime.
- [Script riproducibile](render_study.py): `python3 dashboard/design/evidence/v09-settings-circuits-study-2026-10-11/render_study.py` dalla radice del progetto; richiede NumPy/Pillow e legge i font/colori del bundle Apple Calm presente nel checkout.

Le verifiche geometriche riguardano incroci propri di segmenti campionati. Non verificano continuità analitica, tangenze, margini tra tratti, griglia, raggi sensori, fisica, apprendimento, rendering QML, prestazioni o input fisico. Il primo tracciato interpolato con Catmull-Rom è stato scartato per raggio interno insufficiente; la candidatura B-spline è una base da qualificare. Nessuna dipendenza è stata installata e nessun dato utente è stato modificato.
