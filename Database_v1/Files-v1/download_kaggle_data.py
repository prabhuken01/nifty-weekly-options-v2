#!/usr/bin/env python3
"""
Download Nifty Options dataset from Kaggle
Dataset: pariminikhil/nifty-option-chain-3-oct-24-to-24-mar-26
"""

import os
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_kaggle_credentials():
    """Copy kaggle.json to .kaggle folder"""
    local_kaggle = Path(__file__).parent / "kaggle.json"

    if not local_kaggle.exists():
        logger.error("[ERROR] kaggle.json not found in current folder")
        return False

    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)

    kaggle_dest = kaggle_dir / "kaggle.json"

    # Copy the file
    import shutil
    shutil.copy(local_kaggle, kaggle_dest)
    logger.info(f"[OK] Copied kaggle.json to {kaggle_dest}")

    # Set proper permissions
    os.chmod(kaggle_dest, 0o600)

    return True

def download_dataset():
    """Download Nifty options dataset from Kaggle"""
    logger.info("="*80)
    logger.info("KAGGLE DATASET DOWNLOAD")
    logger.info("="*80)

    # Setup credentials
    if not setup_kaggle_credentials():
        return False

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        logger.info("[OK] Importing Kaggle API...")
        api = KaggleApi()
        api.authenticate()
        logger.info("[OK] Kaggle authentication successful")

        # Download dataset
        dataset = "pariminikhil/nifty-option-chain-3-oct-24-to-24-mar-26"
        download_path = "./kaggle_data"

        logger.info(f"\n[DOWNLOAD] Downloading dataset: {dataset}")
        logger.info(f"[DOWNLOAD] To folder: {download_path}")

        api.dataset_download_files(
            dataset,
            path=download_path,
            unzip=True
        )

        logger.info(f"[OK] Dataset downloaded and extracted")

        # List files
        data_path = Path(download_path)
        if data_path.exists():
            files = list(data_path.glob("**/*"))
            csv_files = [f for f in files if f.suffix == '.csv']

            logger.info(f"\n[INFO] Files in dataset:")
            for f in csv_files[:10]:
                size_mb = f.stat().st_size / (1024*1024)
                logger.info(f"  - {f.name} ({size_mb:.2f} MB)")

            if len(csv_files) > 10:
                logger.info(f"  ... and {len(csv_files) - 10} more files")

            return True
        else:
            logger.error("[ERROR] Download path not found")
            return False

    except Exception as e:
        logger.error(f"[ERROR] Download failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = download_dataset()
    if success:
        logger.info("\n[OK] Dataset ready for processing")
    else:
        logger.error("\n[FAIL] Dataset download failed")
