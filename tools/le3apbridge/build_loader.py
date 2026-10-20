"""Build the unmodified official LEBinkProxy checkout using the local VS toolset."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
environment = {key.upper(): value for key, value in os.environ.items()}
subprocess.run([
    "C:/Program Files/Microsoft Visual Studio/18/Community/MSBuild/Current/Bin/MSBuild.exe",
    str(ROOT / "tools/vendor/LEBinkProxy/bink2w64.vcxproj"),
    "/p:Configuration=Release", "/p:Platform=x64", "/p:PlatformToolset=v145",
    "/p:GenerateDebugInformation=false", "/p:LinkIncremental=false",
    "/p:OutDir=" + str(ROOT / "build/loader") + "/",
    "/p:IntDir=" + str(ROOT / "build/loader-obj") + "/", "/verbosity:minimal",
], env=environment, check=True)
