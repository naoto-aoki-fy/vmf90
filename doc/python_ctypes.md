ctypes Python interface for the HMF simulator {#python_ctypes}
==========================================

This page describes how to call and execute the HMF simulator from Python via
`ctypes`.

Prerequisites
-------------

- A working build toolchain for vmf90 (Fortran compiler and HDF5 setup).
- Python 3 with NumPy installed.

Build the shared library
------------------------

From the repository root, build the ctypes-enabled shared library:

    make -C build -f ../scripts/Makefile hmf_ctypes

This target generates:

- `build/libhmf_ctypes.so`

The library exports the C ABI entry point `hmf_run` from
`src/hmf_ctypes.f90`.

Use the provided Python driver
------------------------------

A ready-to-run driver is provided in `python/hmf_sim.py`.

Example command from the repository root:

    python3 python/hmf_sim.py \
      --nx 64 --nv 64 --vmax 2.0 \
      --dt 0.1 --n-steps 4 --n-top 10 \
      --width 1.0 --bag 1.0 \
      --out hmf_observables.npz

What this script does
---------------------

1. Loads `build/libhmf_ctypes.so` using `ctypes.CDLL`.
2. Resolves `hmf_run` and declares argument types (`int`, `double`, and three
   output `float64` arrays).
3. Allocates NumPy arrays of size `n_top + 1` for `mx`, `my`, and `energy`.
4. Calls the simulator.
5. Saves results to a `.npz` file.

Input parameters
----------------

`hmf_run` receives:

- `nx`: number of grid points in `x`
- `nv`: number of grid points in `v`
- `vmax`: maximum velocity
- `dt`: time step
- `n_steps`: number of internal time steps between saved samples
- `n_top`: number of saved output intervals
- `width`: initial waterbag width in position
- `bag`: initial waterbag width in velocity

Outputs
-------

The simulator fills three arrays (all `float64`) of length `n_top + 1`:

- `mx_out`: magnetization component `M_x`
- `my_out`: magnetization component `M_y`
- `en_out`: total energy

Using `ctypes` directly in your own script
-------------------------------------------

If you prefer not to use `python/hmf_sim.py`, replicate the same interface in
your own code:

- Load `build/libhmf_ctypes.so`.
- Set `run = lib.hmf_run`.
- Declare `run.argtypes` exactly as in `python/hmf_sim.py`.
- Allocate C-contiguous `numpy.float64` 1D arrays for outputs.
- Call `run(...)` with the same parameter ordering.

Notes
-----

- The default library path in `python/hmf_sim.py` is `build/libhmf_ctypes.so`.
  Override it with `--lib` if needed.
- Output arrays must be contiguous `float64` buffers; otherwise `ctypes` type
  checks will fail.
