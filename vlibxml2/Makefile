all: clean
	python setup.py install
	python test/test.py

clean:
	rm -rf build
	rm -rf `find . -name "*.c"`
	rm -rf `find . -name "*.pyc"`
