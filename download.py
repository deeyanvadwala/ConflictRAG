import requests, pathlib

IDS = [
    # DRA 5.0 era
    "20090010571", "20090012109", "20100028285", "20090040343",
    "20120012928", "20120012929", "20110005558",
    # Early era (1997-1998)
    "19980037039", "19980218778",
    # Recent era (EMC, 2014-2016)
    "20140016934", "20150006952", "20160006315",
]

# Some records use a different filename on NTRS
OVERRIDES = {
    "19980037039": "https://ntrs.nasa.gov/api/citations/19980037039/downloads/19980037039_Update.pdf",
    "19980218778": "https://ntrs.nasa.gov/api/citations/19980218778/downloads/19980218778_Update.pdf",
}

pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)

for i in IDS:
    out = pathlib.Path(f"data/raw/{i}.pdf")
    if out.exists():
        continue
    url = OVERRIDES.get(i, f"https://ntrs.nasa.gov/api/citations/{i}/downloads/{i}.pdf")
    r = requests.get(url, timeout=120)
    if r.ok and r.content[:4] == b"%PDF":
        out.write_bytes(r.content)
        print("saved", i)
    else:
        print("FAILED", i, r.status_code, "-> download manually from https://ntrs.nasa.gov/citations/" + i)