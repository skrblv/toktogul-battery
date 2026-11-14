# Toktogul Battery

How full is Kyrgyzstan's battery? The Toktogul reservoir feeds the power plants that keep the country's lights on in winter. We measure its water surface from space with NISAR, the NASA and ISRO radar satellite, and show it next to the officially published water volumes.

Team Paparizi, NASA Space Apps Challenge 2026, challenge "Dancing with the SARs", Bishkek.

## What is in this repository

| File | What it is |
| --- | --- |
| `index.html` | The website. One file, no server; the radar images and numbers are inside it. |
| `toktogul_nisar_v2.ipynb` | The notebook that reads NISAR data from NASA's cloud and makes every number and picture on the page. Runs in Google Colab. |
| `template.html` | The page without data. Put it next to the notebook and the notebook writes a fresh `index.html`. |
| `check_method.py` | A test: runs the notebook's code on simulated radar scenes where the true water area is known. |

## What we found

- The water surface grew from about 206 km² on 20 June 2026 to about 216 km² in late September, a rise of about 11 km².
- Most of the rise, about 8 km², came between 20 June and 2 July, when the Naryn river runs highest.
- All eleven images were taken at 20:09 Bishkek time, seven of them after sunset. The radar does not need daylight or a clear sky.
- By the official count the reservoir held 11.345 billion m³ on 15 October 2026. The part that power plants can use (between the dead level, 5.5, and full, 19.5) was 42% full.

## How the method works

For NISAR's L-band radar, calm water and dry, smooth ground are both very dark. A brightness threshold on one image counts the dry plain around the reservoir as water (our first attempt gave about 700 km² instead of about 215). Wet ground is different: it turns bright, and water does not change.

1. Read only the reservoir window from each NISAR GCOV scene in NASA's cloud. A full scene is about 2 GB; the window is a few dozen megabytes.
2. Use scenes from one orbit only (track 092 descending, frame 067), so the radar looks at the mountains from the same side every time.
3. Find the dates when the ground was wet: the land near the reservoir is 2 to 4 dB brighter than usual and the water is the same. In our series these are 24 September and 6 October.
4. The water body is what stays dark on those dates.
5. For every other date, a pixel counts as water only if it looks the way it does on the wet dates, on that date and on every date between it and the wet date.
6. Repeat the test with a stricter and a looser setting. The spread is the error band shown on the page.

## What it cannot tell you

- The analysis grid is 80 m, so the total area is uncertain by several km². Changes between dates are more reliable than the total.
- Dry, smooth ground can pass for water between wet dates, so growth after mid-July is probably undercounted.
- We did not check the wet dates against a local weather station. NASA POWER shows about 24 mm of rain in the five days before 6 October and light rain on 24 September, but it is one value for a square of mostly mountains about 50 km wide. It also shows showers in late June that left no trace near the reservoir in the radar images.
- The narrow canyon next to the dam is only partly counted.
- NISAR data for this area start in June 2026, so there are no winter images yet.
- The volume and the percentage come from official statements, not from the radar. The radar gives the surface area.

## Run it yourself

1. Create a free NASA Earthdata account: https://urs.earthdata.nasa.gov/users/new
2. Open `toktogul_nisar_v2.ipynb` in Google Colab and choose Runtime, Run all.
3. Type your Earthdata username and password when the login cell asks. They stay inside your Colab session.
4. After a few minutes the notebook prints the table of areas and downloads `toktogul_out.zip`.

To test the method without NASA access:

```
pip install numpy scipy h5py pyproj pillow matplotlib nbformat
python check_method.py
```

On the simulated scenes the measured area stays within 1 km² of the truth. Real ground is messier.

## Data and sources

- NISAR Level-2 GCOV radar backscatter (L-band, HH and HV), NASA and ISRO, distributed by the Alaska Satellite Facility DAAC. Products are provisional.
- NASA POWER daily precipitation (MERRA-2 and GEOS-IT), point 41.85 N, 72.90 E: https://power.larc.nasa.gov/
- Official reservoir volumes: statements of the Ministry of Energy of the Kyrgyz Republic, reported by Economist.kg on [8 July 2026](https://economist.kg/enierghietika/2026/07/08/toktogul-voda-11-5-mlrd/) and [19 October 2026](https://economist.kg/enierghietika/2026/10/19/vyrabotka-980-mln-2026/).
- Dead level and capacity: [24.kg](https://24.kg/obschestvo/363300_skolko_vodyi_byilo_vtoktogulskom_vodohranilische_na1aprelya_vraznyie_godyi/).

## Use of AI

An AI assistant (Claude by Anthropic) helped write the processing code, the website and this text. The team chose the idea, ran the analysis on NASA data and checked the results against the images.

## Team

Baitur Raimzhanov, Sultan Maksutaliev.

## License

MIT. See `LICENSE`.
