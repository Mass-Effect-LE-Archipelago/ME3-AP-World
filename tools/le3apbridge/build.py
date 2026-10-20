"""Build the research ASI (or explicit delivery spike), with game-copy hooks disabled."""
from __future__ import annotations

import os
import argparse
import json
import re
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
CMAKE = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft Visual Studio/18/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--delivery-dev", action="store_true", help="Build opt-in delivery spike into a separate directory")
    profile.add_argument("--career-trace", action="store_true", help="Build read-only career observer into a separate directory")
    args = parser.parse_args()
    if args.delivery_dev:
        audit = json.loads((HERE.parents[1] / "research/le3_delivery_storage_audit_summary.json").read_text())
        header = (HERE / "Delivery.hpp").read_text()
        first = int(re.search(r"constexpr int Base = (0x[0-9A-Fa-f]+)", header).group(1), 16)
        slots = int(re.search(r"constexpr int Slots = (\d+)", header).group(1))
        if audit["candidate_int_block"] != [first, first + slots - 1] or audit["package_and_executable_scan"]["errors"]:
            raise RuntimeError("Development delivery requires a matching completed storage audit")
        for family in ("typed_int_property_hits", "script_function_export_hits", "native_executable_hits", "config_hits", "database_int_hits"):
            if audit[family]:
                raise RuntimeError(f"Unresolved delivery storage audit hits: {family}")
    build = HERE / ("build-delivery" if args.delivery_dev else "build-career" if args.career_trace else "build")
    # Some hosts inherit both PATH and Path. .NET Framework MSBuild rejects
    # duplicate case-insensitive environment keys. Normalize only this child.
    environment = {key.upper(): value for key, value in os.environ.items()}
    for key in ("LEASI_GAME1_WIN64", "LEASI_GAME2_WIN64", "LEASI_GAME3_WIN64", "LEASI_GAMEL_WIN64"):
        environment.pop(key, None)
    environment["LEASI_CMAKE_PRESET"] = "VisualStudio"
    subprocess.run([str(CMAKE), "--fresh", "-S", str(HERE), "-B", str(build),
                    "-G", "Visual Studio 18 2026", "-A", "x64",
                    "-DLEASI_BUILD_LE1=OFF", "-DLEASI_BUILD_LE2=OFF",
                    "-DLEASI_BUILD_LE3=ON", "-DLEASI_BUILD_LEL=OFF",
                    "-DLE3AP_DELIVERY_DEV=" + ("ON" if args.delivery_dev else "OFF"),
                    "-DLE3AP_CAREER_TRACE=" + ("ON" if args.career_trace else "OFF")], env=environment, check=True)
    subprocess.run([str(CMAKE), "--build", str(build), "--config", "RELEASE",
                    "--target", "APBridge-LE3", "DeliveryTests", "CareerTraceTests", "--parallel", "2"], env=environment, check=True)
    subprocess.run([str(build / "Release/DeliveryTests.exe")], env=environment, check=True)
    subprocess.run([str(build / "Release/CareerTraceTests.exe")], env=environment, check=True)


if __name__ == "__main__":
    main()
