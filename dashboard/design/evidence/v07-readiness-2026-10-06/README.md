# v0.7 · evidenze della revisione del 6 ottobre 2026

Verifica di analisi in sola lettura. Nessun comando ai dispositivi, nessuna installazione o riavvio del kiosk, nessun trasferimento di credenziali. [Decisione e piano aggiornato](../../v07-implementation-readiness.md).

## Codice e baseline

- HEAD locale osservato: `df4d7c1`; versione installata sulla board: `0.6.6`.
- Il workspace aveva già modifiche a `Main.qml`, `check_theme_api_adapters.py`, `components/NotificationHost.qml`, `theme_api.py`, `theme_bundle_tools.py`, `theme_runtime.py` e la cartella non tracciata `theme-projects/`. Preservate; non attribuite a Casa.
- `python3 dashboard/check_tuya.py`: **22 test, OK**, eseguiti sul PC. Nessuna prova Qt o Tuya live sulla board in questa revisione.
- Client attuale: inventario generale con cursore; risposta cumulativa e scheduler ancora non implementati nel runtime.

## Cloud reale

Acquisizione iniziata alle **2026-10-06 08:21:24 UTC** (10:21:24 Europe/Rome). File privato letto mediante `load_config`; token mantenuto soltanto nella memoria del processo temporaneo. Endpoint: `https://openapi.tuyaeu.com`.

| Richiesta | Numero | Riscontro |
| --- | ---: | --- |
| GET `/v1.0/token?grant_type=1` | 1 | Autenticazione riuscita |
| GET `/v1.0/users/{uid}/devices?page_no=1&page_size=50` | 1 | Lista di 16 dispositivi; 16 identità distinte |
| GET `/v1.0/users/{uid}/devices`, pagine 1 e 2, `page_size=1` | 2 | Una riga per pagina; identità diverse |
| GET `/v1.2/iot-03/devices/{id}/specification` | 4 | Specifiche dei quattro campioni leggibili |
| **Totale `CloudClient.request_count`** | **8** | Nessun retry necessario |

Tutti i valori del campione derivano dagli stati inclusi nella lettura cumulativa, normalizzati mediante `normalize_status` con le rispettive specifiche. Non sono state richieste quattro GET aggiuntive dello stato.

Riepilogo inventario: **7 online**, **9 offline**, **0 disponibilità sconosciute**; **10 dispositivi con lista stati non vuota**, **83 campi complessivi**; per sei dispositivi la proprietà lista stati non è disponibile. I parametri pagina sono stati provati, ma non è stata percorsa l'intera lista con dimensione 1.

| Campione | Disponibilità secondo Tuya | Ultimo valore riportato |
| --- | --- | --- |
| T & H Sensor | Online | 26,0 °C; 55% umidità; 21% batteria |
| Zigbee Plug | Offline | `switch_1=true`; potenza 48 W; corrente 201 mA; tensione 239 V |
| Lampada scrivania | Offline | `switch_led=true`; modalità `white` |
| Sensore di movimento | Offline | `pir=pir`; batteria 81% |

Questi sono dati letti dal cloud, non misure fisiche effettuate durante il controllo. In particolare `pir=pir` su dispositivo offline non dimostra movimento o presenza attuale. Luminosità senza unità, bitmap e campi strutturati non sono stati tradotti arbitrariamente.

Non sono stati salvati payload grezzi, ID, UID, token, local key, indirizzi privati o coordinate in questa evidenza. Non è stata aggiornata la cache dell'inventario del probe: le risposte sono rimaste in RAM e qui viene conservato solo il riepilogo scelto.

## Board

Verifica SSH di `systemctl show smartpc-dashboard` e lettura di `version.py`:

```text
NRestarts=0
ActiveState=active
SubState=running
VERSION = '0.6.6'
```

Questo riscontro non include un nuovo reboot, test grafico, prova del tastierino, misura prestazionale o acquisizione cloud sulla board.

## Documentazione esterna ricontrollata

- [Inventario Smart Home](https://developer.tuya.com/en/docs/cloud/ad2823ae46?id=Kconjtzq1vk1q): lista dispositivi con `online` e `status`; parametri pagina/dimensione; nessun totale documentato. Il testo dei parametri dice prima pagina 1, mentre un esempio riporta 0: usato e verificato 1 sul progetto.
- [Pricing](https://developer.tuya.com/en/docs/iot/membership-service?id=K9m8k45jwvg9j): pagina aggiornata 28 luglio 2026, 26.000 API/mese e 68.000 messaggi come riferimento Trial; allocazione esemplificativa 50/50 fuori dalla Cina, modificabile. Sospensione al raggiungimento della quota. La pagina è stata letta usando il collegamento ufficiale indicizzato dopo timeout del percorso senza parametri aggiuntivi.

Quota effettiva, saldo e scadenza non sono stati letti dalla console privata. Rinnovo token reale, protocollo Wi-Fi/Zigbee e 22 test simulati sulla board sono evidenze storiche del 1 ottobre e non vengono attribuiti a questa revisione.
