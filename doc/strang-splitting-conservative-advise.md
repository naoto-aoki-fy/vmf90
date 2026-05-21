## Verdict

`model = HMF_strang_cons` is **not properly implemented** against `doc/strang-splitting-conservative-spec.md`.

The most important defect is not numerical subtlety: **the model selector is probably unreachable**. `newHMF` declares the optional `model` argument as `character(len=12)`, but `HMF_strang_cons` has 15 characters. The constructor then compares that 12-character dummy argument to the full string `HMF_strang_cons`; that comparison will not match. As a result, `this%V%use_conservative_sl` remains at its default `.false.`, and the code falls back to the original spline interpolation path rather than the conservative semi-Lagrangian path.    

## Main findings

### 1. `HMF_strang_cons` is not activated

`PTread_s` returns a `character*144` string, and `vmf90_hmf.f90` passes `PTread_s(HCF, 'model')` into `newHMF`.   But inside `newHMF`, the dummy argument is only `character(len=12)`. The intended selector `HMF_strang_cons` is then compared against that shortened dummy.  

Consequence: with a normal input line such as

```text
model = HMF_strang_cons
```

the constructor will behave like ordinary non-external HMF and leave `use_conservative_sl = .false.`. The dispatcher therefore calls `advance_x_spline` and `advance_v_spline`, not the conservative implementations.  

This alone is enough to answer the question: **as configured by `model = HMF_strang_cons`, the documented conservative method is not actually selected.**

### 2. The latent conservative θ-advection has a periodic-indexing bug

Even if the model-string length is fixed, the conservative θ-advection has a serious boundary bug:

```fortran
periodic_idx = mod(i-1, n) + 1
```



Fortran `MOD(A,P)` returns a result with the same sign as `A`; for example, `MOD(-1,n)` is negative, not `n-1`. GNU Fortran documents `MOD(A,P)` as `A - INT(A/P) * P`, with the returned value having the same sign as `A`; `MODULO(A,P)` is the positive-wrap variant for positive `P`. ([GNU Compiler Collection][1])

So `periodic_idx(0,n)` evaluates to `0`, not `n`. In `advance_x_conservative`, the expression

```fortran
this%copy(periodic_idx(i-ishift-1, this%Nx))
```

can therefore index `copy(0)` at the left periodic boundary.  This violates the spec’s required periodic wrapping for angular advection. The fix is:

```fortran
periodic_idx = modulo(i-1, n) + 1
```

### 3. The conservative advection implemented is only first-order

The spec calls for conservative semi-Lagrangian finite-volume advection using a conservative reconstruction of cell averages; it recommends piecewise parabolic, conservative cubic, or WENO reconstruction, and says publication-quality simulations should use at least third-order conservative reconstruction.  

The implemented conservative routines are:

```fortran
f_new = (1-alpha)*copy(src0) + alpha*copy(src1)
```

for both θ and p directions.  This is the exact finite-volume remap for a **piecewise-constant** reconstruction. It is conservative in the finite-volume sense, apart from the θ wrapping bug above, but it is not the third-order-or-better reconstruction described for production use in the spec.

### 4. The p-grid does not match the spec’s cell-centered finite-volume grid

The spec defines a cell-centered momentum grid with

```math
p_j=-p_{\max}+(j+\tfrac12)\Delta p,\qquad \Delta p=2p_{\max}/N_p.
```



The code instead sets

```fortran
dv = (vmax-vmin)/dble(Nv-1)
get_v = vmin + (mv-1)*dv
```

 

That includes the momentum endpoints and uses `Nv-1` intervals, which is the original interpolation-grid convention, not the documented finite-volume cell-centered grid with `Np` cells. This affects quadrature, mass normalization, energy, and the interpretation of boundary mass.

### 5. The Strang ordering and force timing are mostly correct

The main time loop does implement the expected composition pattern:

```fortran
advance_x(..., 0.5)
compute_rho
compute_force
advance_v(..., 1.0)
advance_x(..., 0.5)
```

with full `advance_x(...,1.0)` steps used to merge adjacent half-steps across multiple inner steps.  This matches the spec’s `A_{dt/2} B_dt A_{dt/2}` ordering and the requirement to compute magnetization/force after the first θ half-step.  

The force formula is also consistent with the spec:

```fortran
force(i) = cos(theta_i)*My - sin(theta_i)*Mx
```

which is `F_i = -Mx sin(theta_i) + My cos(theta_i)`.   

### 6. Diagnostics are incomplete relative to the spec

The spec requires monitoring mass, energy, magnetization, `L2`, positivity via `f_min`, and momentum-boundary mass `B_p`.  

The program writes mass, energy, kinetic/interacting energy, momentum, `Mx`, `My`, `I2`, and `I3`.  `I2` is computed as `sum(f^2)*dx*dv`, so it corresponds to the spec’s `L2` diagnostic.  But I found no corresponding output for `f_min` or momentum-boundary mass `B_p` in the HMF output setup. 

## Compliance summary

| Spec item                                         |                          Status | Notes                                                                                        |
| ------------------------------------------------- | ------------------------------: | -------------------------------------------------------------------------------------------- |
| `model = HMF_strang_cons` selects conservative SL |                        **Fail** | String length 12 makes the 15-character model name not match.                                |
| Strang `A(dt/2) B(dt) A(dt/2)` ordering           |                        **Pass** | Main loop structure is consistent.                                                           |
| Force computed after first θ half-step            |                        **Pass** | `compute_force` is called after `advance_x(0.5)` and uses the correct formula.               |
| Conservative θ advection with periodic wrapping   |               **Fail / latent** | Uses `mod`, not `modulo`, so negative/zero wrapped indices can produce index 0.              |
| Conservative p advection with zero extension      |                     **Partial** | Bounds checks implement zero extension, but the grid is not the spec’s cell-centered p-grid. |
| Third-order-or-better conservative reconstruction |                        **Fail** | Implemented remap is piecewise constant / first-order.                                       |
| Cell-centered finite-volume grid                  | **Fail for p; ambiguous for θ** | Momentum grid includes endpoints and uses `Nv-1`.                                            |
| Required diagnostics                              |                     **Partial** | Mass, energy, Mx/My, and I2 exist; `f_min` and boundary mass are missing.                    |

## Minimal fixes

The first fixes should be mechanical:

```fortran
! In HMF_module.f90
character(len=*), optional, intent(in) :: model

...

if (present(model)) then
   select case (trim(model))
   case ('HMFext', 'HMFext_strang_cons')
      this%is_ext = .true.
      ...
   case default
      this%is_ext = .false.
      this%epsilon = 1.d0
      this%Hfield = 0.d0
   end select

   select case (trim(model))
   case ('HMF_strang_cons', 'HMFext_strang_cons')
      this%V%use_conservative_sl = .true.
   end select
end if
```

Then fix the periodic indexer:

```fortran
integer function periodic_idx(i, n)
  integer, intent(in) :: i, n
  periodic_idx = modulo(i-1, n) + 1
end function periodic_idx
```

After that, the numerical implementation still needs work to match the document: change the p-grid to cell centers with `dv = (vmax-vmin)/Nv`, implement a third-order conservative reconstruction such as PPM/cubic/WENO using primitive integrals, and add `f_min` plus momentum-boundary-mass diagnostics.

Bottom line: **the current code is not a conforming implementation of `doc/strang-splitting-conservative-spec.md`; in its present form, `model = HMF_strang_cons` almost certainly runs the old spline method, not the conservative Strang finite-volume method.

**

[1]: https://gcc.gnu.org/onlinedocs/gfortran/MOD.html?utm_source=chatgpt.com "MOD (The GNU Fortran Compiler)"
