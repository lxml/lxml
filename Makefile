PYTHON?=python
TESTFLAGS=-p -v
TESTOPTS=
SETUPFLAGS=
LXMLVERSION=`cat version.txt`

all: inplace

# Build in-place
inplace:
	$(PYTHON) setup.py $(SETUPFLAGS) build_ext -i

build:
	$(PYTHON) setup.py $(SETUPFLAGS) build

test_build: build
	$(PYTHON) test.py $(TESTFLAGS) $(TESTOPTS)

test_inplace: inplace
	$(PYTHON) test.py $(TESTFLAGS) $(TESTOPTS)
	PYTHONPATH=src $(PYTHON) selftest.py
	PYTHONPATH=src $(PYTHON) selftest2.py

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
			-o ../doc/html/api --no-private --exclude='[.]html[.]tests|[.]_' \
			--exclude-introspect='[.]usedoctest' \
			--name "lxml API" --url http://codespeak.net/lxml/ lxml/) \
		|| (echo "not generating epydoc API documentation")

html: inplace apihtml
	PYTHONPATH=src $(PYTHON) doc/mkhtml.py doc/html . ${LXMLVERSION}

apipdf: inplace
	rm -fr doc/pdf
	mkdir -p doc/pdf
	@[ -x "`which epydoc`" ] \
		&& (cd src && echo "Generating API docs ..." && \
			PYTHONPATH=. epydoc -v --latex --docformat "restructuredtext en" \
			-o ../doc/pdf --no-private --exclude='([.]html)?[.]tests|[.]_' \
			--exclude-introspect='html[.]clean|[.]usedoctest' \
			--name "lxml API" --url http://codespeak.net/lxml/ lxml/) \
		|| (echo "not generating epydoc API documentation")

pdf: apipdf
	$(PYTHON) doc/mklatex.py doc/pdf . ${LXMLVERSION}
	(cd doc/pdf && pdflatex lxmldoc.tex \
		    && pdflatex lxmldoc.tex \
		    && pdflatex lxmldoc.tex)
	@pdfopt doc/pdf/lxmldoc.pdf doc/pdf/lxmldoc-${LXMLVERSION}.pdf
	@echo "PDF available as doc/pdf/lxmldoc-${LXMLVERSION}.pdf"

# Two pdflatex runs are needed to build the correct Table of contents.

test: test_inplace

valtest: valgrind_test_inplace

gdbtest: gdb_test_inplace

bench: bench_inplace

ftest: ftest_inplace

clean:
	find . \( -name '*.o' -o -name '*.so' -o -name '*.py[cod]' -o -name '*.dll' \) -exec rm -f {} \;
	rm -rf build

docclean:
	rm -f doc/html/*.html
	rm -fr doc/html/api
	rm -fr doc/pdf

realclean: clean docclean
	find . -name '*.c' -exec rm -f {} \;
	rm -f TAGS
	$(PYTHON) setup.py clean -a
