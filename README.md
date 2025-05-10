# mhd_ba
Custom component for home assistant to get idsbk stops data as a sensor

# Instalation
1. Copy mhd_ba folder into custom_components folder and restart home assistant
2. In Home assistant open add new integration and search for MHD BA
3. Open https://mapa.idsbk.sk/mhd-ids-bk and click on F12 to display network tab in dev tools
4. On page on the left side search for your stop name and select it
5. in dev tools network tab search for call that contain stop id, e.g. https://mapa.idsbk.sk/navigation/stops/ids?ids=800000169
6. copy id and insert it into integration stop id input
7. click on submit to add stop into home assistant as a sensor

You can add multiple stops with different stop id, or with same stop id but different lines filter
