PYTHON?=python
PYTHON3?=python3
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
LXMLVERSION=$(shell cat version.txt)

PARALLEL=$(shell $(PYTHON) -c 'import sys; print("-j7" if sys.version_info >= (3, 5) else "")' )
PARALLEL3=$(shell $(PYTHON3) -c 'import sys; print("-j7" if sys.version_info >= (3, 5) else "")' )
PYTHON_WITH_CYTHON=$(shell $(PYTHON)  -c 'import Cython.Build.Dependencies' >/dev/null 2>/dev/null && echo " --with-cython" || true)
PY3_WITH_CYTHON=$(shell $(PYTHON3) -c 'import Cython.Build.Dependencies' >/dev/null 2>/dev/null && echo " --with-cython" || true)
CYTHON_WITH_COVERAGE=$(shell $(PYTHON) -c 'import Cython.Coverage; import sys; assert not hasattr(sys, "pypy_version_info")' >/dev/null 2>/dev/null && echo " --coverage" || true)
CYTHON3_WITH_COVERAGE=$(shell $(PYTHON3) -c 'import Cython.Coverage; import sys; assert not hasattr(sys, "pypy_version_info")' >/dev/null 2>/dev/null && echo " --coverage" || true)

MANYLINUX_LIBXML2_VERSION=2.9.8
MANYLINUX_LIBXSLT_VERSION=1.1.32
MANYLINUX_IMAGE_X86_64=quay.io/pypa/manylinux1_x86_64
MANYLINUX_IMAGE_686=quay.io/pypa/manylinux1_i686

.PHONY: all inplace inplace3 rebuild-sdist sdist build require-cython wheel_manylinux wheel

all: inplace

# Build in-place
inplace:
	$(PYTHON) setup.py $(SETUPFLAGS) build_ext -i $(PYTHON_WITH_CYTHON) --warnings --with-coverage $(PARALLEL)

inplace3:
	$(PYTHON3) setup.py $(SETUPFLAGS) build_ext -i $(PY3_WITH_CYTHON) --warnings --with-coverage $(PARALLEL3)

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

wheel_manylinux: wheel_manylinux64 wheel_manylinux32

wheel_manylinux32 wheel_manylinux64: dist/lxml-$(LXMLVERSION).tar.gz
	time docker run --rm -t \
		-v $(shell pwd):/io \
		-e CFLAGS="-O3 -g1 -mtune=generic -pipe -fPIC -flto" \
		-e LDFLAGS="$(LDFLAGS) -flto" \
		-e LIBXML2_VERSION="$(MANYLINUX_LIBXML2_VERSION)" \
		-e LIBXSLT_VERSION="$(MANYLINUX_LIBXSLT_VERSION)" \
		-e WHEELHOUSE=wheelhouse_$(subst wheel_,,$@) \
		$(if $(patsubst %32,,$@),$(MANYLINUX_IMAGE_X86_64),$(MANYLINUX_IMAGE_686)) \
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
	@echo -e "file $(PYTHON)\nrun test.py" > .gdb.command
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

apihtml: inplace
	rm -fr doc/html/api
	@[ -x "`which epydoc`" ] \
		&& (cd src && echo "Generating API docs ..." && \
			PYTHONPATH=. epydoc -v --docformat "restructuredtext en" \
			-o ../doc/html/api --exclude='[.]html[.]tests|[.]_' \
			--exclude-introspect='[.]usedoctest' \
			--name "lxml API" --url / lxml/) \
		|| (echo "not generating epydoc API documentation")

website: inplace
	PYTHONPATH=src:$(PYTHONPATH) $(PYTHON) doc/mkhtml.py doc/html . ${LXMLVERSION}

html: inplace website apihtml s5

s5:
	$(MAKE) -C doc/s5 slides

apipdf: inplace
	rm -fr doc/pdf
	mkdir -p doc/pdf
	@[ -x "`which epydoc`" ] \
		&& (cd src && echo "Generating API docs ..." && \
			PYTHONPATH=. epydoc -v --latex --docformat "restructuredtext en" \
			-o ../doc/pdf --exclude='([.]html)?[.]tests|[.]_' \
			--exclude-introspect='html[.]clean|[.]usedoctest' \
			--name "lxml API" --url / lxml/) \
		|| (echo "not generating epydoc API documentation")

pdf: apipdf
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
	rm -fr doc/html/api
	rm -fr doc/pdf

realclean: clean docclean
	find src -name '*.c' -exec rm -f {} \;
	rm -f TAGS
	$(PYTHON) setup.py clean -a --without-cython
