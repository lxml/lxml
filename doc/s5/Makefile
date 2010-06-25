PYTHON?=python

SLIDES=$(subst .txt,.html,$(wildcard *.txt))

slides: $(SLIDES)

%.html: %.txt
	$(PYTHON) rst2s5.py --current-slide --language=en $< $@

clean:
	rm -f *~ $(SLIDES)
