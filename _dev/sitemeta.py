# -*- coding: utf-8 -*-
"""Editorial metadata for the Chirio.com rebuild.

Everything in this file is a *navigation / classification* decision taken by
hand from the original content inventory.  No page text is stored here: titles
and descriptions used on the pages themselves are always read from the source
HTML at build time.  The short index blurbs below are drawn from the original
page titles / meta descriptions.
"""

# ---------------------------------------------------------------- main site --
# Section order == order on the homepage and in the primary navigation.
# Each entry: (slug, nav label, homepage heading, short section description)
SECTIONS = [
    ("radio", "Radio & antenne", "Radio Corner — antenne e radiofrequenza",
     "Antenne attive e filari, generatori e oscillatori RF, misure di campo, "
     "trasmettitori sperimentali e sensori."),
    ("alimentatori", "Alimentatori", "Alimentatori e convertitori",
     "Alimentatori switching da laboratorio, conversioni ATX, step-up, "
     "push-pull e carichi elettronici."),
    ("batterie", "Batterie & energia", "Batterie, accumulatori ed energia",
     "Prove di capacità e autonomia, caricabatterie, BMS, pacchi batteria, "
     "risparmio energetico e mobilità elettrica."),
    ("led", "LED & illuminazione", "LED e illuminazione",
     "Teoria e pratica dei LED di potenza: torce, proiettori, lampade, dimmer "
     "e prove comparative di illuminamento."),
    ("radioattivita", "Radioattività", "Contatori Geiger e radioattività",
     "Contatori Geiger, elettronica di lettura, alta tensione, calibrazione e "
     "monitoraggio ambientale."),
    ("misure", "Misure & laboratorio", "Misure, strumenti e laboratorio",
     "Strumenti di misura autocostruiti, tecniche di laboratorio e fondamenti "
     "di elettrotecnica."),
    ("progetti", "Foto & progetti", "Fotografia, meccanica e altri progetti",
     "Accessori fotografici, stampa 3D e realizzazioni meccaniche varie."),
]

# page file name -> section slug
PAGE_SECTION = {
    # --- radio & antenne
    "mini_whip.htm": "radio",
    "mini_whip_sdr.htm": "radio",
    "mini_whip_sdr_p.htm": "radio",
    "mini_whip_tricks_and_tips.htm": "radio",
    "mini_loop.htm": "radio",
    "antenna_40m.htm": "radio",
    "yagi_pmr.htm": "radio",
    "rf_gen_2014.htm": "radio",
    "rf_gen_2018.htm": "radio",
    "rf_gen_VHF.htm": "radio",
    "vfo_gen_2015.htm": "radio",
    "tunnel_generator.htm": "radio",
    "rf_field_meter.htm": "radio",
    "attenuator_20dbm.htm": "radio",
    "fm_spy_bug.htm": "radio",
    "433Mhz_sensor.htm": "radio",
    "drone_jammer.htm": "radio",
    # --- alimentatori
    "switching_power_supply_atx.htm": "alimentatori",
    "power_supply_12v_30A.htm": "alimentatori",
    "atx_14_volt.htm": "alimentatori",
    "step_up_10a.htm": "alimentatori",
    "push_pull_20_16.htm": "alimentatori",
    "electronic_load.htm": "alimentatori",
    # --- batterie & energia
    "battery_test.htm": "batterie",
    "nimh_battery_charger.htm": "batterie",
    "lipo_battery_charger.htm": "batterie",
    "parkside_battery_pack.htm": "batterie",
    "ebike_test_batterie.htm": "batterie",
    "ebike_extra_pack.htm": "batterie",
    "electric_bike_bms.htm": "batterie",
    "auto_elettrica.htm": "batterie",
    "home_save_energy.htm": "batterie",
    "solare_termico_centralina.htm": "batterie",
    "luci_auto.htm": "batterie",
    "luci_auto_2.htm": "batterie",
    # --- LED
    "led_light_emitting_diodes.htm": "led",
    "led_s.htm": "led",
    "led_1_battery_AAA_.htm": "led",
    "led_6_220V.htm": "led",
    "led_h4.htm": "led",
    "led_acquario.htm": "led",
    "led_bk3_s.htm": "led",
    "led_dimmer_rgb.htm": "led",
    "led_lamp_10w.htm": "led",
    "led_video_3p7.htm": "led",
    "led_seoul_zp4_mtb_3.htm": "led",
    "led_torcia_sub_03.htm": "led",
    "led_torcia_sub_p7.htm": "led",
    "led_test.htm": "led",
    "test_magicshine.htm": "led",
    # --- radioattività
    "geiger_counter.htm": "radioattivita",
    "geiger_arduino.htm": "radioattivita",
    "geiger_counter_pulsar.htm": "radioattivita",
    "geiger_counter_voltmeter.htm": "radioattivita",
    "ram63.htm": "radioattivita",
    "SV500.htm": "radioattivita",
    # --- misure & laboratorio
    "legge_di_ohm.htm": "misure",
    "lux_meter.htm": "misure",
    "bromografo_uv.htm": "misure",
    "cmos_cleaning.htm": "misure",
    # --- foto & progetti
    "flash_macro.htm": "progetti",
    "monopiede_1.htm": "progetti",
    "steady_cam_simple.htm": "progetti",
    "printer_3d.htm": "progetti",
    "jeep_perego.htm": "progetti",
    "mtb_gomme_chiodate.htm": "progetti",
}

LEGAL_PAGES = ["chirio_com_privacy.htm", "chirio_com_disclaimer.htm"]

# Short, neutral index labels. Taken from the original homepage link text and
# page titles; not new editorial claims.
INDEX_LABEL = {
    "mini_whip.htm": ("Mini Whip — antenna attiva HF/VLF", "10 kHz – 30 MHz, antenna attiva capacitiva"),
    "mini_whip_sdr.htm": ("Mini Whip SDR — antenna attiva", "Versione per ricevitori SDR, base fissa"),
    "mini_whip_sdr_p.htm": ("Mini Whip SDR+ — antenna attiva", "Versione SDR+ per banda HF e VLF"),
    "mini_whip_tricks_and_tips.htm": ("Mini Whip — tricks & tips", "Consigli per montare la MiniWhip e ridurre i disturbi"),
    "mini_loop.htm": ("Mini Loop — antenna attiva", "Antenna a loop attiva 10 kHz – 30 MHz"),
    "antenna_40m.htm": ("Antenna filare 40 mt band", "Dipolo per la banda dei 40 mt"),
    "yagi_pmr.htm": ("Antenna Yagi PMR", "Yagi per banda PMR 446 MHz"),
    "rf_gen_2014.htm": ("RF Oscillator — generatore 20 MHz – 4 GHz", "Harmonic comb generator"),
    "rf_gen_2018.htm": ("Generatore RF 2700 MHz", "2700 MHz generator, microonde 2018"),
    "rf_gen_VHF.htm": ("VHF generator 70–500 MHz", "Oscillatore per VHF/UHF"),
    "vfo_gen_2015.htm": ("RF VFO Oscillator a 2 FET", "Oscillatore variabile per banda HF"),
    "tunnel_generator.htm": ("Effetto tunnel — generatore microonde", "Generatore 1000–4000 MHz a diodo tunnel"),
    "rf_field_meter.htm": ("RF field meter a LED", "Rilevatore di campo a radiofrequenza"),
    "attenuator_20dbm.htm": ("Attenuatore variabile −20 dBm", "10 kHz – 3000 MHz"),
    "fm_spy_bug.htm": ("Spy Bug FM Transmitter", "Microtrasmettitori FM a transistor, spie"),
    "433Mhz_sensor.htm": ("Sensori 433 MHz sensor wireless", "Come aumentare la distanza di collegamento"),
    "drone_jammer.htm": ("Anti drone / drone jammer", "Rilevazione e disturbo dei radiocomandi"),
    "switching_power_supply_atx.htm": ("ATX lab power supply", "Alimentatore da laboratorio da un ATX"),
    "power_supply_12v_30A.htm": ("Alimentatore ATX 12 V 30 A", "Conversione ATX per uso da banco"),
    "atx_14_volt.htm": ("ATX 13.8V power supply", "Modifiche per aumentare la tensione d'uscita"),
    "step_up_10a.htm": ("Step-up 10A 16V", "Convertitore switching elevatore 12 V"),
    "push_pull_20_16.htm": ("Push-pull DC-DC 12V 20A 16V 250W", "Anche 12V 40+40V 400W: electronics design"),
    "electronic_load.htm": ("Electronic Load 20A 40V", "Carico elettronico fino a 400 W"),
    "battery_test.htm": ("Come testare l'autonomia delle batterie Ni-Mh", "Fai da te: metodo di misura e risultati comparati"),
    "nimh_battery_charger.htm": ("Ni-Mh fast charger", "Caricabatterie automatico da 1 a 4 celle"),
    "lipo_battery_charger.htm": ("Litio (Li-Po) charger", "Caricabatteria bilanciato"),
    "parkside_battery_pack.htm": ("Parkside paccobatteria 20V 15Ah", "Realizzazione di un pacco maggiorato"),
    "ebike_test_batterie.htm": ("E-bike — test batterie 36/48 V", "Prove di capacità su pacchi per e-bike"),
    "ebike_extra_pack.htm": ("E-bike — extra pack 36/48 V", "Pacco batteria supplementare"),
    "electric_bike_bms.htm": ("BMS 48V 4A", "Battery Management System per e-bike"),
    "auto_elettrica.htm": ("Auto elettrica: che fare?", "Considerazioni su batterie, costi e autonomia"),
    "home_save_energy.htm": ("Come risparmiare energia elettrica in casa", "Consumare meno: consumi domestici, misure e interventi"),
    "solare_termico_centralina.htm": ("Centralina solare termico", "Controllo differenziale per pannello Heat Pipe"),
    "luci_auto.htm": ("Quanto ci costa tenere sempre accese le luci in auto?", "Calcolo del consumo dei fari in automobile"),
    "luci_auto_2.htm": ("Come aumentare la durata delle lampade auto", "Lampade più recenti, tensione e vita utile"),
    "led_light_emitting_diodes.htm": ("Cosa è un LED", "Come si alimenta un light emitting diode"),
    "led_s.htm": ("Utilizzo diverso dei led", "Il led come sensore e altre applicazioni"),
    "led_1_battery_AAA_.htm": ("Un LED con una stilo da 1,5 V", "Alimentare LED 5 mm e 10 mm da singola cella"),
    "led_6_220V.htm": ("Lampade a LED con il 220 V", "Realizzazione di lampade da rete"),
    "led_h4.htm": ("Lampada LED sostituzione H4", "Prove di sostituzione dei fari auto"),
    "led_acquario.htm": ("Illuminare un acquario a LED", "Soluzioni e schemi di alimentazione"),
    "led_bk3_s.htm": ("BK3/S — proiettore LED 10 W", "Proiettore stagno per uso professionale"),
    "led_dimmer_rgb.htm": ("Dimmer RGB 3 canali 12 V 10 A", "Per plafoniere LED e strisce RGB"),
    "led_lamp_10w.htm": ("Illuminatore video 3× Seoul P7", "Lampada video ad alta potenza"),
    "led_video_3p7.htm": ("Video lamp 3× LED P7", "Illuminatore per riprese video"),
    "led_seoul_zp4_mtb_3.htm": ("BIKE-TRILED 2008", "Illuminazione per gare notturne di MTB"),
    "led_torcia_sub_03.htm": ("Torcia sub 3 LED Seoul Z-P4", "Circa 720 lumen, uso subacqueo"),
    "led_torcia_sub_p7.htm": ("Torcia sub 1 LED Seoul P7", "Circa 900 lumen, modifica torcia sub"),
    "led_test.htm": ("Test di illuminazione con torce LED", "Confronto fra torce e lampade, oppure fra ottiche diverse"),
    "test_magicshine.htm": ("Test MagicShine", "Prova su strada di lampade per MTB"),
    "geiger_counter.htm": ("Geiger Counter PC CDV", "Sistema per la misura ambientale delle radiazioni"),
    "geiger_arduino.htm": ("Geiger counter con Arduino", "Contatore di radiazioni digitale"),
    "geiger_counter_pulsar.htm": ("Calibratore per Geiger counter", "Geiger Pulsar e calibrazione"),
    "geiger_counter_voltmeter.htm": ("HV Voltmeter 1000 MΩ", "Misura dell'alta tensione del Geiger counter"),
    "ram63.htm": ("RAM 63 — miglioramenti", "Modifiche a un contatore Geiger militare"),
    "SV500.htm": ("FAG SV500 — upgrade", "Aggiornamento di un Geiger counter FAG"),
    "legge_di_ohm.htm": ("La legge di Ohm", "Fondamenti per principianti"),
    "lux_meter.htm": ("LUX-METER ANALOG", "Luxmetro analogico per misure di illuminamento"),
    "bromografo_uv.htm": ("Bromografo UV realizzato con uno scanner", "Per circuiti stampati fotoincisi"),
    "cmos_cleaning.htm": ("Pulizia sensore reflex C-mos — CCD cleaning", "Procedura e prodotti"),
    "flash_macro.htm": ("Flash macro made simple", "Un semplice flash per la macrofotografia"),
    "monopiede_1.htm": ("MONOPIEDE photo economico", "Realizzato con un bastoncino da trekking"),
    "steady_cam_simple.htm": ("Steady cam made simple", "Stabilizzatore video autocostruito"),
    "printer_3d.htm": ("Printer 3D", "Stampa 3D: esperienze e note"),
    "jeep_perego.htm": ("How to pimp your Perego Jeep", "Elettronica, motore e batterie per l'auto dei bambini"),
    "mtb_gomme_chiodate.htm": ("Gomme chiodate per MTB", "Realizzazione con viti parker"),
    "chirio_com_privacy.htm": ("Informativa sulla privacy", "www.chirio.com — privacy"),
    "chirio_com_disclaimer.htm": ("Disclaimer", "www.chirio.com — condizioni d'uso"),
}

# Small preview used beside each page in the homepage archive list.
# Taken from the thumbnail the original homepage showed for that page;
# where the original had none, the first substantial image on the page.
INDEX_THUMB = {
    'mini_whip.htm': 'IMAGES/mini_whip_034_small2.jpg',
    'mini_whip_sdr.htm': 'IMAGES/mini_whip_050_small.jpg',
    'mini_whip_sdr_p.htm': 'IMAGES/mini_whip_sdr_p01_small.jpg',
    'mini_whip_tricks_and_tips.htm': 'IMAGES/mini_whip_tricks_trip.jpg',
    'mini_loop.htm': 'IMAGES/mini_loop_004_small.jpg',
    'antenna_40m.htm': 'IMAGES/antenna_40_002_small.jpg',
    'yagi_pmr.htm': 'IMAGES/yagi_001_small.jpg',
    'rf_gen_2014.htm': 'IMAGES/rf_gen_2014_oscillator_small.jpg',
    'rf_gen_2018.htm': 'IMAGES/rf_gen_2018_04_small.jpg',
    'rf_gen_VHF.htm': 'IMAGES/rf_gen_vhf_09_small.jpg',
    'vfo_gen_2015.htm': 'IMAGES/vfo_003_small.jpg',
    'tunnel_generator.htm': 'IMAGES/tunnel_003_small.jpg',
    'rf_field_meter.htm': 'IMAGES/rf_led_meter_001_small.jpg',
    'attenuator_20dbm.htm': 'IMAGES/attenuator_01_small.jpg',
    'fm_spy_bug.htm': 'IMAGES/fm_micro_bug_001_small.jpg',
    '433Mhz_sensor.htm': 'IMAGES/433mhz_001_small.jpg',
    'drone_jammer.htm': 'IMAGES/drone_02_small.jpg',
    'switching_power_supply_atx.htm': 'IMAGES/atx_001_small.jpg',
    'atx_14_volt.htm': 'IMAGES/atx_14_ss.jpg',
    'step_up_10a.htm': 'IMAGES/step_up_10a_IMG_4712_x_smal.jpg',
    'push_pull_20_16.htm': 'IMAGES/ps_20a_000.jpg',
    'electronic_load.htm': 'IMAGES/electronic_load_00_ss.jpg',
    'battery_test.htm': 'IMAGES/Battery_test_11_16_small.jpg',
    'nimh_battery_charger.htm': 'IMAGES/battery_charger_nimh_001_sm.jpg',
    'lipo_battery_charger.htm': 'IMAGES/lipo_battery_charger_001_small.jpg',
    'parkside_battery_pack.htm': 'IMAGES/parkside_0.jpg',
    'ebike_test_batterie.htm': 'IMAGES/ebike_battery_pack_01_small.jpg',
    'ebike_extra_pack.htm': 'IMAGES/caricabatterie-ebike.jpg',
    'electric_bike_bms.htm': 'IMAGES/BMS_4A_2014_small.jpg',
    'auto_elettrica.htm': 'IMAGES/citroen_ami_elettrica_2_small.jpg',
    'home_save_energy.htm': 'IMAGES/power_meter_wireless_03_small.jpg',
    'solare_termico_centralina.htm': 'IMAGES/solare_centralina.jpg',
    'luci_auto.htm': 'IMAGES/luci_auto_accese.jpg',
    'luci_auto_2.htm': 'IMAGES/car_lamp_003_small.jpg',
    'led_light_emitting_diodes.htm': 'led/images/led_led5.jpg',
    'led_s.htm': 'IMAGES/led_s_varicap_01_small1.jpg',
    'led_1_battery_AAA_.htm': 'IMAGES/led_1stilo.jpg',
    'led_6_220V.htm': 'IMAGES/led_3xP7_333a_small.jpg',
    'led_h4.htm': 'IMAGES/led_h4_000_small.jpg',
    'led_acquario.htm': 'IMAGES/led_acquario_03.jpg',
    'led_bk3_s.htm': 'IMAGES/BK3_S_001_small.jpg',
    'led_dimmer_rgb.htm': 'IMAGES/led_dimmer_rgb_001_small.jpg',
    'led_lamp_10w.htm': 'IMAGES/led_lamp_000.jpg',
    'led_video_3p7.htm': 'IMAGES/led_p7_3x_video_000_small.jpg',
    'led_seoul_zp4_mtb_3.htm': 'IMAGES/led_bk3_00.jpg',
    'led_torcia_sub_03.htm': 'IMAGES/led_kit_sub_03_a1_small.jpg',
    'led_torcia_sub_p7.htm': 'IMAGES/led_p7_sub_b001_small_small.jpg',
    'led_test.htm': 'IMAGES/led_p7_sk_001.jpg',
    'test_magicshine.htm': 'IMAGES/test_magicshine_mj880_005_s_small.jpg',
    'geiger_counter.htm': 'IMAGES/geiger_pc_002_small.jpg',
    'geiger_arduino.htm': 'IMAGES/geiger_arduino_01_small.jpg',
    'geiger_counter_pulsar.htm': 'IMAGES/geiger_pulse_sm.jpg',
    'geiger_counter_voltmeter.htm': 'IMAGES/voltmeter_1000_03_small.jpg',
    'ram63.htm': 'IMAGES/RAM63_002_small_s.jpg',
    'SV500.htm': 'IMAGES/Sv500_00.JPG',
    'legge_di_ohm.htm': 'IMAGES/legge_di_ohm_table.jpg',
    'lux_meter.htm': 'IMAGES/lux_meter_00_small.jpg',
    'bromografo_uv.htm': 'IMAGES/bromografo_00_small.jpg',
    'cmos_cleaning.htm': 'cmos_cleaning/images/cmos_1.jpg',
    'flash_macro.htm': 'IMAGES/flash_macro_01_ss.jpg',
    'monopiede_1.htm': 'IMAGES/mp_03_a.jpg',
    'steady_cam_simple.htm': 'IMAGES/steadycam_000.jpg',
    'printer_3d.htm': 'IMAGES/3d_printer_004_small.jpg',
    'jeep_perego.htm': 'IMAGES/jeep_perego_000_small.jpg',
    'mtb_gomme_chiodate.htm': 'IMAGES/mtb_chiodate_001_small.jpg',
}

# ------------------------------------------------------------- chaberton ----
CHAB_NAV = [
    ("chab.htm", "Chaberton"),
    ("storia_chaberton.htm", "Storia"),
    ("fortificazioni.htm", "Fortificazioni"),
    ("tunnel_chaberton.htm", "Tunnel"),
    ("teleferica_chaberton.htm", "Teleferica"),
    ("panorami_chaberton.htm", "Panorami"),
    ("pan_360.HTM", "Panoramiche 360°"),
    ("mappa_chaberton.htm", "Mappa"),
    ("escursione_chaberton.htm", "Escursione"),
    ("foto_chaberton.HTM", "Foto"),
    ("video_chaberton.HTM", "Video"),
    ("mappa_sito.htm", "Mappa del sito"),
]

# Galleries: directory -> (index page, human title)
CHAB_GALLERIES = {
    "batteria_2003": ("batteria_2003.htm", "Batteria Chaberton — 2003"),
    "foto_210804": ("index.htm", "Foto 21 agosto 2004"),
    "foto_301204": ("index.htm", "Forti di Briançon — 30 dicembre 2004"),
    "cesana_40_42": ("index.htm", "Cesana 1940–42"),
    "2007_04_05": ("index.htm", "17 marzo 2007"),
    "pt_vallon": ("index.htm", "Postazioni del Petit Vallon"),
    "centri_colle": ("index.htm", "Postazioni al Colle dello Chaberton"),
}

# Panorama pages: page -> (panorama jpg, page title).  Titles are the captions
# the author wrote on each page, minus the obsolete "(versione Java)" note.
CHAB_PANORAMAS = {
    "pan_01/Pan001.html": ("pan_01/pano/360_chab_03.jpg",
                           "Pan 360° — spianata lato est (18 settembre 2004)"),
    "pan_02/Pan002.html": ("pan_02/pano/360_chab_02.jpg",
                           "Pan 360° — dalla Torre n.4 (21 agosto 2004)"),
    "pan_03/Pan003.html": ("pan_03/pano/360_chab_01.jpg",
                           "Pan 360° — spianata (29 luglio 2005)"),
}

SITE_NAME = "Chirio.com"
SITE_TAGLINE = "Elettronica, radio e progetti di Roberto Chirio"
CHAB_NAME = "La Batteria dello Chaberton"
