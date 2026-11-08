"""Build this release without assuming the author's machine paths."""
import argparse, os, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cargo", help="Path to cargo if it is not on PATH.")
    parser.add_argument("--cargo-home", type=Path, help="Optional existing download cache.")
    parser.add_argument("--rustup-home", type=Path, help="Optional existing Rust toolchains.")
    args = parser.parse_args()
    cargo = args.cargo or shutil.which("cargo")
    if not cargo:
        raise SystemExit("Install Rust and its platform C/C++ toolchain, or supply --cargo.")
    scratch = ROOT/".research-tmp/build"
    scratch.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CARGO_TARGET_DIR":str(ROOT/"native/target"),
           "TMP":str(scratch), "TEMP":str(scratch), "CARGO_BUILD_JOBS":"4"}
    if args.cargo_home: env["CARGO_HOME"] = str(args.cargo_home.resolve())
    if args.rustup_home: env["RUSTUP_HOME"] = str(args.rustup_home.resolve())
    env["PATH"] = str(Path(cargo).resolve().parent)+os.pathsep+env["PATH"]
    subprocess.run([cargo, "build", "--locked", "--release", "--bin", "receiptcoordinator"],
                   cwd=ROOT/"native", env=env, check=True)

if __name__ == "__main__":
    main()
