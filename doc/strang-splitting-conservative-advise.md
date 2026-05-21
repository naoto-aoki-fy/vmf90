## Verdict

**No — `strang_cons` is only partially implemented and is not compliant with `doc/strang-splitting-conservative-spec.md` under a strict reading.**

There is **no standalone `strang_cons` routine**. It is a configuration scheme: `newHMF(..., scheme=...)` sets `this%V%use_conservative_sl = .true.` only when `scheme == 'strang_cons'`, and `advance_x` / `advance_v` then dispatch to `advance_x_conservative` / `advance_v_conservative`.  

The implementation does get the **Strang sequencing** mostly right, but the conservative advection operator is a **low-order two-point remap**, not the documented finite-volume semi-Lagrangian method with conservative polynomial reconstruction of cell averages.

---

## What is implemented correctly

| Spec item                                     |                                                                                                                              Implementation status |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------: |
| Configurable conservative mode                |                                                                                  **Yes**. `scheme = strang_cons` activates `use_conservative_sl`.  |
| Strang order `A(dt/2) B(dt) A(dt/2)`          |                    **Mostly yes**. The loop does `advance_x(0.5)`, then force / `advance_v(1.0)`, then `advance_x`, ending with `advance_x(0.5)`.  |
| Force evaluated after first angular half-step |                                                    **Yes**. The loop computes `rho`, then `force`, after `advance_x(0.5)` and before `advance_v`.  |
| Force formula                                 |                                                 **Yes for HMF**. `force = cos(x)*My - sin(x)*Mx`, equivalent to `-Mx sin(theta) + My cos(theta)`.  |
| Periodic angular remap                        |                   **Yes in a narrow sense**. `advance_x_conservative` uses periodic indexing and therefore preserves each fixed-velocity row sum.  |
| Momentum zero extension                       | **Partially**. `advance_v_conservative` drops contributions whose source index falls outside `1:Nv`, which is a discrete zero-extension behavior.  |

---

## Blocking mismatches with the spec

### 1. The grid is not the documented cell-centered finite-volume grid

The spec requires cell centers

[
\theta_i=(i+1/2)\Delta\theta,\qquad
p_j=-p_{\max}+(j+1/2)\Delta p,\qquad
\Delta p=2p_{\max}/N_p.
]

It also defines the unknown as a **cell average** and expects mass to be computed from those cell averages.  

The code instead uses

```fortran
get_x = xmin + (ix-1)*dx
get_v = vmin + (mv-1)*dv
```

and, for periodic grids, sets

```fortran
dx = (xmax-xmin)/Nx
dv = (vmax-vmin)/(Nv-1)
```

with `Nv` points including the velocity endpoints. 

That is a **nodal grid**, not the documented cell-centered finite-volume grid. This is a fundamental mismatch because the spec’s conservative semi-Lagrangian update is defined for **cell averages over cells**, not nodal samples.

---

### 2. The “conservative” advection is not the documented reconstruction/primitive method

The spec requires, for each target cell, tracing the full cell backward and computing

[
\bar g_k^{new} =
\frac{G(x_{k+1/2}-a\tau)-G(x_{k-1/2}-a\tau)}{\Delta x},
]

where (G) is the primitive of a conservative reconstruction (R[g]). It recommends PPM, conservative cubic, or WENO, and says publication-quality simulations should use at least third-order conservative reconstruction. 

The implementation instead does a two-point convex remap:

```fortran
f(i,m) = (1-alpha)*copy(idx0) + alpha*copy(idx1)
```

for both angular and momentum advection. 

That can be interpreted as a **piecewise-constant / low-order remap**, and it is conservative in some discrete sums, but it is **not** the documented primitive-integral scheme with third-order-or-better conservative reconstruction.

---

### 3. The θ-advection row conservation is present, but only for the low-order operator

The spec explicitly says the angular substep must conserve the mass of each fixed-(p_j) row. 

`advance_x_conservative` likely does preserve each row sum exactly because periodic indexing makes the source indices a wrapped permutation and the weights sum to one. 

However, this is still not enough for compliance because the operator is not applied to a cell-centered cell-average grid and does not use the specified conservative reconstruction.

---

### 4. The p-advection zero extension is too crude for the documented method

The spec requires the momentum update to integrate a reconstructed (R_p[\bar f]) over the traced-back momentum cell and use zero extension outside ([-p_{\max},p_{\max}]). 

The code clips source indices:

```fortran
if (src0.ge.1 .and. src0.le.Nv) ...
if (src1.ge.1 .and. src1.le.Nv) ...
```

This implements a discrete zero outside the array, but only for the two-point remap. It does **not** implement a zero-extended conservative reconstruction and primitive integral.

---

### 5. Diagnostics required by the spec are incomplete

The spec requires monitoring mass, energy, magnetization, (L_2), positivity via (f_{\min}), and momentum-boundary mass (B_p). It also asks for reporting max mass drift, energy drift, max (|f_{\min}|), max boundary mass, and convergence checks. 

The code computes/writes mass, energy, momentum, magnetization components, `I2`, `I3`, and optional moments.  

I did not find implementation of:

* `f_min`
* momentum-boundary mass `B_p`
* automated convergence checks
* reported max mass/energy/positivity/boundary diagnostics

So the diagnostic section is not implemented as specified.

---

## Non-issues or minor issues

The code uses ([-\pi,\pi)) rather than ([0,2\pi)) for angle. For a periodic HMF problem this is not a real mathematical problem, provided the quadrature and cell definitions are consistent. The larger issue is that the grid is nodal rather than cell-centered.

The force timing is acceptable: after the initial angular half-step, the main loop computes `rho`, then `force`, then does momentum advection. 

---

## Bottom line

`strang_cons` is better described as:

> **Strang splitting with a low-order conservative-ish semi-Lagrangian remap**

not as:

> **Strang splitting with the documented conservative finite-volume semi-Lagrangian scheme using conservative reconstruction of cell averages.**

To make it compliant, the implementation would need at least:

1. A true cell-centered finite-volume grid:

   ```fortran
   dx = (xmax-xmin)/Nx
   dv = (vmax-vmin)/Nv
   get_x(i) = xmin + (i-0.5d0)*dx
   get_v(m) = vmin + (m-0.5d0)*dv
   ```

2. Treat `f(i,m)` as a cell average, not a nodal value.

3. Replace `advance_x_conservative` and `advance_v_conservative` with primitive-integral remap routines using at least a conservative cubic or PPM reconstruction.

4. Implement zero-extension consistently in the reconstructed primitive for momentum advection.

5. Add required diagnostics: `f_min`, momentum-boundary mass, max relative mass drift, max relative energy drift, and convergence runs.
