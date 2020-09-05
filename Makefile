PYTHON?=python
PYTHON3?=python3
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
LXMLVERSION:=$(shell sed -ne '/__version__/s|.*__version__\s*=\s*"\([^"]*\)".*|\1|p' src/lxml/__init__.py)

PARALLEL?=$(shell $(PYTHON) -c 'import sys; print("-j7" if sys.version_info >= (3, 5) else "")' )
PARALLEL3?=$(shell $(PYTHON3) -c 'import sys; print("-j7" if sys.version_info >= (3, 5) else "")' )
PYTHON_WITH_CYTHON?=$(shell $(PYTHON)  -c 'import Cython.Build.Dependencies' >/dev/null 2>/dev/null && echo " --with-cython" || true)
PY3_WITH_CYTHON?=$(shell $(PYTHON3) -c 'import Cython.Build.Dependencies' >/dev/null 2>/dev/null && echo " --with-cython" || true)
CYTHON_WITH_COVERAGE?=$(shell $(PYTHON) -c 'import Cython.Coverage; import sys; assert not hasattr(sys, "pypy_version_info")' >/dev/null 2>/dev/null && echo " --coverage" || true)
CYTHON3_WITH_COVERAGE?=$(shell $(PYTHON3) -c 'import Cython.Coverage; import sys; assert not hasattr(sys, "pypy_version_info")' >/dev/null 2>/dev/null && echo " --coverage" || true)

MANYLINUX_LIBXML2_VERSION=2.9.10
MANYLINUX_LIBXSLT_VERSION=1.1.34
MANYLINUX_CFLAGS=-O3 -g1 -pipe -fPIC -flto
MANYLINUX_LDFLAGS=-flto
MANYLINUX_IMAGE_X86_64=quay.io/pypa/manylinux1_x86_64
MANYLINUX_IMAGE_686=quay.io/pypa/manylinux1_i686
MANYLINUX_IMAGE_AARCH64=quay.io/pypa/manylinux2014_aarch64

AARCH64_ENV=-e AR="/opt/rh/devtoolset-9/root/usr/bin/gcc-ar" \
		-e NM="/opt/rh/devtoolset-9/root/usr/bin/gcc-nm" \
		-e RANLIB="/opt/rh/devtoolset-9/root/usr/bin/gcc-ranlib"

.PHONY: all inplace inplace3 rebuild-sdist sdist build require-cython wheel_manylinux wheel

all: inplace

# Build in-place
inplace:
	$(PYTHON) setup.py $(SETUPFLAGS) build_ext -i $(PYTHON_WITH_CYTHON) --warnings $(subst --,--with-,$(CYTHON_WITH_COVERAGE)) $(PARALLEL)

inplace3:
	$(PYTHON3) setup.py $(SETUPFLAGS) build_ext -i $(PY3_WITH_CYTHON) --warnings $(subst --,--with-,$(CYTHON3_WITH_COVERAGE)) $(PARALLEL3)

rebuild-sdist: require-cython
	rm -f dist/lxml-$(LXMLVERSION).tar.gz
	find src -name '*.c' -exec rm -f {} \;
	$(MAKE) dist/lxml-$(LXMLVERSION).tar.gz

dist/lxml-$(LXMLVERSION).tar.gz:
	$(PYTHON) setup.py $(SETUPFLAGS) sdist $(PYTHON_WITH_CYTHON)

sdist: dist/lxml-$(LXMLVERSION).tar.gz

build:
	$(PYTHON) setup.py $(SETUPFLAGS) build $(PYTHON_WITH_CYTHON)

require-cython:
	@[ -n "$(PYTHON_WITH_CYTHON)" ] || { \
	    echo "NOTE: missing Cython - please use this command to install it: $(PYTHON) -m pip install Cython"; false; }

qemu-user-static:
	docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

wheel_manylinux: wheel_manylinux64 wheel_manylinux32 wheel_manylinuxaarch64
wheel_manylinuxaarch64: qemu-user-static

wheel_manylinux32 wheel_manylinux64 wheel_manylinuxaarch64: dist/lxml-$(LXMLVERSION).tar.gz
	time docker run --rm -t \
		-v $(shell pwd):/io \
		$(if $(patsubst %aarch64,,$@),,$(AARCH64_ENV)) \
		-e CFLAGS="$(MANYLINUX_CFLAGS) $(if $(patsubst %aarch64,,$@),-march=core2,-march=armv8-a -mtune=cortex-a72)" \
		-e LDFLAGS="$(MANYLINUX_LDFLAGS)" \
		-e LIBXML2_VERSION="$(MANYLINUX_LIBXML2_VERSION)" \
		-e LIBXSLT_VERSION="$(MANYLINUX_LIBXSLT_VERSION)" \
		-e WHEELHOUSE=wheelhouse_$(subst wheel_,,$@) \
		$(if $(filter $@,wheel_manylinuxaarch64),$(MANYLINUX_IMAGE_AARCH64),$(if $(patsubst %32,,$@),$(MANYLINUX_IMAGE_X86_64),$(MANYLINUX_IMAGE_686))) \
		bash /io/tools/manylinux/build-wheels.sh /io/$<

wheel:
	$(PYTHON) setup.py $(SETUPFLAGS) bdist_wheel $(PYTHON_WITH_CYTHON)

wheel_static:
	$(PYTHON) setup.py $(SETUPFLAGS) bdist_wheel $(PYTHON_WITH_CYTHON) --static-deps

test_build: build
	$(PYTHON) test.py $(TESTFLAGS) $(TESTOPTS)

test_inplace: inplace
	$(PYTHON) test.py $(TESTFLAGS) $(TESTOPTS) $(CYTHON_WITH_COVERAGE)

test_inplace3: inplace3
	$(PYTHON3) test.py $(TESTFLAGS) $(TESTOPTS) $(CYTHON3_WITH_COVERAGE)

valgrind_test_inplace: inplace
	valgrind --tool=memcheck --leak-check=full --num-callers=30 --suppressions=valgrind-python.supp \
		$(PYTHON) test.py

gdb_test_inplace: inplace
	@echo "file $(PYTHON)\nrun test.py" > .gdb.command
	gdb -x .gdb.command -d src -d src/lxml

bench_inplace: inplace
	$(PYTHON) benchmark/bench_etree.py -i
	$(PYTHON) benchmark/bench_xpath.py -i
	$(PYTHON) benchmark/bench_xslt.py -i
	$(PYTHON) benchmark/bench_objectify.py -i

ftest_build: build
	$(PYTHON) test.py -f $(TESTFLAGS) $(TESTOPTS)

ftest_inplace: inplace
	$(PYTHON) test.py -f $(TESTFLAGS) $(TESTOPTS)

apidoc: apidocclean
	@[ -x "`which sphinx-apidoc`" ] \
		&& (echo "Generating API docs ..." && \
			PYTHONPATH=src:$(PYTHONPATH) sphinx-apidoc -e -P -T -o doc/api src/lxml \
				"*includes" "*tests" "*pyclasslookup.py" "*usedoctest.py" "*html/_html5builder.py" \
				"*.so" "*.pyd") \
		|| (echo "not generating Sphinx autodoc API rst files")

apihtml: apidoc inplace3
	@[ -x "`which sphinx-build`" ] \
		&& (echo "Generating API docs ..." && \
			make -C doc/api html) \
		|| (echo "not generating Sphinx autodoc API documentation")

website: inplace3 docclean
	PYTHONPATH=src:$(PYTHONPATH) $(PYTHON3) doc/mkhtml.py doc/html . ${LXMLVERSION}

html: apihtml website s5

s5:
	$(MAKE) -C doc/s5 slides

apipdf: apidoc inplace3
	rm -fr doc/api/_build
	@[ -x "`which sphinx-build`" ] \
		&& (echo "Generating API PDF docs ..." && \
			make -C doc/api latexpdf) \
		|| (echo "not generating Sphinx autodoc API PDF documentation")

pdf: apipdf pdfclean
	$(PYTHON) doc/mklatex.py doc/pdf . ${LXMLVERSION}
	(cd doc/pdf && pdflatex lxmldoc.tex \
		    && pdflatex lxmldoc.tex \
		    && pdflatex lxmldoc.tex)
	@cp doc/pdf/lxmldoc.pdf doc/pdf/lxmldoc-${LXMLVERSION}.pdf
	@echo "PDF available as doc/pdf/lxmldoc-${LXMLVERSION}.pdf"

# Two pdflatex runs are needed to build the correct Table of contents.

test: test_inplace

test3: test_inplace3

valtest: valgrind_test_inplace

gdbtest: gdb_test_inplace

bench: bench_inplace

ftest: ftest_inplace

clean:
	find . \( -name '*.o' -o -name '*.so' -o -name '*.py[cod]' -o -name '*.dll' \) -exec rm -f {} \;
	rm -rf build

docclean:
	$(MAKE) -C doc/s5 clean
	rm -f doc/html/*.html

pdfclean:
	rm -fr doc/pdf

apidocclean:
	rm -fr doc/html/api
	rm -f doc/api/lxml*.rst
	rm -fr doc/api/_build

realclean: clean docclean apidocclean
	find src -name '*.c' -exec rm -f {} \;
	rm -f TAGS
	$(PYTHON) setup.py clean -a --without-cython
