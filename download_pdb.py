#!/usr/bin/env python3

import argparse
import os
import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download PDB files from RCSB"
    )
    parser.add_argument(
        "-p", "--pdb",
        nargs="+",
        required=True,
        help="PDB ID(s), e.g. 1ABC 2XYZ"
    )
    parser.add_argument(
        "-o", "--outdir",
        default="pdbs",
        help="Output directory (default: pdbs)"
    )
    parser.add_argument(
        "--format",
        choices=["pdb", "cif"],
        default="pdb",
        help="File format (default: pdb)"
    )
    return parser.parse_args()


def download_structure(pdb_id, outdir, file_format):
    pdb_id = pdb_id.upper()
    os.makedirs(outdir, exist_ok=True)

    url = f"https://files.rcsb.org/download/{pdb_id}.{file_format}"
    outfile = os.path.join(outdir, f"{pdb_id}.{file_format}")

    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            with open(outfile, "wb") as f:
                f.write(r.content)
            print(f"[OK] {pdb_id}")
        else:
            print(f"[FAIL] {pdb_id} (status {r.status_code})")
    except Exception as e:
        print(f"[ERROR] {pdb_id}: {e}")


def main():
    args = parse_args()

    for pdb_id in args.pdb:
        download_structure(pdb_id, args.outdir, args.format)


if __name__ == "__main__":
    main()
