# mhd_ba
Custom component for home assistant to get idsbk stops data as a sensor

# Instalation
1. Create mhd_ba folder in custom_components folder in home assistant
1. Copy all files into mhd_ba folder (you can download all files as zip)
1. In Home assistant open add new integration and search for MHD BA
1. Open https://mapa.idsbk.sk/mhd-ids-bk and click on F12 to display network tab in dev tools
1. On page on the left side search for your stop name and select it
1. in dev tools network tab search for call that contain stop id, e.g. https://mapa.idsbk.sk/navigation/stops/ids?ids=800000169
1. copy id and insert it into integration stop id input
1. click on submit to add stop into home assistant as a sensor

You can add multiple stops with different stop id, or with same stop id but different lines filter
