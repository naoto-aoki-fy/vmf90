module hmf_ctypes
  use, intrinsic :: iso_c_binding
  use HMF_module
  implicit none
contains
  subroutine hmf_run(nx, nv, vmax, dt, n_steps, n_top, width, bag, mx_out, my_out, en_out) bind(c)
    integer(c_int), value, intent(in) :: nx, nv, n_steps, n_top
    real(c_double), value, intent(in) :: vmax, dt, width, bag
    real(c_double), intent(out) :: mx_out(*), my_out(*), en_out(*)

    type(HMF) :: h
    integer :: t, t_top

    call newHMF(h, nx, nv, vmax)
    h%V%DT = dt
    call init_carre(h%V, width, bag)
    h%f0 = 1d0/(4d0*width*bag)

    call compute_rho(h%V)
    call compute_M(h)
    call compute_phys(h)
    mx_out(1) = h%Mx
    my_out(1) = h%My
    en_out(1) = h%V%energie

    do t_top = 1, n_top
      call advance_x(h%V, 0.5d0)
      do t = 1, n_steps-1
        call compute_rho(h%V)
        call compute_force(h)
        call advance_v(h%V, 1.d0)
        call advance_x(h%V, 1.d0)
      end do

      call compute_rho(h%V)
      call compute_force(h)
      call advance_v(h%V, 1.d0)
      call advance_x(h%V, 0.5d0)

      call compute_rho(h%V)
      call compute_M(h)
      call compute_phys(h)
      mx_out(t_top+1) = h%Mx
      my_out(t_top+1) = h%My
      en_out(t_top+1) = h%V%energie
    end do
  end subroutine hmf_run
end module hmf_ctypes
