# ============================================================
# DISASTERGUARD - WILDFIRE SATELLITE IMAGE DOWNLOADER
# Resume-safe version for Pakistan FIRMS detections (2020-2025)
# ============================================================

from pathlib import Path
from io import BytesIO
import re
import time
import traceback

import ee
import pandas as pd
import requests
from PIL import Image, ImageStat


# ============================================================
# 1. CONFIGURATION
# ============================================================

GEE_PROJECT = "disasterguard-514118"

# This script should be saved in the project ROOT folder.
PROJECT_ROOT = Path(__file__).resolve().parent

FIRMS_CSV = (
    PROJECT_ROOT / "datasets" / "wildfire" / "raw"
    / "pakistan_viirs_snpp_2020_2025.csv"
)

OUTPUT_ROOT = PROJECT_ROOT / "datasets" / "wildfire" / "images"
BEFORE_DIR = OUTPUT_ROOT / "before"
AFTER_DIR = OUTPUT_ROOT / "after"

METADATA_FILE = OUTPUT_ROOT / "metadata.csv"
FAILED_FILE = OUTPUT_ROOT / "failed.csv"

# None = all records. For a small test, temporarily use 20.
MAX_SAMPLES = None

# Used only if metadata.csv does not exist or contains no recognizable IDs.
# 20419 means start at row 20420 (zero-based index 20419).
FALLBACK_START_INDEX = 20419



START_DATE = "2020-01-01"
END_DATE_EXCLUSIVE = "2026-01-01"

IMAGE_SIZE = 256
MAX_CLOUD = 30

BEFORE_DAYS = 60
AFTER_DAYS = 90
DATE_GAP = 7

WEST, SOUTH, EAST, NORTH = 60.5, 23.5, 77.9, 37.2

SENTINEL_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
RGB_BANDS = ["B4", "B3", "B2"]

DELAY_SECONDS = 0.5
OVERWRITE = False


# ============================================================
# 2. CREATE FOLDERS
# ============================================================

BEFORE_DIR.mkdir(parents=True, exist_ok=True)
AFTER_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


# ============================================================
# 3. EARTH ENGINE
# ============================================================

def initialize_earth_engine():
    print("\n[INFO] Connecting to Google Earth Engine...")

    try:
        ee.Initialize(project=GEE_PROJECT)
        print("[SUCCESS] Earth Engine connected.")
    except Exception as first_error:
        print("[WARNING] Existing authentication could not initialize EE.")
        print("[INFO] Starting Google Earth Engine authentication...")
        print("Details:", first_error)
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)
        print("[SUCCESS] Authentication completed.")


# ============================================================
# 4. LOAD AND FILTER FIRMS CSV
# ============================================================

def load_firms_data():
    print("\n[INFO] Loading NASA FIRMS CSV...")

    if not FIRMS_CSV.exists():
        raise FileNotFoundError(f"FIRMS CSV not found:\n{FIRMS_CSV}")

    df = pd.read_csv(FIRMS_CSV)

    required = ["latitude", "longitude", "acq_date"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required CSV columns: {missing}")

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")

    df = df.dropna(subset=required).copy()

    start = pd.Timestamp(START_DATE)
    end_exclusive = pd.Timestamp(END_DATE_EXCLUSIVE)
    df = df[
        (df["acq_date"] >= start)
        & (df["acq_date"] < end_exclusive)
    ].copy()

    df = df[
        df["latitude"].between(SOUTH, NORTH)
        & df["longitude"].between(WEST, EAST)
    ].copy()

    # Keep the same de-duplication and sorting approach as the earlier script.
    df["lat_key"] = df["latitude"].round(4)
    df["lon_key"] = df["longitude"].round(4)
    df = df.drop_duplicates(
        subset=["lat_key", "lon_key", "acq_date"]
    )

    # IMPORTANT: keep this exact sort to preserve the previous sample numbering.
    df = df.sort_values("acq_date").reset_index(drop=True)

    if MAX_SAMPLES is not None:
        df = df.head(MAX_SAMPLES).copy()

    df = df.reset_index(drop=True)

    print(f"[INFO] FIRMS records available: {len(df)}")
    if not df.empty:
        print(
            f"[INFO] Date range: {df['acq_date'].min().date()} "
            f"to {df['acq_date'].max().date()}"
        )
        print("[INFO] Records by year:")
        print(df["acq_date"].dt.year.value_counts().sort_index())

    return df


# ============================================================
# 5. RESUME FROM EXISTING METADATA
# ============================================================

def load_resume_state():
    """
    Loads previous metadata and determines the next zero-based row index.
    Existing metadata is retained; it is never discarded.
    """
    if not METADATA_FILE.exists():
        print("[INFO] No previous metadata found.")
        return [], FALLBACK_START_INDEX

    try:
        old_df = pd.read_csv(METADATA_FILE)

        if old_df.empty or "sample_id" not in old_df.columns:
            print("[WARNING] Existing metadata has no usable sample IDs.")
            return [], FALLBACK_START_INDEX

        indexes = []
        for sample_id in old_df["sample_id"].dropna().astype(str):
            match = re.search(r"fire_(\d+)_", sample_id)
            if match:
                indexes.append(int(match.group(1)))

        if not indexes:
            print("[WARNING] Could not read record indexes from metadata.")
            return old_df.to_dict("records"), FALLBACK_START_INDEX

        next_index = max(max(indexes) + 1, FALLBACK_START_INDEX)

        print(f"[INFO] Previous metadata records loaded: {len(old_df)}")
        print(f"[INFO] Highest saved record index: {max(indexes)}")
        print(f"[INFO] Next record to process: {next_index + 1}")

        return old_df.to_dict("records"), next_index

    except Exception as error:
        print("[WARNING] Could not read previous metadata:", error)
        print("[INFO] Using fallback start index:", FALLBACK_START_INDEX)
        return [], FALLBACK_START_INDEX


# ============================================================
# 6. SENTINEL-2 CLOUD MASK
# ============================================================

def mask_sentinel_clouds(image):
    scl = image.select("SCL")
    mask = (
        scl.neq(3)       # cloud shadow
        .And(scl.neq(8)) # medium probability cloud
        .And(scl.neq(9)) # high probability cloud
        .And(scl.neq(10))# cirrus
        .And(scl.neq(11))# snow/ice
    )
    return image.updateMask(mask)


# ============================================================
# 7. FIND BEST AVAILABLE SENTINEL IMAGE
# ============================================================

def find_sentinel_image(latitude, longitude, start_date, end_date):
    point = ee.Geometry.Point([float(longitude), float(latitude)])
    region = point.buffer(1280).bounds()

    collection = (
        ee.ImageCollection(SENTINEL_COLLECTION)
        .filterBounds(region)
        .filterDate(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD))
        .map(mask_sentinel_clouds)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    count = collection.size().getInfo()
    if count == 0:
        return None

    image = ee.Image(collection.first())

    image_date = ee.Date(
        image.get("system:time_start")
    ).format("YYYY-MM-dd").getInfo()

    cloud = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()

    return {
        "image": image,
        "region": region,
        "date": image_date,
        "cloud": cloud
    }


# ============================================================
# 8. RGB VISUALIZATION AND PNG DOWNLOAD
# ============================================================

def create_visual_rgb(image):
    reflectance = image.select(RGB_BANDS).multiply(0.0001)

    return reflectance.visualize(
        bands=RGB_BANDS,
        min=0.02,
        max=0.30,
        gamma=1.3
    )


def download_rgb(image, region, output_path):
    if output_path.exists() and not OVERWRITE:
        print(f"[SKIP] Image already exists: {output_path.name}")
        return True

    visual_image = create_visual_rgb(image)

    download_url = visual_image.getThumbURL({
        "region": region,
        "dimensions": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
        "format": "png"
    })

    response = requests.get(download_url, timeout=120)
    response.raise_for_status()

    with Image.open(BytesIO(response.content)) as opened:
        satellite_image = opened.convert("RGB")

    satellite_image = satellite_image.resize(
        (IMAGE_SIZE, IMAGE_SIZE),
        Image.Resampling.LANCZOS
    )

    brightness = sum(ImageStat.Stat(satellite_image).mean) / 3
    if brightness < 1.0:
        raise ValueError("Downloaded image is almost completely black.")

    satellite_image.save(output_path, format="PNG")
    return True


# ============================================================
# 9. PROCESS ONE FIRMS DETECTION
# ============================================================

def process_fire_location(index, row):
    latitude = float(row["latitude"])
    longitude = float(row["longitude"])
    fire_date = pd.Timestamp(row["acq_date"]).normalize()

    sample_id = f"fire_{index:06d}_{fire_date.strftime('%Y%m%d')}"

    before_path = BEFORE_DIR / f"{sample_id}_before.png"
    after_path = AFTER_DIR / f"{sample_id}_after.png"

    print("\n" + "=" * 65)
    print(f"[{index + 1}] Processing {sample_id}")
    print(f"Location: {latitude}, {longitude}")
    print(f"Fire date: {fire_date.date()}")

    result = {
        "sample_id": sample_id,
        "latitude": latitude,
        "longitude": longitude,
        "fire_date": fire_date.strftime("%Y-%m-%d"),
        "before_image": "",
        "before_date": "",
        "before_cloud": "",
        "after_image": "",
        "after_date": "",
        "after_cloud": "",
        "status": ""
    }

    # BEFORE image: from 60 days before until 7 days before fire date.
    try:
        before_start = fire_date - pd.Timedelta(days=BEFORE_DAYS)
        before_end = fire_date - pd.Timedelta(days=DATE_GAP)

        print("[INFO] Searching BEFORE satellite image...")
        before_data = find_sentinel_image(
            latitude, longitude, before_start, before_end
        )

        if before_data:
            download_rgb(
                before_data["image"], before_data["region"], before_path
            )
            result["before_image"] = str(before_path.relative_to(PROJECT_ROOT))
            result["before_date"] = before_data["date"]
            result["before_cloud"] = before_data["cloud"]
            print("[SUCCESS] Before image:", before_data["date"])
        else:
            print("[WARNING] No BEFORE image found.")
    except Exception as error:
        print("[ERROR] Before image:", error)

    # AFTER image: from 7 days after until 90 days after fire date.
    try:
        after_start = fire_date + pd.Timedelta(days=DATE_GAP)
        after_end = fire_date + pd.Timedelta(days=AFTER_DAYS + 1)

        print("[INFO] Searching AFTER satellite image...")
        after_data = find_sentinel_image(
            latitude, longitude, after_start, after_end
        )

        if after_data:
            download_rgb(
                after_data["image"], after_data["region"], after_path
            )
            result["after_image"] = str(after_path.relative_to(PROJECT_ROOT))
            result["after_date"] = after_data["date"]
            result["after_cloud"] = after_data["cloud"]
            print("[SUCCESS] After image:", after_data["date"])
        else:
            print("[WARNING] No AFTER image found.")
    except Exception as error:
        print("[ERROR] After image:", error)

    has_before = bool(result["before_image"])
    has_after = bool(result["after_image"])

    if has_before and has_after:
        result["status"] = "paired"
    elif has_before:
        result["status"] = "before_only"
    elif has_after:
        result["status"] = "after_only"
    else:
        result["status"] = "no_images_found"

    print("[INFO] Status:", result["status"])
    return result


# ============================================================
# 10. SAVE ALL OLD + NEW METADATA
# ============================================================

def save_metadata(all_results):
    if not all_results:
        return

    metadata_df = pd.DataFrame(all_results)

    # Keep only one row per sample_id; latest row wins.
    if "sample_id" in metadata_df.columns:
        metadata_df = metadata_df.drop_duplicates(
            subset=["sample_id"], keep="last"
        )

    metadata_df.to_csv(METADATA_FILE, index=False)

    failed_df = metadata_df[metadata_df["status"] != "paired"]
    failed_df.to_csv(FAILED_FILE, index=False)

    print("[INFO] Progress saved:", METADATA_FILE)


# ============================================================
# 11. MAIN
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("DISASTERGUARD - WILDFIRE SATELLITE IMAGE DOWNLOADER")
    print("Pakistan | Sentinel-2 RGB | 2020-2025")
    print("=" * 70)

    initialize_earth_engine()
    df = load_firms_data()

    if df.empty:
        print("[ERROR] No FIRMS records found.")
        return

    all_results, start_index = load_resume_state()
    total = len(df)

    if start_index >= total:
        print("[INFO] No remaining records to process.")
        print(f"[INFO] Dataset contains {total} records.")
        return

    print(f"\n[INFO] Total FIRMS records: {total}")
    print(f"[INFO] Starting at record: {start_index + 1}")
    print(f"[INFO] Remaining records: {total - start_index}")
    print("[INFO] Existing metadata and images will be preserved.")

    for index in range(start_index, total):
        row = df.iloc[index]

        try:
            result = process_fire_location(index, row)
            all_results.append(result)

        except KeyboardInterrupt:
            print("\n[WARNING] Stopped by user. Saved progress is retained.")
            save_metadata(all_results)
            break

        except Exception as error:
            print(f"[ERROR] Record {index + 1}: {error}")
            traceback.print_exc()

            fire_date = pd.Timestamp(row["acq_date"]).normalize()
            all_results.append({
                "sample_id": f"fire_{index:06d}_{fire_date.strftime('%Y%m%d')}",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "fire_date": fire_date.strftime("%Y-%m-%d"),
                "before_image": "",
                "before_date": "",
                "before_cloud": "",
                "after_image": "",
                "after_date": "",
                "after_cloud": "",
                "status": "failed"
            })

        # Save after EVERY processed record.
        save_metadata(all_results)

        print(f"\n[PROGRESS] {index + 1}/{total} completed")
        time.sleep(DELAY_SECONDS)

    if all_results:
        final_df = pd.DataFrame(all_results)
        print("\n" + "=" * 70)
        print("DOWNLOAD SUMMARY")
        print("=" * 70)
        print("Metadata rows:", len(final_df))
        print("Paired:", (final_df["status"] == "paired").sum())
        print("Before only:", (final_df["status"] == "before_only").sum())
        print("After only:", (final_df["status"] == "after_only").sum())
        print("No images:", (final_df["status"] == "no_images_found").sum())
        print("Failed:", (final_df["status"] == "failed").sum())

    print("\n[FINISHED] Wildfire image processing run ended.")
    print("Output folder:", OUTPUT_ROOT)


if __name__ == "__main__":
    main()
