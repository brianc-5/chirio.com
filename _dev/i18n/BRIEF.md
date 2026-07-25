# Translation brief — Chirio.com, Italian → English

You are translating strings from a personal Italian technical archive by Roberto
Chirio: electronics, radio and antennas, power supplies, batteries, LED
lighting, Geiger counters, laboratory measurements, plus a historical section on
an Italian alpine fort (the Chaberton battery).

The reader is a hobbyist or engineer. Aim for clear, plain technical English —
the register of a well-written build log, not marketing copy and not a stiff
literal gloss.

## Hard rules

1. **Return exactly the same keys you were given.** Same number of items, same
   key strings. Never merge, split, reorder, add or drop an item.
2. **Never change a number, a unit, a tolerance or a part number.** `5mA`,
   `9V`, `10 kHz – 30 MHz`, `2N3819`, `BC547`, `IC-R20`, `149/35`, `2900mAh`
   stay exactly as written, including spacing and case.
3. **Never translate** file names (`005.JPG`, `schema.pdf`), URLs, e-mail
   addresses, or brand and product names (Parkside, Eneloop, MagicShine, Seoul
   P7, Wandel & Goltermann, ICOM, Yaesu, Arduino, LIDL).
4. **Never translate proper nouns**: Roberto Chirio, Chaberton, Briançon,
   Cesana, Sestriere, Claviere, Valle di Susa, Petit Vallon, Exilles, Monte
   Chaberton, Sacra di San Michele.
5. Keep any HTML entity or special character that appears (`&nbsp;`, `→`, `°`,
   `±`, `Ω`, `µ`) exactly as it is.
6. If a string is already English, or is a bare label with no Italian in it,
   return it unchanged.
7. Preserve the author's voice, including his informal asides and ellipses
   (`.....`). Do not tidy his opinions, do not add hedging, do not add
   information that is not there.

## Glossary — use these consistently

| Italian | English |
| --- | --- |
| alimentatore | power supply |
| alimentare | to power / to supply |
| assorbimento | current draw |
| autonomia (di batteria) | runtime |
| avvolgimento | winding |
| basetta / scheda | board |
| carico elettronico | electronic load |
| caricabatterie | battery charger |
| circuito stampato | printed circuit board (PCB) |
| collegamento a terra | ground connection |
| condensatore | capacitor |
| contatore Geiger | Geiger counter |
| corrente | current |
| fondo (radiazioni) | background radiation |
| illuminamento | illuminance |
| lampada | lamp |
| misura / misure | measurement / measurements |
| pacco batteria | battery pack |
| piastra | plate |
| pila / stilo (AA) | AA cell |
| presa | socket |
| prova / prove | test / tests |
| raddrizzatore | rectifier |
| resistenza (componente) | resistor |
| ricevitore | receiver |
| rilevatore | detector |
| saldatura | soldering |
| schema elettrico | circuit diagram |
| sonda | probe |
| stagno (aggettivo) | waterproof |
| tensione | voltage |
| torcia | torch |
| trasformatore | transformer |
| banda passante | bandwidth |
| onde corte | shortwave |
| radioamatori | radio amateurs |
| ascolto | listening / reception |
| fortificazione | fortification |
| teleferica | cable car / aerial ropeway |
| spalti | ramparts |
| postazione | emplacement |
| ricovero | shelter |
| galleria / tunnel | tunnel |

## Output format

Write a JSON object with the **same keys** as the input and the English string
as each value. No commentary, no code fences in the file, nothing else.

```
{"1": "English for item 1", "2": "English for item 2", ...}
```
