#!/usr/bin/env python3
import argparse
import ctypes
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser(description="Run HMF simulation via ctypes-enabled Fortran core")
    p.add_argument("--lib", default="build/libhmf_ctypes.so")
    p.add_argument("--nx", type=int, required=True)
    p.add_argument("--nv", type=int, required=True)
    p.add_argument("--vmax", type=float, required=True)
    p.add_argument("--dt", type=float, required=True)
    p.add_argument("--n-steps", type=int, required=True)
    p.add_argument("--n-top", type=int, required=True)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--bag", type=float, required=True)
    p.add_argument("--out", default="hmf_observables.npz")
    args = p.parse_args()

    lib = ctypes.CDLL(str(Path(args.lib).resolve()))
    run = lib.hmf_run
    run.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
        np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
        np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS"),
    ]
    run.restype = None

    size = args.n_top + 1
    mx = np.zeros(size, dtype=np.float64)
    my = np.zeros(size, dtype=np.float64)
    en = np.zeros(size, dtype=np.float64)

    run(args.nx, args.nv, args.vmax, args.dt, args.n_steps, args.n_top, args.width, args.bag, mx, my, en)

    np.savez(args.out, mx=mx, my=my, energy=en)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
