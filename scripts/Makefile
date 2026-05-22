# Copyright (C) 2009-2011 Pierre de Buyl

# This file is part of vmf90

# vmf90 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# vmf90 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with vmf90.  If not, see <http://www.gnu.org/licenses/>.

F90 = h5fc -O3 -I.
PIC_FLAGS = -fPIC
SHLIB_FLAGS = -shlib
VPATH = ../src
all : hmf hmf_ctypes
hmf: vmf90_hmf
hmf_ctypes: libhmf_ctypes.so

vmf90_version.h: vmf90_version.h.in FORCE
	../scripts/make_version.sh
FORCE:

vmf90.o: vmf90.f90 vmf90_version.h
	$(F90) $(PIC_FLAGS) -c $<

%.o : %.f90
	$(F90) $(PIC_FLAGS) -c $<


# Ensure Fortran module dependencies are built before sources that `use` them
hmf_ctypes.o: hmf_ctypes.f90 HMF_module.o

vmf90_hmf: h5md.o spline_module.o Vlasov_module.o HMF_module.o ParseText.o vmf90_version.h vmf90.o vmf90_hmf.o
	$(F90) h5md.o spline_module.o Vlasov_module.o HMF_module.o ParseText.o vmf90.o vmf90_hmf.o -o vmf90_hmf

libhmf_ctypes.so: spline_module.o Vlasov_module.o HMF_module.o hmf_ctypes.o
	$(F90) $(SHLIB_FLAGS) -shared spline_module.o Vlasov_module.o HMF_module.o hmf_ctypes.o -o libhmf_ctypes.so


clean:
	rm -f spline_module.o Vlasov_module.o HMF_module.o ParseText.o vmf90.o \
	vmf90_hmf.o \
	spline_module.mod vlasov_module.mod parsetext.mod vmf90.mod vmf90.mod \
	hmf_module.mod \
	vmf90_version.h vmf90_hmf \
	h5md.o h5md.mod \
	hmf_ctypes.o hmf_ctypes.mod libhmf_ctypes.so
