# Pc_Inspector
For check every settings in windows pc. You can check difference betwen two pc (PCA and PCB).

PC Inspector & Comparator
=========================

App per scansionare l'hardware e le impostazioni di un PC Windows
e confrontarle con un altro PC.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REQUISITI
---------
- Python 3.8+ per Windows  →  https://www.python.org/downloads/
- Libreria psutil (installazione automatica con installa.bat)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTALLAZIONE RAPIDA
--------------------
1. Assicurati di avere Python installato
2. Fai doppio clic su  "installa_e_avvia.bat"
   → installa psutil automaticamente
   → avvia l'app

In alternativa, da terminale:
  pip install psutil
  python pc_inspector.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UTILIZZO - Flusso tipico
-------------------------

  PC 1:
  1. Apri l'app su PC 1
  2. Scheda "Scansiona PC" → clicca "Scansiona questo PC"
  3. Clicca "Salva JSON"  → salva il file (es. scan_PC1.json)
  4. Porta il file sull'altro PC (USB, rete, cloud)

  PC 2:
  1. Apri l'app su PC 2
  2. Scheda "Scansiona PC" → clicca "Scansiona questo PC"
  3. Clicca "Salva JSON"  → salva (es. scan_PC2.json)

  Confronto (su qualsiasi PC):
  1. Scheda "Confronta PC"
  2. "PC A → Carica"  →  seleziona scan_PC1.json
  3. "PC B → Carica"  →  seleziona scan_PC2.json
  4. Clicca "Confronta!"
  5. Usa i filtri: "Solo differenze" per vedere solo cosa cambia

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COLORI NEL CONFRONTO
--------------------
  Verde  →  Valore identico su entrambi i PC
  Rosso  →  Valore diverso
  Giallo →  Presente solo su uno dei due PC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
