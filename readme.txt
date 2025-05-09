# VSR Checker App

## Overview
This application processes vehicle scan report (VSR) HTML files, compares ECU part numbers and software versions against a Master Software List, and provides an easy-to-use visual report.

## How It Works
- Upload a VSR HTML file.
- The app parses ECU information and compares it to the Master SW List.
- Color-coded results show matches, mismatches, and missing ECUs.

## Key Features
- Upload VSR and auto-compare to latest master list.
- View, edit, and save the Master SW List directly through the app.
- Filter results by match/mismatch status.
- Hide unwanted ECUs dynamically.
- Download filtered results as CSV.
- View app ReadMe inside the GUI.

## Roadmap
- [x] Add logic to identify if Hardware of SW is NEWER than expected (if number is bigger)
- [x] Filters to show only high priority / powertrain ECUs, or ADAS ECUs, or Other
- Add historical comparison ("diffing") between two VSR scans.
- Add versioned backups of the Master SW List.
- Save backups of every VSR uploaded in a repository (ignore duplicates)
- Summary:
  VIN: xxxxxxxxxx
  Vehicle: (Year: xxxx, Body: xxxx)
  Total ECUs in VSR: (number found/total number xx%)
  Part Status: # matching/ total ECUs found
  SW Status: # matching/total ECUs found
- [x] Autofit table column width, not to exceed a fixed pixel width
- Replace Download CSV with Download Excel summary
- Add Print option
- Add share option - email summary list
- Freeze top row (headers)
- Add Priority column (Powertrain Modules = 1, ADAS modules = 2, other = 3). Easily sort by priority
- Action plan summary (provide list of modules to update in order of priority):
    -ex. 
      - 1) Update BCM from (sw#) to (sw#). Contact [Name of DRE] if needed
      - 2) Update ......

## Known Bugs
- Only available locally, as master sw list is stored on P4AVD
- Need to press "Save Master List" twice to refresh Comparison Results


---

Last updated: April 2025
